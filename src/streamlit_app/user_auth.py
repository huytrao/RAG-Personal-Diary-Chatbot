import sqlite3
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import os
class UserAuthManager:
    "this class use for user authentication and session management"
    def __init__(self, db_path: str = "./user_db/auth.db"):
        self.db_path = db_path
        self.session_timeout = timedelta(hours=24)
        self._init_auth_database()
    
    def _init_auth_database(self):
        # Create directory if it doesn't exist
        db_dir = os.path.dirname(self.db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                salt TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP,
                is_active BOOLEAN DEFAULT 1
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                session_token TEXT UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP NOT NULL,
                is_active BOOLEAN DEFAULT 1
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def _hash_password(self, password: str, salt: str = None):
        if salt is None:
            salt = secrets.token_hex(32)
        
        password_hash = hashlib.pbkdf2_hmac(
            'sha256', password.encode('utf-8'), salt.encode('utf-8'), 100000
        )
        
        return password_hash.hex(), salt
    
    def register_user(self, username: str, email: str, password: str):
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('SELECT id FROM users WHERE username = ? OR email = ?', (username, email))
            if cursor.fetchone():
                return {"success": False, "message": "User already exists"}
            
            password_hash, salt = self._hash_password(password)
            cursor.execute('''
                INSERT INTO users (username, email, password_hash, salt)
                VALUES (?, ?, ?, ?)
            ''', (username, email, password_hash, salt))
            
            user_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            return {"success": True, "message": "Registration successful", "user_id": user_id}
            
        except Exception as e:
            return {"success": False, "message": str(e)}
    
    def login_user(self, username: str, password: str):
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT id, username, email, password_hash, salt
                FROM users WHERE (username = ? OR email = ?) AND is_active = 1
            ''', (username, username))
            
            user = cursor.fetchone()
            if not user:
                return {"success": False, "message": "Invalid credentials"}
            
            user_id, user_username, user_email, stored_hash, salt = user
            password_hash, _ = self._hash_password(password, salt)
            
            if password_hash != stored_hash:
                return {"success": False, "message": "Invalid credentials"}
            
            session_token = secrets.token_urlsafe(32)
            expires_at = datetime.now() + self.session_timeout
            
            cursor.execute('UPDATE user_sessions SET is_active = 0 WHERE user_id = ?', (user_id,))
            cursor.execute('''
                INSERT INTO user_sessions (user_id, session_token, expires_at)
                VALUES (?, ?, ?)
            ''', (user_id, session_token, expires_at))
            
            conn.commit()
            conn.close()
            
            return {
                "success": True,
                "session_token": session_token,
                "user": {"id": user_id, "username": user_username, "email": user_email}
            }
            
        except Exception as e:
            return {"success": False, "message": str(e)}
    
    def validate_session(self, session_token: str):
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT u.id, u.username, u.email, s.expires_at
                FROM user_sessions s
                JOIN users u ON s.user_id = u.id
                WHERE s.session_token = ? AND s.is_active = 1
            ''', (session_token,))
            
            result = cursor.fetchone()
            if not result:
                return None
            
            user_id, username, email, expires_at = result
            expires_datetime = datetime.fromisoformat(expires_at)
            
            if datetime.now() > expires_datetime:
                cursor.execute('UPDATE user_sessions SET is_active = 0 WHERE session_token = ?', (session_token,))
                conn.commit()
                conn.close()
                return None
            
            conn.close()
            return {"id": user_id, "username": username, "email": email}
            
        except Exception:
            return None
    
    def logout_user(self, session_token: str):
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('UPDATE user_sessions SET is_active = 0 WHERE session_token = ?', (session_token,))
            conn.commit()
            conn.close()
            return True
        except Exception:
            return False
    
    def authenticate_user(self, username_or_email: str, password: str):
        """Authenticate user and return success, message, and user data"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT id, username, email, password_hash, salt
                FROM users WHERE (username = ? OR email = ?) AND is_active = 1
            ''', (username_or_email, username_or_email))
            
            user = cursor.fetchone()
            if not user:
                conn.close()
                return False, "Invalid credentials", None
            
            user_id, username, email, stored_hash, salt = user
            password_hash, _ = self._hash_password(password, salt)
            
            if password_hash != stored_hash:
                conn.close()
                return False, "Invalid credentials", None
            
            # Update last login
            cursor.execute('UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?', (user_id,))
            conn.commit()
            conn.close()
            
            user_data = {"id": user_id, "username": username, "email": email}
            return True, "Login successful", user_data
            
        except Exception as e:
            return False, f"Authentication error: {str(e)}", None
    
    def create_session(self, user_id: int):
        """Create a new session for the user"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            session_token = secrets.token_urlsafe(32)
            expires_at = datetime.now() + self.session_timeout
            
            # Deactivate old sessions
            cursor.execute('UPDATE user_sessions SET is_active = 0 WHERE user_id = ?', (user_id,))
            
            # Create new session
            cursor.execute('''
                INSERT INTO user_sessions (user_id, session_token, expires_at)
                VALUES (?, ?, ?)
            ''', (user_id, session_token, expires_at))
            
            conn.commit()
            conn.close()
            
            return session_token
            
        except Exception as e:
            return None
    
    def change_password(self, user_id: int, old_password: str, new_password: str):
        """Change user password"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Verify old password
            cursor.execute('SELECT password_hash, salt FROM users WHERE id = ?', (user_id,))
            result = cursor.fetchone()
            if not result:
                conn.close()
                return False, "User not found"
            
            stored_hash, salt = result
            old_password_hash, _ = self._hash_password(old_password, salt)
            
            if old_password_hash != stored_hash:
                conn.close()
                return False, "Current password is incorrect"
            
            # Update with new password
            new_password_hash, new_salt = self._hash_password(new_password)
            cursor.execute('''
                UPDATE users SET password_hash = ?, salt = ?
                WHERE id = ?
            ''', (new_password_hash, new_salt, user_id))
            
            conn.commit()
            conn.close()
            
            return True, "Password changed successfully"
            
        except Exception as e:
            return False, f"Error changing password: {str(e)}"
