import streamlit as st

def render(role, pages):
    st.title("SETTINGS — integracje/role (demo)")
    st.json({"role": role, "pages": pages})
