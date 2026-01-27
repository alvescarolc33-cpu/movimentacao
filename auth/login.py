import streamlit as st
from services.supabase_client import get_supabase

def tela_login():
    st.title("🔐 Login")

    email = st.text_input("Email")
    senha = st.text_input("Senha", type="password")

    if st.button("Entrar"):
        try:
            supabase = get_supabase()
            res = supabase.auth.sign_in_with_password({
                "email": email,
                "password": senha
            })

            st.session_state.user = res.user
            st.session_state.token = res.session.access_token

            st.success("Login realizado!")
            st.rerun()

        except Exception as e:
            st.error(f"Erro no login: {e}")