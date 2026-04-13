import streamlit as st

from auth.login import tela_login
from pages.consulta import pagina_consulta
from pages.edital import pagina_edital
from pages.atos import pagina_atos

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
    ["Movimentação", "Edital", "Atos TJ", "Sair"]
)

# Mostrar informações do usuário logado
with st.sidebar:
    st.divider()
    if st.session_state.user:
        st.caption(f"✅ Logado como: {st.session_state.user.email}")


# ---------------- ROUTER ----------------

if menu == "Movimentação":

    pagina_consulta()

elif menu == "Edital":
    
    pagina_edital()

elif menu == "Atos TJ":
    
    pagina_atos()

elif menu == "Sair":

    st.session_state.user = None
    st.session_state.token = None
    st.session_state.refresh_token = None

    st.rerun()

# ---------------- RODAPÉ DINÂMICO ----------------

link = ""

if menu == "Movimentação":
    link = "https://transparencia.mprj.mp.br/web/novo-portal-transparencia/plantoes_novo"
elif menu == "Atos TJ":
    link = "https://www3.tjrj.jus.br/sophia_web/acervo/detalhe/304686?guid=1729196909299&returnUrl=%2fsophia_web%2fresultado%2flistar%3fguid%3d1729196909299%26quantidadePaginas%3d1%26codigoRegistro%3d304686%23304686&i=1"
elif menu == "Edital":
    link = "https://www.mprj.mp.br/conheca-o-mprj/conselho-superior"

st.markdown(f"""
<style>
.footer {{
    position: fixed;
    left: 0;
    bottom: 0;
    width: 100%;
    background-color: #FCFCFC;
    color: #0E1117;
    text-align: center;
    padding: 8px;
    font-size: 0.85rem;
    border-top: 1px solid #F0F2F6;
    z-index: 999;
}}
.footer a {{
    color: #4EA1FF;
    text-decoration: none;
}}
</style>

<div class="footer">
    🔗 <b>Fonte dos dados:</b>
    <a href="{link}" target="_blank">Acessar página oficial</a>
</div>
""", unsafe_allow_html=True)