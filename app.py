
import streamlit as st
import streamlit_authenticator as stauth

st.set_page_config(page_title="Movimentação", page_icon="📊", layout="wide")

# --- Lê secrets brutos
_secrets = st.secrets

# --- Funções utilitárias para converter qualquer estrutura do st.secrets para dict/list/str puros
def to_plain_dict(d):
    """Converte objetos de st.secrets (Tables/Secrets) em dicts puros, recursivamente."""
    if isinstance(d, dict):
        return {k: to_plain_dict(v) for k, v in d.items()}
    try:
        # alguns objetos de secrets têm .items()
        return {k: to_plain_dict(v) for k, v in d.items()}
    except Exception:
        pass
    # listas/tuplas
    if isinstance(d, (list, tuple)):
        return [to_plain_dict(x) for x in d]
    # tipos primitivos
    return d

# --- Extrai e normaliza blocos
raw_credentials = _secrets.get("credentials", {})
raw_cookie      = _secrets.get("cookie", _secrets.get("authentication", {}))

credentials = to_plain_dict(raw_credentials)
cookie      = to_plain_dict(raw_cookie)

# --- Se estiver no schema 0.4.x (users lista), converte para usernames dict (schema 0.3.x)
if "usernames" not in credentials and "users" in credentials:
    usernames = {}
    for u in credentials["users"]:
        uname = u.get("username")
        if not uname:
            continue
        usernames[uname] = {
            "email": u.get("email", ""),
            "name":  u.get("name", uname),
            "password": u.get("password", ""),
        }
    credentials = {"usernames": usernames}

# --- Validações mínimas (agora com dicts puros)
if "usernames" not in credentials or not isinstance(credentials["usernames"], dict):
    st.error("Secrets inválidos: faltou 'credentials.usernames' como dicionário.")
    st.write("Debug credentials (plain):", credentials)
    st.stop()

# Ajuste para cookie quando vier em [authentication] (0.4.x)
if "name" not in cookie and "cookie_name" in cookie:
    cookie["name"] = cookie.get("cookie_name")
if "key" not in cookie and "cookie_key" in cookie:
    cookie["key"] = cookie.get("cookie_key")
if "expiry_days" not in cookie and "cookie_expiry_days" in cookie:
    cookie["expiry_days"] = cookie.get("cookie_expiry_days", 7)

for k in ("name", "key"):
    if k not in cookie or not cookie[k]:
        st.error("Secrets inválidos: defina cookie 'name' e 'key'.")
        st.write("Debug cookie (plain):", cookie)
        st.stop()

expiry_days = int(cookie.get("expiry_days", 7))

# --- Instancia o autenticador com dicts puros
authenticator = stauth.Authenticate(
    credentials,
    cookie["name"],
    cookie["key"],
    expiry_days
)

# --- UI de login
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
