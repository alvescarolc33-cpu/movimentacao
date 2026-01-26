import io
import pandas as pd
import streamlit as st

from services.supabase_client import get_supabase
from utils.helpers import (
    is_vago,
    normalize_str,
    ordenar_por_mes_e_designacao
)


supabase = get_supabase()


def listar_orgaos_unicos():

    res = supabase.table("orgaos_distintos").select("orgao").execute()

    return [r["orgao"] for r in res.data or []]


def consultar_por_orgao(orgao: str) -> pd.DataFrame:

    q = (
        supabase
        .table("movimentacao")
        .select("ano, mes, membro, designacao, observacao")
        .eq("orgao", orgao)
        .order("mes")
        .order("membro")
    )

    res = q.execute()

    df = pd.DataFrame(res.data or [])

    if df.empty:
        return df

    return ordenar_por_mes_e_designacao(df)


def pagina_consulta():

    st.title("🏛️ Consulta de Membros por Órgão")

    orgaos = listar_orgaos_unicos()

    df_orgao = pd.DataFrame()

    col1, col2 = st.columns([3, 1])

    with col1:

        orgao_sel = st.selectbox(
            "Órgão",
            options=orgaos
        )

    with col2:

        consultar = st.button("Consultar")

    if consultar:

        df_orgao = consultar_por_orgao(orgao_sel)

        st.dataframe(df_orgao)
