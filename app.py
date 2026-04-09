import streamlit as st
from database import init_db
import pages.lecturer as lecturer_page
import pages.student as student_page

# Initialize DB on first run
init_db()

st.set_page_config(page_title="QR Attendance", layout="wide")

# Simple session state
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = None
    st.session_state.role = None

def login():
    st.title("🔐 QR Attendance Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    
    if st.button("Login"):
        conn = st.session_state.get("conn", None) or init_db()  # dummy
        conn = __import__("database").get_connection()
        c = conn.cursor()
        c.execute("SELECT role FROM users WHERE username=? AND password=?", (username, password))
        user = c.fetchone()
        conn.close()
        
        if user:
            st.session_state.logged_in = True
            st.session_state.username = username
            st.session_state.role = user[0]
            st.success(f"Welcome {username}!")
            st.rerun()
        else:
            st.error("Wrong credentials (demo: lecturer1 / student1 / student2  | pass: pass123)")

if not st.session_state.logged_in:
    login()
else:
    st.sidebar.success(f"Logged in as {st.session_state.username} ({st.session_state.role})")
    if st.sidebar.button("Logout"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()
    
    # Navigation
    page = st.sidebar.radio("Go to", ["Lecturer Dashboard" if st.session_state.role == "lecturer" else "Student Scanner"])
    
    if page == "Lecturer Dashboard":
        lecturer_page.show()
    else:
        student_page.show()