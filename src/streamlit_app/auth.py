"""
User Authentication Module for RAG Personal Diary Chatbot
Developed by huytrao

This module handles user registration, login, session management
and user-specific data isolation.
"""

import sqlite3
import hashlib
import secrets
import streamlit as st
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import os
import re

class UserAuthManager:
    """
    Handles user authentication and session management for the diary app.
    """
    
    def __init__(self, db_path: str = "auth.db"):
        """
        Initialize the authentication manager.
        
        Args:
            db_path: Path to the authentication database
        """
        self.db_path = db_path
        self.session_timeout = timedelta(hours=24)  # 24 hour session timeout
        self._init_auth_database()
    
    def _init_auth_database(self):
        """Initialize the authentication database tables."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                salt TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP,
                is_active BOOLEAN DEFAULT 1,
                profile_data TEXT DEFAULT '{}'
            )
        ''')
        
        # Sessions table for user session management
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                session_token TEXT UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP NOT NULL,
                is_active BOOLEAN DEFAULT 1,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        # Create indexes for better performance
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_sessions_token ON user_sessions(session_token)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON user_sessions(user_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)')
        
        conn.commit()
        conn.close()
    
    def _hash_password(self, password: str, salt: str = None) -> tuple:
        """
        Hash a password with salt using PBKDF2.
        
        Args:
            password: The password to hash
            salt: Optional salt (will generate new one if not provided)
            
        Returns:
            Tuple of (hashed_password, salt)
        """
        if salt is None:
            salt = secrets.token_hex(32)
        
        # Use PBKDF2 with SHA-256
        password_hash = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt.encode('utf-8'),
            100000  # 100,000 iterations
        )
        
        return password_hash.hex(), salt
    
    def _generate_session_token(self) -> str:
        """Generate a secure session token."""
        return secrets.token_urlsafe(32)
    
    def register_user(self, username: str, email: str, password: str) -> Dict[str, Any]:
        """
        Register a new user.
        
        Args:
            username: Username (3-20 characters, alphanumeric + underscore)
            email: Email address
            password: Password (min 8 characters)
            
        Returns:
            Dictionary with success status and message
        """
        # Validation
        if not self._validate_username(username):
            return {"success": False, "message": "Username must be 3-20 characters, alphanumeric and underscore only"}
        
        if not self._validate_email(email):
            return {"success": False, "message": "Invalid email format"}
        
        if not self._validate_password(password):
            return {"success": False, "message": "Password must be at least 8 characters"}
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Check if username or email already exists
            cursor.execute('SELECT id FROM users WHERE username = ? OR email = ?', (username, email))
            if cursor.fetchone():
                return {"success": False, "message": "Username or email already exists"}
            
            # Hash password
            password_hash, salt = self._hash_password(password)
            
            # Insert new user
            cursor.execute('''
                INSERT INTO users (username, email, password_hash, salt)
                VALUES (?, ?, ?, ?)
            ''', (username, email, password_hash, salt))
            
            user_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            return {
                "success": True, 
                "message": "User registered successfully",
                "user_id": user_id
            }
            
        except sqlite3.Error as e:
            return {"success": False, "message": f"Database error: {str(e)}"}
    
    def login_user(self, username: str, password: str) -> Dict[str, Any]:
        """
        Authenticate user and create session.
        
        Args:
            username: Username or email
            password: Password
            
        Returns:
            Dictionary with success status, message, and session data
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get user by username or email
            cursor.execute('''
                SELECT id, username, email, password_hash, salt, is_active
                FROM users 
                WHERE (username = ? OR email = ?) AND is_active = 1
            ''', (username, username))
            
            user = cursor.fetchone()
            if not user:
                return {"success": False, "message": "Invalid credentials"}
            
            user_id, user_username, user_email, stored_hash, salt, is_active = user
            
            # Verify password
            password_hash, _ = self._hash_password(password, salt)
            if password_hash != stored_hash:
                return {"success": False, "message": "Invalid credentials"}
            
            # Create session
            session_token = self._generate_session_token()
            expires_at = datetime.now() + self.session_timeout
            
            # Clean up old sessions for this user
            cursor.execute('UPDATE user_sessions SET is_active = 0 WHERE user_id = ?', (user_id,))
            
            # Insert new session
            cursor.execute('''
                INSERT INTO user_sessions (user_id, session_token, expires_at)
                VALUES (?, ?, ?)
            ''', (user_id, session_token, expires_at))
            
            # Update last login
            cursor.execute('UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?', (user_id,))
            
            conn.commit()
            conn.close()
            
            return {
                "success": True,
                "message": "Login successful",
                "session_token": session_token,
                "user": {
                    "id": user_id,
                    "username": user_username,
                    "email": user_email
                }
            }
            
        except sqlite3.Error as e:
            return {"success": False, "message": f"Database error: {str(e)}"}
    
    def validate_session(self, session_token: str) -> Optional[Dict[str, Any]]:
        """
        Validate a session token and return user data.
        
        Args:
            session_token: The session token to validate
            
        Returns:
            User data if valid session, None otherwise
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT u.id, u.username, u.email, s.expires_at
                FROM user_sessions s
                JOIN users u ON s.user_id = u.id
                WHERE s.session_token = ? AND s.is_active = 1 AND u.is_active = 1
            ''', (session_token,))
            
            result = cursor.fetchone()
            if not result:
                return None
            
            user_id, username, email, expires_at = result
            
            # Check if session has expired
            expires_datetime = datetime.fromisoformat(expires_at)
            if datetime.now() > expires_datetime:
                # Deactivate expired session
                cursor.execute('UPDATE user_sessions SET is_active = 0 WHERE session_token = ?', (session_token,))
                conn.commit()
                conn.close()
                return None
            
            conn.close()
            
            return {
                "id": user_id,
                "username": username,
                "email": email
            }
            
        except sqlite3.Error:
            return None
    
    def logout_user(self, session_token: str) -> bool:
        """
        Logout user by deactivating session.
        
        Args:
            session_token: The session token to logout
            
        Returns:
            True if successful, False otherwise
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('UPDATE user_sessions SET is_active = 0 WHERE session_token = ?', (session_token,))
            
            conn.commit()
            conn.close()
            
            return True
            
        except sqlite3.Error:
            return False
    
    def change_password(self, user_id: int, current_password: str, new_password: str) -> Dict[str, Any]:
        """
        Change user password.
        
        Args:
            user_id: User ID
            current_password: Current password
            new_password: New password
            
        Returns:
            Dictionary with success status and message
        """
        if not self._validate_password(new_password):
            return {"success": False, "message": "New password must be at least 8 characters"}
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get current password hash
            cursor.execute('SELECT password_hash, salt FROM users WHERE id = ?', (user_id,))
            result = cursor.fetchone()
            if not result:
                return {"success": False, "message": "User not found"}
            
            stored_hash, salt = result
            
            # Verify current password
            current_hash, _ = self._hash_password(current_password, salt)
            if current_hash != stored_hash:
                return {"success": False, "message": "Current password is incorrect"}
            
            # Hash new password
            new_hash, new_salt = self._hash_password(new_password)
            
            # Update password
            cursor.execute('UPDATE users SET password_hash = ?, salt = ? WHERE id = ?', 
                         (new_hash, new_salt, user_id))
            
            # Deactivate all sessions to force re-login
            cursor.execute('UPDATE user_sessions SET is_active = 0 WHERE user_id = ?', (user_id,))
            
            conn.commit()
            conn.close()
            
            return {"success": True, "message": "Password changed successfully"}
            
        except sqlite3.Error as e:
            return {"success": False, "message": f"Database error: {str(e)}"}
    
    def get_user_profile(self, user_id: int) -> Optional[Dict[str, Any]]:
        """
        Get user profile data.
        
        Args:
            user_id: User ID
            
        Returns:
            User profile data or None
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT username, email, created_at, last_login, profile_data
                FROM users 
                WHERE id = ? AND is_active = 1
            ''', (user_id,))
            
            result = cursor.fetchone()
            if not result:
                return None
            
            username, email, created_at, last_login, profile_data = result
            
            conn.close()
            
            return {
                "id": user_id,
                "username": username,
                "email": email,
                "created_at": created_at,
                "last_login": last_login,
                "profile_data": profile_data
            }
            
        except sqlite3.Error:
            return None
    
    def _validate_username(self, username: str) -> bool:
        """Validate username format."""
        if not username or len(username) < 3 or len(username) > 20:
            return False
        return re.match(r'^[a-zA-Z0-9_]+$', username) is not None
    
    def _validate_email(self, email: str) -> bool:
        """Validate email format."""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None
    
    def _validate_password(self, password: str) -> bool:
        """Validate password format."""
        return len(password) >= 8
    
    def cleanup_expired_sessions(self):
        """Clean up expired sessions from the database."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('UPDATE user_sessions SET is_active = 0 WHERE expires_at < ?', (datetime.now(),))
            
            conn.commit()
            conn.close()
            
        except sqlite3.Error:
            pass
