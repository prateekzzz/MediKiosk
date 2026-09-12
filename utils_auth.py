import streamlit as st
import hashlib
import bcrypt

# Default users (in production, store in database)
DEFAULT_USERS = {
    "admin": {
        "password_hash": bcrypt.hashpw("admin123".encode(), bcrypt.gensalt()).decode(),
        "role": "admin",
        "name": "Administrator"
    },
    "doctor1": {
        "password_hash": bcrypt.hashpw("doctor123".encode(), bcrypt.gensalt()).decode(),
        "role": "doctor",
        "name": "Dr. Sharma"
    },
    "doctor2": {
        "password_hash": bcrypt.hashpw("doctor123".encode(), bcrypt.gensalt()).decode(),
        "role": "doctor",
        "name": "Dr. Patel"
    }
}

def verify_password(username: str, password: str) -> bool:
    """Verify user credentials"""
    if username not in DEFAULT_USERS:
        return False
    
    stored_hash = DEFAULT_USERS[username]['password_hash'].encode()
    return bcrypt.checkpw(password.encode(), stored_hash)

def login_form():
    """Display login form"""
    st.markdown("## 🔐 Doctor Login")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submit = st.form_submit_button("Login", use_container_width=True)
            
            if submit:
                if verify_password(username, password):
                    st.session_state.authenticated = True
                    st.session_state.username = username
                    st.session_state.user_name = DEFAULT_USERS[username]['name']
                    st.session_state.user_role = DEFAULT_USERS[username]['role']
                    st.success(f"Welcome, {DEFAULT_USERS[username]['name']}!")
                    st.rerun()
                else:
                    st.error("Invalid credentials")
        
        st.info("**Demo Credentials:**\n- Username: `doctor1` / Password: `doctor123`")