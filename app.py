import streamlit as st

from auth.login import tela_login
from pages.consulta import pagina_consulta

# ---------------- SESSION ----------------

if "user" not in st.session_state:
    st.session_state.user = None

if "token" not in st.session_state:
    st.session_state.token = None

if "refresh_token" not in st.session_state:
    st.session_state.refresh_token = None


# ---------------- CONFIG ----------------

st.set_page_config(
    page_title="Consulta por Órgão",
    page_icon="🏛️",
    layout="wide"
)


# ---------------- AUTH ----------------

if not st.session_state.user:
    tela_login()
    st.stop()


# ---------------- MENU ----------------

menu = st.sidebar.radio(
    "Menu",
    ["Consulta", "Sair"]
)

# Mostrar informações do usuário logado
with st.sidebar:
    st.divider()
    if st.session_state.user:
        st.caption(f"✅ Logado como: {st.session_state.user.email}")

# ---------------- ROUTER ----------------

if menu == "Consulta":

    pagina_consulta()

elif menu == "Sair":

    st.session_state.user = None
    st.session_state.token = None
    st.session_state.refresh_token = None

    st.rerun()
