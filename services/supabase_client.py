import os
import streamlit as st
from supabase import Client, create_client, ClientOptions
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")

if not SUPABASE_URL or not SUPABASE_ANON_KEY:
    st.error("⚠️ Configure SUPABASE_URL e SUPABASE_ANON_KEY nos Secrets do Streamlit.")
    st.stop()

def get_anon_client():
    return create_client(
        SUPABASE_URL,
        SUPABASE_ANON_KEY
    )

def get_auth_client():
    if "token" in st.session_state and st.session_state.token:
        return create_client(
            SUPABASE_URL,
            SUPABASE_ANON_KEY,
            options=ClientOptions(
                headers={
                    "Authorization": f"Bearer {st.session_state.token}"
                },
                auto_refresh_token=True,
                persist_session=True
            )
        )
    return get_anon_client()

def get_supabase() -> Client:
    return get_auth_client()

def get_user():
    """Recupera o usuário logado da sessão"""
    if "user" in st.session_state:
        return st.session_state.user
    return None

def is_authenticated():
    """Verifica se há um usuário autenticado"""
    return get_user() is not None