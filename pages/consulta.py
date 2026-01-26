import io
import pandas as pd
import streamlit as st

from services.supabase_client import get_supabase
from utils.helpers import (
    is_vago,
    normalize_str,
    ordenar_por_mes_e_designacao
)

# --------------------------------------------------
# CLIENT
# --------------------------------------------------

supabase = get_supabase()


# --------------------------------------------------
# CONSULTAS
# --------------------------------------------------

@st.cache_data(ttl=300)
def listar_orgaos():

    res = (
        supabase
        .table("orgaos_distintos")
        .select("orgao")
        .order("orgao")
        .execute()
    )

    return [r["orgao"] for r in res.data or []]


@st.cache_data(ttl=300)
def carregar_movimentacao(orgao: str):

    res = (
        supabase
        .table("movimentacao")
        .select("""
            ano,
            mes,
            orgao,
            membro,
            designacao,
            observacao
        """)
        .eq("orgao", orgao)
        .execute()
    )

    return pd.DataFrame(res.data or [])


@st.cache_data(ttl=300)
def carregar_geral():

    res = (
        supabase
        .table("movimentacao")
        .select("""
            ano,
            mes,
            orgao,
            membro,
            designacao,
            observacao
        """)
        .execute()
    )

    return pd.DataFrame(res.data or [])


# --------------------------------------------------
# ANALISES
# --------------------------------------------------

def analisar_vagos(df: pd.DataFrame):

    if df.empty:
        return df

    df = df.copy()

    df["eh_vago"] = df["membro"].apply(is_vago)

    return df


def analisar_designacoes(df: pd.DataFrame):

    if df.empty:
        return df

    df = df.copy()

    df["eh_designacao"] = df["designacao"].str.contains(
        "DESIG",
        case=False,
        na=False
    )

    return df


def gerar_resumo_orgao(df: pd.DataFrame):

    if df.empty:
        return {}

    total = len(df)

    vagos = df["eh_vago"].sum()

    designacoes = df["eh_designacao"].sum()

    ocupados = total - vagos

    return {
        "Total registros": total,
        "Vagos": int(vagos),
        "Ocupados": int(ocupados),
        "Designações": int(designacoes)
    }


def filtrar_periodo(df, ano, mes):

    if df.empty:
        return df

    return df[
        (df["ano"] == ano) &
        (df["mes"] == mes)
    ]


# --------------------------------------------------
# EXPORTAÇÃO
# --------------------------------------------------

def gerar_excel(df):

    buffer = io.BytesIO()

    with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False)

    buffer.seek(0)

    return buffer


# --------------------------------------------------
# INTERFACE
# --------------------------------------------------

def pagina_consulta():

    st.title("📊 Análise de Movimentação")

    # ---------- FILTROS ----------

    col1, col2, col3 = st.columns(3)

    orgaos = listar_orgaos()

    with col1:
        orgao = st.selectbox("Órgão", orgaos)

    with col2:
        ano = st.selectbox("Ano", [2022, 2023, 2024, 2025])

    with col3:
        mes = st.selectbox(
            "Mês",
            [
                "JANEIRO","FEVEREIRO","MARÇO","ABRIL","MAIO","JUNHO",
                "JULHO","AGOSTO","SETEMBRO","OUTUBRO","NOVEMBRO","DEZEMBRO"
            ]
        )

    if not st.button("Analisar"):
        st.stop()

    # ---------- CARGA ----------

    df = carregar_movimentacao(orgao)

    if df.empty:

        st.warning("Nenhum dado encontrado.")
        st.stop()

    # ---------- FILTRO ----------

    df = filtrar_periodo(df, ano, mes)

    if df.empty:

        st.warning("Sem dados no período.")
        st.stop()

    # ---------- NORMALIZA ----------

    df["membro"] = df["membro"].apply(normalize_str)
    df["designacao"] = df["designacao"].apply(normalize_str)

    df = ordenar_por_mes_e_designacao(df)

    # ---------- ANÁLISES ----------

    df = analisar_vagos(df)

    df = analisar_designacoes(df)

    resumo = gerar_resumo_orgao(df)

    # ---------- DASHBOARD ----------

    st.subheader("📌 Resumo")

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Total", resumo["Total registros"])
    col2.metric("Vagos", resumo["Vagos"])
    col3.metric("Ocupados", resumo["Ocupados"])
    col4.metric("Designações", resumo["Designações"])

    # ---------- TABELA ----------

    st.subheader("📄 Detalhamento")

    st.dataframe(df, use_container_width=True)

    # ---------- DOWNLOAD ----------

    excel = gerar_excel(df)

    st.download_button(
        "⬇️ Baixar Excel",
        data=excel,
        file_name="movimentacao.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
