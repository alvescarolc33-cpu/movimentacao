
import streamlit as st
import streamlit_authenticator as stauth

st.set_page_config(page_title="Movimentação", page_icon="📊", layout="wide")

# --- Lê secrets
credentials = st.secrets["credentials"]
cookie = st.secrets["cookie"]

st.write(credentials)
st.write(cookie)

# --- Validação amigável
if "usernames" not in credentials or not isinstance(credentials["usernames"], dict):
    st.error("Secrets inválidos: esperava 'credentials.usernames' como dicionário.\n"
             "Verifique o conteúdo em Settings → Secrets no Streamlit Cloud.")
    st.stop()

authenticator = stauth.Authenticate(
    credentials,                 # precisa do dict com 'usernames'
    cookie["name"],
    cookie["key"],
    cookie["expiry_days"]
)

st.sidebar.title("Acesso")
name, authentication_status, username = authenticator.login("Login", "sidebar")

if authentication_status is False:
    st.sidebar.error("Usuário ou senha inválidos.")
elif authentication_status is None:
    st.sidebar.warning("Informe suas credenciais.")
else:
    st.sidebar.success(f"Bem-vinda, {name}!")
    authenticator.logout("Sair", "sidebar")

    st.title("📊 Painel de Movimentação")
    st.write(f"Usuário logado: {username}")
    # Seu conteúdo protegido aqui
