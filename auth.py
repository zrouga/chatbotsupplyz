import streamlit as st
import os
from dotenv import load_dotenv
load_dotenv()

def login() -> None:
    with st.sidebar:
        if "authenticated" not in st.session_state:
            st.session_state["authenticated"] = False

        if not st.session_state["authenticated"]:
            st.title("Login")
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            if st.button("Login"):
                if username == os.getenv("USERNAME") and password == os.getenv("PWD"):
                    st.session_state["authenticated"] = True
                    st.success("Logged in successfully!")
                    return
                else:
                    st.error("Invalid username or password")
            st.stop()
