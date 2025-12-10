import os
import pandas as pd
import streamlit as st
from supabase import create_client, Client

# -------------------- Config da página --------------------
st.set_page_config(page_title="Consulta por Órgão", page_icon="🏛️", layout="wide")
st.title("🏛️ Consulta de Membros por Órgão")
st.caption("Selecione um órgão para listar os campos: membro, designacao e observacao.")

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
    """Busca valores distintos de 'orgao' e os ordena alfabeticamente."""
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
    """Retorna somente as colunas membro, designacao e observacao do órgão selecionado."""
    q = supabase.table("movimentacao").select("mes, membro, designacao, observacao").eq("orgao", orgao).order("membro", desc=False)
    res = q.execute()
    rows = res.data if hasattr(res, "data") else []
    df = pd.DataFrame(rows)
    # garante colunas na ordem desejada, mesmo se vierem fora de ordem
    cols = [c for c in ["mes", "membro", "designacao", "observacao"] if c in df.columns]
    return df[cols] if not df.empty else df

# -------------------- Interface --------------------
st.sidebar.header("Filtro")
orgaos = listar_orgaos_unicos()

if not orgaos:
    st.warning("Não há órgãos cadastrados ou houve erro ao carregar a lista.")
else:
    orgao_sel = st.sidebar.selectbox("Órgão", options=orgaos, index=0)
    consultar = st.sidebar.button("🔎 Consultar")

    if consultar and orgao_sel:
        try:
            df = consultar_por_orgao(orgao_sel)
        except Exception as ex:
            mostrar_erro(ex, "na consulta por órgão")
            st.stop()

        st.subheader(f"Resultados para: **{orgao_sel}**")
        if df.empty:
            st.info("Nenhum registro encontrado para este órgão.")
        else:
            st.success(f"{len(df)} registro(s) encontrado(s).")
            st.dataframe(df, use_container_width=True)

            # Downloads
            c1, c2 = st.columns(2)
            with c1:
                csv_bytes = df.to_csv(index=False).encode("utf-8")
                st.download_button(
                    "⬇️ Baixar CSV",
                    data=csv_bytes,
                    file_name=f"consulta_{orgao_sel}.csv",
                    mime="text/csv"
                )
            with c2:
                # gera Excel em memória
                tmp_path = "/tmp/consulta_orgao.xlsx"
                with pd.ExcelWriter(tmp_path, engine="xlsxwriter") as writer:
                    df.to_excel(writer, index=False, sheet_name="Resultados")
                with open(tmp_path, "rb") as f:
                    st.download_button(
                        "⬇️ Baixar Excel",
                        data=f.read(),
                        file_name=f"consulta_{orgao_sel}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
