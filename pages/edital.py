import pandas as pd
import streamlit as st
from services.supabase_client import get_supabase

#---- Tabelas
TABELA_2 = "edital"

COLUNAS_RESULTADO = [
    "data_sessao",
    "sessao",
    "ano",
    "concurso",
    "cargo",
    "validade",
    "criterio",
    "orgao_disponivel",
    "membro",
    "orgao_titular"
]

ANOS_FIXOS = ["Todos", "2023", "2024", "2025", "2026"]

CARGOS_FIXOS = [
    "Todos",
    "PCJ",
    "PJ"
]


#---- Carregar itens do seletor (Tabela1)

def listar_itens():
    supabase = get_supabase()

    response = (
        supabase
        .table("orgaos_distintos_2")
        .select("orgao")
        .execute()
    )

    itens = [
        row["orgao"]
        for row in response.data
        if row.get("orgao")
    ]

    return sorted(itens)


#---- Buscar ocorrências na Tabela2

def buscar_ocorrencias(item):
    supabase = get_supabase()

    response = (
        supabase
        .table("edital")
        .select(",".join(COLUNAS_RESULTADO))
        .execute()
    )

    if not response.data:
        return pd.DataFrame()

    df = pd.DataFrame(response.data)

    if item != "Todos":
    df = df[
        (df["orgao_disponivel"] == item) |
        (df["orgao_titular"] == item)
    ]

    # ordenar por data
    if "data_sessao" in df.columns:
        df["data_sessao"] = pd.to_datetime(df["data_sessao"], errors="coerce")
        df = df.sort_values(by="data_sessao", ascending=True)

    return df
    

# --------------------------- Interface Página

def pagina_edital():
    st.title("📊 Análise de Ocorrências")

    itens = ["Todos"] + listar_itens()

    #----- Filtros

    item = st.selectbox("Selecione o órgão:", itens)

    ano = st.selectbox("Filtrar por ano:", ANOS_FIXOS)

    cargo = st.selectbox("Filtrar por cargo:", CARGOS_FIXOS)

    membro = st.text_input("Filtrar por membro:")


    if item:
        df = buscar_ocorrencias(item)

    #---- Aplicar Filtros Adicionais
        if not df.empty:

            # filtro por ano
            if ano != "Todos":
                df = df[df["ano"].astype(str) == ano]

            # filtro por cargo
            if cargo != "Todos":
                df = df[df["cargo"] == cargo]

            # filtro por membro (busca parcial)
            if membro:
                df = df[
                    df["membro"].str.contains(membro, case=False, na=False)
                ]

    #------ Resultado
        if df.empty:
            st.warning("Nenhum registro encontrado.")
        else:
            st.dataframe(df, use_container_width=True)