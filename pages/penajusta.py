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
    
    # ==================================================
    # CONSULTA
    # ==================================================

    def consultar_ioerj(data):
        pass
    
    
    def consultar_cnj(data):
        pass
    
    
    def consultar_cnmp(data):
        pass
    
    
    def consultar_tjrj(data):
        pass

    if pesquisar:
    
        barra = st.progress(0)
    
        total = len(diarios)
    
        for i, diario in enumerate(diarios):
    
            st.write(f"Consultando {diario}...")
    
            if diario == "IOERJ":
                consultar_ioerj(data)
    
            elif diario == "CNJ":
                consultar_cnj(data)
    
            elif diario == "CNMP":
                consultar_cnmp(data)
    
            elif diario == "TJRJ":
                consultar_tjrj(data)
    
            barra.progress((i + 1) / total)
    
        st.success("Consulta concluída!")
