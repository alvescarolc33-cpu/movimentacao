import pandas as pd
import streamlit as st
from services.supabase_client import get_supabase

#---- Tabelas
TABELA_1 = "orgaos_distintos_2"
TABELA_2 = "edital"

COLUNA_SELECT = "orgao"

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

    response = supabase.table(TABELA_1).select(COLUNA_SELECT).execute()

    itens = [
        row[COLUNA_SELECT]
        for row in response.data
        if row.get(COLUNA_SELECT)
    ]

    return sorted(itens)


#---- Buscar ocorrências na Tabela2

def buscar_ocorrencias(item):
    supabase = get_supabase()

    try:
        response = supabase.table(TABELA_2) \
            .select(",".join(COLUNAS_RESULTADO)) \
            .or_(f"orgao_disponivel.eq.{item},orgao_titular.eq.{item}") \
            .execute()

        dados = response.data

    except:
        response = supabase.table(TABELA_2) \
            .select(",".join(COLUNAS_RESULTADO)) \
            .execute()

        df = pd.DataFrame(response.data)

        df = df[
            (df["orgao_disponivel"] == item) |
            (df["orgao_titular"] == item)
        ]

        dados = df.to_dict("records")
    
    if not dados:
        return pd.DataFrame()

    df = pd.DataFrame(dados)

    #----- Ordenar por data
    if "data_sessao" in df.columns:
        df["data_sessao"] = pd.to_datetime(df["data_sessao"], format="%Y/%m/%d", errors="coerce")
        df = df.sort_values(by="data_sessao", ascending=True)

    return df

# --------------------------- Interface Página

def pagina_edital():
    st.title("📊 Análise de Ocorrências")

    itens = listar_itens()

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