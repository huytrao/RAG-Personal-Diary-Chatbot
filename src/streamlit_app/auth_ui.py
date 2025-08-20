"""
Authentication UI Components for RAG Personal Diary Chatbot
Developed by huytrao

This module provides Streamlit UI components for login, registration,
and user session management.
"""

import streamlit as st
import os
from typing import Optional, Dict, Any
from user_auth import UserAuthManager
import time

class AuthUI:
    """
    Handles authentication UI components and flows.
    """
    
    def __init__(self):
        """Initialize the authentication UI manager."""
        # Use absolute path to auth database
        auth_db_path = os.path.join(os.path.dirname(__file__), "user_database", "auth.db")
        self.auth_manager = UserAuthManager(auth_db_path)
        
        # Initialize session state
        if 'authenticated' not in st.session_state:
            st.session_state.authenticated = False
        if 'user_data' not in st.session_state:
            st.session_state.user_data = None
        if 'session_token' not in st.session_state:
            st.session_state.session_token = None
        if 'auth_mode' not in st.session_state:
            st.session_state.auth_mode = 'login'  # 'login' or 'register'
    
    def check_authentication(self) -> bool:
        """
        Check if user is authenticated and session is valid.
        
        Returns:
            True if authenticated, False otherwise
        """
        if not st.session_state.authenticated or not st.session_state.session_token:
            return False
        
        # Validate session token
        user_data = self.auth_manager.validate_session(st.session_state.session_token)
        if user_data:
            st.session_state.user_data = user_data
            return True
        else:
            # Session expired or invalid
            self.logout()
            return False
    
    def logout(self):
        """Logout the current user."""
        if st.session_state.session_token:
            self.auth_manager.logout_user(st.session_state.session_token)
        
        # Clear session state
        st.session_state.authenticated = False
        st.session_state.user_data = None
        st.session_state.session_token = None
        st.rerun()
    
    def render_login_form(self) -> bool:
        """
        Render the login form.
        
        Returns:
            True if login successful, False otherwise
        """
        with st.form("login_form", clear_on_submit=False):
            st.subheader("🔐 Login to Your Diary")
            
            username_or_email = st.text_input(
                "Username or Email",
                placeholder="Enter your username or email",
                help="Use the username or email you registered with"
            )
            
            password = st.text_input(
                "Password",
                type="password",
                placeholder="Enter your password"
            )
            
            col1, col2, col3 = st.columns([1, 1, 1])
            
            with col2:
                login_submitted = st.form_submit_button(
                    "🚀 Login",
                    use_container_width=True,
                    type="primary"
                )
            
            if login_submitted:
                if not username_or_email or not password:
                    st.error("❌ Please fill in all fields")
                    return False
                
                with st.spinner("🔍 Authenticating..."):
                    success, message, user_data = self.auth_manager.authenticate_user(
                        username_or_email, password
                    )
                
                if success:
                    # Create session
                    session_token = self.auth_manager.create_session(user_data['id'])
                    
                    # Update session state
                    st.session_state.authenticated = True
                    st.session_state.user_data = user_data
                    st.session_state.session_token = session_token
                    
                    st.success(f"✅ Welcome back, {user_data['username']}!")
                    time.sleep(1)
                    st.rerun()
                    return True
                else:
                    st.error(f"❌ {message}")
                    return False
        
        return False
    
    def render_register_form(self) -> bool:
        """
        Render the registration form.
        
        Returns:
            True if registration successful, False otherwise
        """
        with st.form("register_form", clear_on_submit=False):
            st.subheader("📝 Create Your Diary Account")
            
            username = st.text_input(
                "Username",
                placeholder="Choose a unique username (3-20 characters)",
                help="Username must be 3-20 characters, alphanumeric and underscore only"
            )
            
            email = st.text_input(
                "Email",
                placeholder="Enter your email address",
                help="We'll use this for account recovery"
            )
            
            password = st.text_input(
                "Password",
                type="password",
                placeholder="Create a strong password",
                help="At least 8 characters with uppercase, lowercase, and number"
            )
            
            confirm_password = st.text_input(
                "Confirm Password",
                type="password",
                placeholder="Confirm your password"
            )
            
            # Terms and conditions
            terms_accepted = st.checkbox(
                "I agree to the Terms of Service and Privacy Policy",
                help="By checking this box, you agree to our terms and conditions"
            )
            
            col1, col2, col3 = st.columns([1, 1, 1])
            
            with col2:
                register_submitted = st.form_submit_button(
                    "🎉 Create Account",
                    use_container_width=True,
                    type="primary"
                )
            
            if register_submitted:
                # Validation
                if not all([username, email, password, confirm_password]):
                    st.error("❌ Please fill in all fields")
                    return False
                
                if password != confirm_password:
                    st.error("❌ Passwords do not match")
                    return False
                
                if not terms_accepted:
                    st.error("❌ Please accept the Terms of Service")
                    return False
                
                with st.spinner("🔨 Creating your account..."):
                    success, message, user_id = self.auth_manager.register_user(
                        username, email, password
                    )
                
                if success:
                    st.success(f"✅ {message}")
                    st.info("🔐 You can now login with your credentials")
                    
                    # Auto-switch to login mode
                    st.session_state.auth_mode = 'login'
                    time.sleep(2)
                    st.rerun()
                    return True
                else:
                    st.error(f"❌ {message}")
                    return False
        
        return False
    
    def render_user_profile(self):
        """Render user profile section."""
        if not st.session_state.user_data:
            return
        
        user = st.session_state.user_data
        
        with st.sidebar:
            st.markdown("---")
            st.markdown("### 👤 User Profile")
            st.markdown(f"**Username:** {user['username']}")
            st.markdown(f"**Email:** {user['email']}")
            
            # Logout button
            if st.button("🚪 Logout", type="secondary", use_container_width=True):
                self.logout()
            
            # Change password expander
            with st.expander("🔒 Change Password"):
                with st.form("change_password_form"):
                    old_password = st.text_input("Current Password", type="password")
                    new_password = st.text_input("New Password", type="password")
                    confirm_new_password = st.text_input("Confirm New Password", type="password")
                    
                    if st.form_submit_button("Update Password"):
                        if not all([old_password, new_password, confirm_new_password]):
                            st.error("Please fill in all fields")
                        elif new_password != confirm_new_password:
                            st.error("New passwords do not match")
                        else:
                            success, message = self.auth_manager.change_password(
                                user['id'], old_password, new_password
                            )
                            if success:
                                st.success(message)
                                st.info("Please login again with your new password")
                                time.sleep(2)
                                self.logout()
                            else:
                                st.error(message)
    
    def render_auth_page(self):
        """
        Render the main authentication page.
        """
        # Header
        st.markdown("# 📔 Personal Diary Chatbot")
        st.markdown("### *Developed by [@huytrao](https://github.com/huytrao)*")
        st.markdown("---")
        
        # Mode toggle
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button(
                "🔐 Login",
                use_container_width=True,
                type="primary" if st.session_state.auth_mode == 'login' else "secondary"
            ):
                st.session_state.auth_mode = 'login'
                st.rerun()
        
        with col2:
            if st.button(
                "📝 Register",
                use_container_width=True,
                type="primary" if st.session_state.auth_mode == 'register' else "secondary"
            ):
                st.session_state.auth_mode = 'register'
                st.rerun()
        
        st.markdown("---")
        
        # Render appropriate form
        if st.session_state.auth_mode == 'login':
            self.render_login_form()
        else:
            self.render_register_form()
        
        # Features section
        st.markdown("---")
        st.markdown("## ✨ Features")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("""
            **📝 Smart Diary**
            - Write daily entries
            - Auto-tagging with #hashtags
            - Rich metadata support
            """)
        
        with col2:
            st.markdown("""
            **🤖 AI Assistant**
            - Ask about past entries
            - Memory recall
            - Reflection insights
            """)
        
        with col3:
            st.markdown("""
            **🔍 Advanced Search**
            - Semantic search
            - Date filtering
            - Tag-based organization
            """)
        
        # Footer
        st.markdown("---")
        st.markdown(
            """
            <div style='text-align: center; color: #666;'>
                <p>Built with ❤️ by <strong>huytrao</strong> using Streamlit & RAG Technology</p>
                <p><em>Your personal diary with AI-powered insights</em></p>
            </div>
            """,
            unsafe_allow_html=True
        )
    
    def get_current_user_id(self) -> Optional[int]:
        """
        Get the current authenticated user ID.
        
        Returns:
            User ID if authenticated, None otherwise
        """
        try:
            if self.check_authentication() and st.session_state.user_data and isinstance(st.session_state.user_data, dict):
                return st.session_state.user_data.get('id')
        except Exception as e:
            print(f"Error getting user ID: {e}")
        return None
    
    def get_current_username(self) -> Optional[str]:
        """
        Get the current authenticated username.
        
        Returns:
            Username if authenticated, None otherwise
        """
        try:
            if self.check_authentication() and st.session_state.user_data and isinstance(st.session_state.user_data, dict):
                return st.session_state.user_data.get('username')
        except Exception as e:
            print(f"Error getting username: {e}")
        return None
