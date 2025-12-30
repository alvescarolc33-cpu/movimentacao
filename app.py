
import streamlit as st
import streamlit_authenticator as stauth

st.set_page_config(page_title="Movimentação", page_icon="📊", layout="wide")

# Carregar secrets
credentials = st.secrets["credentials"]
cookie = st.secrets["cookie"]
preauthorized = st.secrets.get("preauthorized", {"emails": []})

# Opcional: validar estrutura antes de instanciar
assert "usernames" in credentials and isinstance(credentials["usernames"], dict), \
    "A chave 'credentials.usernames' deve ser um dicionário {username: {...}}."

authenticator = stauth.Authenticate(
    credentials,             # dict com 'usernames'
    cookie["name"],          # string
    cookie["key"],           # string secreta
    cookie["expiry_days"],   # int
    preauthorized["emails"]  # lista de emails (opcional)
)

# Login no sidebar
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
    # Coloque seu conteúdo protegido aqui
