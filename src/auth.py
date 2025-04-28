# auth.py
"""Provides basic, demonstration-only authentication for the Streamlit app.

WARNING: This module uses hardcoded credentials and is NOT secure for 
production environments. It serves only as a placeholder to illustrate 
login flow control in Streamlit.
"""

import hashlib
import streamlit as st
import functools

# --- !!! SECURITY WARNING !!! --- 
# Hardcoded credentials - suitable ONLY for local demos.
# In a real application, use a secure database, environment variables, 
# or an identity provider (e.g., OAuth, SAML) for user management.
USERS = {
    # Username: SHA256 hash of password
    "admin": "8c6976e5b5410415bde908bd4dee15dfb167a9c873fc4bb8a81f6f2ab448a918"  # Default password: 'admin'
}
# ----------------------------- #

def hash_password(password: str) -> str:
    """Hashes a password using SHA256.

    Args:
        password (str): The plain-text password.

    Returns:
        str: The hex digest of the SHA256 hash.
    """
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(username: str, password: str) -> bool:
    """Verifies a given username and password against the stored (hashed) credentials.

    Args:
        username (str): The submitted username.
        password (str): The submitted plain-text password.

    Returns:
        bool: True if the username exists and the hashed password matches, False otherwise.
    """
    if username not in USERS:
        return False
    # Compare the hash of the provided password with the stored hash
    return USERS[username] == hash_password(password)

def login_required(func):
    """Decorator to protect Streamlit pages, requiring login.

    Checks `st.session_state` for a 'username'. If not found, it displays
    a login form. If login is successful, the username is stored in the 
    session state, and the decorated function is executed.

    Args:
        func (callable): The function (Streamlit page rendering logic) to decorate.

    Returns:
        callable: The wrapped function with login check.
    """
    @functools.wraps(func) # Preserve original function metadata
    def wrapper(*args, **kwargs):
        # Check if user is already logged in (username in session state)
        if 'username' not in st.session_state:
            st.warning("Please log in to access this page.")
            
            # Display login form
            username_input = st.text_input("Username", key="login_username")
            password_input = st.text_input("Password", type="password", key="login_password")
            login_button = st.button("Login", key="login_button")

            if login_button:
                # Verify credentials on button click
                if verify_password(username_input, password_input):
                    # Store username in session state upon successful login
                    st.session_state['username'] = username_input
                    st.success("Logged in successfully!")
                    # Rerun the script to reflect the logged-in state and execute the decorated function
                    st.rerun()
                else:
                    st.error("Incorrect username or password")
            # Prevent execution of the decorated function if not logged in
            return
        
        # If already logged in, execute the original function
        return func(*args, **kwargs)
    return wrapper