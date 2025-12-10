import os
import io
import pandas as pd
import streamlit as st
from supabase import create_client, Client

# -------------------- Config da página --------------------
st.set_page_config(page_title="Consulta por Órgão", page_icon="🏛️", layout="wide")
st.title("🏛️ Consulta de Membros por Órgão")
st.caption("Selecione um órgão para listar mes, membro, designacao e observacao. "
           "Depois, veja onde esses mesmos membros aparecem no mesmo mês em outros órgãos.")

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
    """Busca valores de 'orgao' e retorna lista única ordenada.
       (Se preferir, troque por uma VIEW ou query DISTINCT no servidor)."""
    try:
        res = supabase.table("dados").select("orgao").execute()
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
            .table("dados")
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
def consultar_membros_mes_outros_orgaos(membros: list, mes_valor, orgao_sel: str) -> pd.DataFrame:
    """Busca onde os mesmos membros aparecem no mesmo mês, porém em outros órgãos."""
    if not membros or mes_valor is None or mes_valor == "":
        return pd.DataFrame([])
    try:
        q = (
            supabase
            .table("dados")
            .select("orgao, mes, membro, designacao, observacao")
            .in_("membro", membros)
            .eq("mes", mes_valor)
            .neq("orgao", orgao_sel)
            .order("orgao", desc=False)
            .order("membro", desc=False)
        )
        res = q.execute()
        rows = res.data if hasattr(res, "data") else []
        df = pd.DataFrame(rows)
        cols = [c for c in ["orgao", "mes", "membro", "designacao", "observacao"] if c in df.columns]
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
    orgao_sel = st.sidebar.selectbox("Órgão", options=orgaos, index=0)
    consultar = st.sidebar.button("🔎 Consultar")

    if consultar and orgao_sel:
        # ---- Tabela 1: resultados do órgão selecionado ----
        df_orgao = consultar_por_orgao(orgao_sel)

        st.subheader(f"Resultados do órgão: **{orgao_sel}**")
        if df_orgao.empty:
            st.info("Nenhum registro encontrado para este órgão.")
        else:
            st.success(f"{len(df_orgao)} registro(s) encontrado(s).")
            st.dataframe(df_orgao, use_container_width=True)

            # Downloads da tabela 1
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
                # Excel (em memória) para Tabela 1
                excel_buffer_1 = io.BytesIO()
                with pd.ExcelWriter(excel_buffer_1, engine="openpyxl") as writer:
                    df_orgao.to_excel(writer, index=False, sheet_name="Orgão Selecionado")
                excel_buffer_1.seek(0)
                st.download_button(
                    "⬇️ Baixar Excel (Tabela 1)",
                    data=excel_buffer_1.getvalue(),
                    file_name=f"tabela1_{orgao_sel}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

            # ---- Escolha do mês (por padrão: mês do primeiro resultado) ----
            meses_unicos = sorted([m for m in df_orgao["mes"].dropna().unique()])
            mes_padrao = df_orgao.iloc[0]["mes"] if "mes" in df_orgao.columns and not df_orgao.empty else None

            st.markdown("### 🔁 Ocorrências dos mesmos membros no **mesmo mês** em outros órgãos")
            mes_escolhido = st.selectbox(
                "Selecione o mês de referência",
                options=meses_unicos if meses_unicos else [],
                index=meses_unicos.index(mes_padrao) if meses_unicos and mes_padrao in meses_unicos else 0
            ) if meses_unicos else None

            membros_unicos = sorted([m for m in df_orgao["membro"].dropna().unique()]) if "membro" in df_orgao.columns else []

            buscar_outros = st.button("🔍 Buscar em outros órgãos (mesmo mês)")
            if buscar_outros and mes_escolhido:
                df_outros = consultar_membros_mes_outros_orgaos(membros_unicos, mes_escolhido, orgao_sel)

                if df_outros.empty:
                    st.info(f"Nenhuma ocorrência dos mesmos membros no mês **{mes_escolhido}** em outros órgãos.")
                else:
                    st.success(f"{len(df_outros)} ocorrência(s) encontrada(s) no mês **{mes_escolhido}** em outros órgãos.")
                    st.dataframe(df_outros, use_container_width=True)

                    # Downloads da tabela 2
                    col_d2a, col_d2b = st.columns(2)
                    with col_d2a:
                        csv_bytes_2 = df_outros.to_csv(index=False).encode("utf-8")
                        st.download_button(
                            "⬇️ Baixar CSV (Tabela 2)",
                            data=csv_bytes_2,
                            file_name=f"tabela2_outros_orgaos_mes_{mes_escolhido}.csv",
                            mime="text/csv"
                        )
                    with col_d2b:
                        excel_buffer_2 = io.BytesIO()
                        with pd.ExcelWriter(excel_buffer_2, engine="openpyxl") as writer:
                            df_outros.to_excel(writer, index=False, sheet_name="Outros Órgãos")
                        excel_buffer_2.seek(0)
                        st.download_button(
                            "⬇️ Baixar Excel (Tabela 2)",
                            data=excel_buffer_2.getvalue(),
                            file_name=f"tabela2_outros_orgaos_mes_{mes_escolhido}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )
