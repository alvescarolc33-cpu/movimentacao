import streamlit as st
import requests

# ==================================================
# CONFIGURAÇÃO
# ==================================================

def pagina_penajusta():

    PALAVRAS = [
        "SEPPEN",
        "PENA JUSTA",
        "CEPPRJ",
        "GMF",
        "superlotação prisional"
    ]
    
    # ==================================================
    # INTERFACE
    # ==================================================

    st.title("📑 Clipping de Diários Oficiais")

    st.sidebar.header("Consulta")
    
    data = st.sidebar.date_input(
        "Data do Diário"
    )
    
    diarios = st.sidebar.multiselect(
        "Diários",
        [
            "IOERJ",
            "CNJ",
            "CNMP",
            "TJRJ"
        ],
        default=[
            "IOERJ",
            "CNJ",
            "CNMP",
            "TJRJ"
        ]
    )
    
    pesquisar = st.sidebar.button(
        "Pesquisar"
    )
