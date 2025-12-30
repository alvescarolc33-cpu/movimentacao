import streamlit as st
import streamlit_authenticator as stauth

st.set_page_config(page_title="App Protegida", page_icon="🔐")

# Carrega configs de secrets
credentials = st.secrets["credentials"]
cookie = st.secrets["cookie"]
preauthorized = st.secrets.get("preauthorized", {})

authenticator = stauth.Authenticate(
    credentials,
    cookie["name"],
    cookie["key"],
    cookie["expiry_days"],
    preauthorized
)

# Renderiza o login e obtém estado
name, authentication_status, username = authenticator.login("Login", "main")

if authentication_status:
    st.sidebar.success(f"Logada: {name}")
    authenticator.logout("Sair", "sidebar")

    st.header("Conteúdo protegido")
    st.write("Sua página Streamlit aqui…")
    # … sua consulta, gráficos, etc.

elif authentication_status is False:
    st.error("Usuário ou senha inválidos.")
elif authentication_status is None:
    st.warning("Por favor, informe usuário e senha.")
