
import os
import io
import pandas as pd
import streamlit as st
from supabase import create_client, Client

# -------------------- Config da página --------------------
st.set_page_config(page_title="Consulta por Órgão/Promotoria", page_icon="🏛️", layout="wide")
st.title("🏛️ Consulta de Membros por Órgão/Promotoria")
st.caption(
    "Selecione um órgão para listar mes, membro, designacao e observacao. "
    "Em seguida, o app busca automaticamente onde esses mesmos membros "
    "aparecem no(s) mesmo(s) mês(es) em outras promotorias/órgãos."
)

# -------------------- Variáveis de ambiente --------------------
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")

if not SUPABASE_URL or not SUPABASE_ANON_KEY:
    st.error("⚠️ Configure SUPABASE_URL e SUPABASE_ANON_KEY nos Secrets do Streamlit.")
    st.stop()

# -------------------- Cliente Supabase (cache) --------------------
@st.cache_resource
def get_supabase() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

supabase = get_supabase()

# -------------------- Utilitários --------------------
def mostrar_erro(ex: Exception, contexto: str = ""):
    st.error(f"❌ Ocorreu um erro {('em ' + contexto) if contexto else ''}: {ex}")

@st.cache_data(ttl=300)
def listar_orgaos_unicos() -> list:
    """
    Busca valores de 'orgao' e retorna lista única ordenada.
    Observação: esta abordagem lê a coluna e deduplica no cliente.
    Para bases muito grandes, considere criar uma VIEW com SELECT DISTINCT.
    """
    try:
        res = supabase.table("movimentacao").select("orgao").execute()
        data = res.data if hasattr(res, "data") else []
        orgaos = sorted({row.get("orgao") for row in data if row.get("orgao")})
        return orgaos
    except Exception as ex:
        mostrar_erro(ex, "ao listar órgãos")
        return []

@st.cache_data(ttl=120)
def consultar_por_orgao(orgao: str) -> pd.DataFrame:
    """Retorna colunas mes, membro, designacao, observacao para o órgão selecionado."""
    try:
        q = (
            supabase
            .table("movimentacao")
            .select("mes, membro, designacao, observacao")
            .eq("orgao", orgao)
            .order("mes", desc=False)
            .order("membro", desc=False)
        )
        res = q.execute()
        rows = res.data if hasattr(res, "data") else []
        df = pd.DataFrame(rows)
        cols = [c for c in ["mes", "membro", "designacao", "observacao"] if c in df.columns]
        return df[cols] if not df.empty else df
    except Exception as ex:
        mostrar_erro(ex, "na consulta por órgão")
        return pd.DataFrame([])

@st.cache_data(ttl=120)
def consultar_membros_mes_outros_orgaos(membros: list, meses: list, orgao_sel: str) -> pd.DataFrame:
    """
    Busca em UMA consulta todas as ocorrências onde:
    - membro ∈ membros da Tabela 1
    - mes ∈ meses da Tabela 1
    - orgao ≠ órgão selecionado
    Retorna orgao, cod_orgao (se existir), mes, membro, designacao, observacao.
    """
    if not membros or not meses:
        return pd.DataFrame([])
    try:
        q = (
            supabase
            .table("movimentacao")
            .select("orgao, cod_orgao, mes, membro, designacao, observacao")
            .in_("membro", membros)
            .in_("mes", meses)
            .neq("orgao", orgao_sel)
            .order("mes", desc=False)
            .order("membro", desc=False)
            .order("orgao", desc=False)
        )
        res = q.execute()
        rows = res.data if hasattr(res, "data") else []
        df = pd.DataFrame(rows)
        cols = [c for c in ["orgao", "cod_orgao", "mes", "membro", "designacao", "observacao"] if c in df.columns]
        return df[cols] if not df.empty else df
    except Exception as ex:
        mostrar_erro(ex, "na consulta de ocorrências em outros órgãos")
        return pd.DataFrame([])

# -------------------- Interface --------------------
st.sidebar.header("Filtro")
orgaos = listar_orgaos_unicos()

if not orgaos:
    st.warning("Não há órgãos cadastrados ou houve erro ao carregar a lista.")
else:
    orgao_sel = st.sidebar.selectbox("Órgão/Promotoria", options=orgaos, index=0)
    consultar = st.sidebar.button("🔎 Consultar")

    if consultar and orgao_sel:
        # ---- Tabela 1: resultados do órgão selecionado ----
        df_orgao = consultar_por_orgao(orgao_sel)

        st.subheader(f"Resultados do órgão/promotoria: **{orgao_sel}**")
        if df_orgao.empty:
            st.info("Nenhum registro encontrado para este órgão.")
        else:
            st.success(f"{len(df_orgao)} registro(s) encontrado(s).")
            st.dataframe(df_orgao, use_container_width=True)

            # Downloads da Tabela 1
            col_d1a, col_d1b = st.columns(2)
            with col_d1a:
                csv_bytes = df_orgao.to_csv(index=False).encode("utf-8")
                st.download_button(
                    "⬇️ Baixar CSV (Tabela 1)",
                    data=csv_bytes,
                    file_name=f"tabela1_{orgao_sel}.csv",
                    mime="text/csv"
                )
            with col_d1b:
                excel_buffer_1 = io.BytesIO()
                with pd.ExcelWriter(excel_buffer_1, engine="xlsxwriter") as writer:
                    df_orgao.to_excel(writer, index=False, sheet_name="Orgão Selecionado")
                excel_buffer_1.seek(0)
                st.download_button(
                    "⬇️ Baixar Excel (Tabela 1)",
                    data=excel_buffer_1.getvalue(),
                    file_name=f"tabela1_{orgao_sel}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

            # ---- Tabela 2: mesmos membros no(s) mesmo(s) mês(es) em outros órgãos ----
            membros_unicos = sorted([m for m in df_orgao["membro"].dropna().unique()]) if "membro" in df_orgao.columns else []
            meses_unicos = sorted([m for m in df_orgao["mes"].dropna().unique()]) if "mes" in df_orgao.columns else []

            st.markdown("### 🔁 Ocorrências dos **mesmos membros** no(s) **mesmo(s) mês(es)** em outras promotorias/órgãos")
            if not membros_unicos or not meses_unicos:
                st.info("Não foi possível determinar membros e/ou meses a partir da Tabela 1.")
            else:
                df_outros = consultar_membros_mes_outros_orgaos(membros_unicos, meses_unicos, orgao_sel)

                if df_outros.empty:
                    st.info("Nenhuma ocorrência dos mesmos membros nos mesmos meses em outros órgãos.")
                else:
                    st.success(f"{len(df_outros)} ocorrência(s) encontrada(s) em outros órgãos.")
                    st.dataframe(df_outros, use_container_width=True)

                    # Downloads da Tabela 2
                    col_d2a, col_d2b = st.columns(2)
                    with col_d2a:
                        csv_bytes_2 = df_outros.to_csv(index=False).encode("utf-8")
                        st.download_button(
                            "⬇️ Baixar CSV (Tabela 2)",
                            data=csv_bytes_2,
                            file_name=f"tabela2_outros_orgaos.csv",
                            mime="text/csv"
                        )
                    with col_d2b:
                        excel_buffer_2 = io.BytesIO()
                        with pd.ExcelWriter(excel_buffer_2, engine="xlsxwriter") as writer:
                            df_outros.to_excel(writer, index=False, sheet_name="Outros Órgãos")
                        excel_buffer_2.seek(0)
                        st.download_button(
                            "⬇️ Baixar Excel (Tabela 2)",
                            data=excel_buffer_2.getvalue(),
                            file_name=f"tabela2_outros_orgaos.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )