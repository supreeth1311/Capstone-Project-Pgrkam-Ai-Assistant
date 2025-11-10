# services/utils.py
import streamlit as st
import re

def init_session():
    if "vector_store" not in st.session_state:
        st.session_state.vector_store = None
    if "history" not in st.session_state:
        st.session_state.history = []
    if "prefs" not in st.session_state:
        st.session_state.prefs = {"roles":[], "sectors":[], "locations":[], "degree":"", "experience":""}

def sanitize_filename(name: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_.-]", "_", name or "file")
