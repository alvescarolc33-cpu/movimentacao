import streamlit as st
import requests
import pdfplumber
from io import BytesIO

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

    def consultar_cnj(data):
    
        st.subheader("CNJ")
    
        try:
    
            pdf_url = obter_pdf_cnj(data)
    
            if pdf_url is None:
                st.warning("Nenhuma edição encontrada.")
                return
    
            resposta = requests.get(pdf_url, timeout=60)
    
            resposta.raise_for_status()
    
            pdf = BytesIO(resposta.content)
    
            ocorrencias = []
    
            with pdfplumber.open(pdf) as arquivo:
    
                for numero_pagina, pagina in enumerate(arquivo.pages, start=1):
    
                    texto = pagina.extract_text()
    
                    if texto is None:
                        continue
    
                    texto_maiusculo = texto.upper()
    
                    for palavra in PALAVRAS:
    
                        if palavra.upper() in texto_maiusculo:
    
                            ocorrencias.append(
                                {
                                    "pagina": numero_pagina,
                                    "palavra": palavra,
                                    "texto": texto
                                }
                            )
    
            if len(ocorrencias) == 0:
    
                st.info("Nenhuma ocorrência encontrada.")
    
            else:
    
                st.success(f"{len(ocorrencias)} ocorrências encontradas.")
    
                for item in ocorrencias:
    
                    with st.expander(
                        f"Página {item['pagina']} - {item['palavra']}"
                    ):
    
                        st.text(item["texto"][:3000])
    
        except Exception as erro:
    
            st.error(str(erro))

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
