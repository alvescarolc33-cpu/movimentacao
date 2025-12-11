import os
import io
import pandas as pd
import streamlit as st
from supabase import create_client, Client

# 1) Configuração da página (sempre antes de outros st.*)
st.set_page_config(
    page_title="Consulta de Membros por Órgão",
    page_icon="🏛️",
    layout="wide",
    menu_items={
        'Get Help': None,           # remove "Get Help" do menu
        'Report a bug': None,       # remove "Report a bug"
        'About': "Consulta de Membros • v1.0",  # texto do About
    }
)

# 2) Ocultar toolbar (superior direito)
st.markdown("""
<style>
[data-testid="stToolbar"] { display: none !important; }
header .stActionButton, header [data-testid="stHeader"] div:nth-child(2) { display: none !important; }
</style>
""", unsafe_allow_html=True)

# 3) Ocultar botão "Manage app" (inferior direito)
st.markdown("""
<style>
[data-testid="manage-app-button"] { display: none !important; }
</style>
""", unsafe_allow_html=True)

def is_vago(valor) -> bool:
    """Retorna True se o valor for 'VAGO' (ignorando espaços/caixa)."""
    return isinstance(valor, str) and valor.strip().upper() == "VAGO"

def normalize_str(x):
    """Normaliza para string sem espaços nas pontas (útil para comparar membro/mes)."""
    return "" if x is None else str(x).strip()

# -------------------- Config da página --------------------
st.set_page_config(page_title="Consulta por Órgão", page_icon="🏛️", layout="wide")
st.title("🏛️ Consulta de Membros por Órgão")
st.caption(
    "Selecione um Órgão. Em seguida, o app busca automaticamente onde os Membros aparecem no(s) mês(es)."
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
def consultar_membros_mes_outros_orgaos_pares(df_orgao: pd.DataFrame, orgao_sel: str) -> pd.DataFrame:
    """
    Usa os membros e meses da Tabela 1 e busca todas as ocorrências em outros órgãos,
    mas só retorna registros que casem exatamente o PAR (membro, mes) da Tabela 1.
    Exclui sempre membro = 'VAGO'.
    """

    if df_orgao.empty or "membro" not in df_orgao.columns or "mes" not in df_orgao.columns:
        return pd.DataFrame([])

    # Extrai pares (membro, mes) da Tabela 1, excluindo 'VAGO'
    df_pairs = df_orgao.copy()
    df_pairs["membro_norm"] = df_pairs["membro"].apply(normalize_str)
    df_pairs["mes_norm"] = df_pairs["mes"].apply(normalize_str)
    df_pairs = df_pairs[~df_pairs["membro_norm"].apply(is_vago)]

    membros = sorted(df_pairs["membro_norm"].dropna().unique().tolist())
    meses = sorted(df_pairs["mes_norm"].dropna().unique().tolist())

    if not membros or not meses:
        return pd.DataFrame([])

    # Consulta bruta no Supabase (limitada por conjuntos), excluindo o órgão selecionado e 'VAGO'
    q = (
        supabase
        .table("movimentacao")
        .select("orgao, cod_orgao, mes, membro, designacao, observacao")
        .in_("membro", membros)
        .in_("mes", meses)
        .neq("orgao", orgao_sel)
        .neq("membro", "VAGO")
        .order("mes", desc=False)
        .order("membro", desc=False)
        .order("orgao", desc=False)
    )
    res = q.execute()
    rows = res.data if hasattr(res, "data") else []
    df_raw = pd.DataFrame(rows)

    if df_raw.empty:
        return df_raw

    # Normaliza os campos para comparação de pares
    df_raw["membro_norm"] = df_raw["membro"].apply(normalize_str)
    df_raw["mes_norm"] = df_raw["mes"].apply(normalize_str)

    # Conjunto de pares válidos da Tabela 1
    pairs_set = set(zip(df_pairs["membro_norm"], df_pairs["mes_norm"]))

    # Filtra mantendo apenas (membro, mes) que existam na Tabela 1
    df_outros = df_raw[df_raw.apply(lambda r: (r["membro_norm"], r["mes_norm"]) in pairs_set, axis=1)].copy()

    # Garante ordem e remove colunas auxiliares
    cols = [c for c in ["orgao", "cod_orgao", "mes", "membro", "designacao", "observacao"] if c in df_outros.columns]
    df_outros = df_outros[cols].sort_values(by=["mes", "membro", "orgao"], ascending=[True, True, True])
    df_outros.reset_index(drop=True, inplace=True)

    return df_outros

# -------------------- Interface --------------------

st.markdown("### Filtro")

orgaos = listar_orgaos_unicos()
df_orgao = pd.DataFrame()  # evita NameError

col1, col2 = st.columns([3, 1])

with col1:
    if not orgaos:
        st.warning("Não há Órgãos cadastrados ou houve erro ao carregar a lista.")
        orgao_sel = None
    else:
        orgao_sel = st.selectbox("Órgão/Promotoria", options=orgaos, index=0, key="orgao_sel_top")

with col2:
    # spacer para alinhar verticalmente o botão com o selectbox
    st.write("")  # primeira linha vazia
    st.write("")  # segunda linha vazia (ajusta a altura)
    consultar = st.button("🔎 Consultar", use_container_width=True)

# Fluxo permanece igual
if consultar and orgao_sel:

        # ---- Tabela 1: resultados do órgão selecionado ----
        df_orgao = consultar_por_orgao(orgao_sel)

        st.subheader(f"Resultado: **{orgao_sel}**")
        if df_orgao.empty:
            st.info("Nenhum registro encontrado para este Órgão.")
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
            

# ---- Tabela 2: mesmos membros no(s) mesmo(s) mês(es) em outros órgãos (pareamento exato) ----
st.markdown("### 🔁 Ocorrências em outros Órgãos")

df_outros = consultar_membros_mes_outros_orgaos_pares(df_orgao, orgao_sel)

if df_outros.empty:
    st.info("Nenhuma ocorrência em outros Órgãos.")
else:
    st.success(f"{len(df_outros)} ocorrência(s) encontrada(s) em outros órgãos.")
    st.dataframe(df_outros, use_container_width=True)

    # Downloads da Tabela 2
    col_d2a, col_d2b = st.columns(2)
    with col_d2a:
        csv_bytes_2 = df_outros.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="⬇️ Baixar CSV (Tabela 2)",
            data=csv_bytes_2,
            file_name="tabela2_outros_orgaos.csv",
            mime="text/csv"
        )
    with col_d2b:
        excel_buffer_2 = io.BytesIO()
        with pd.ExcelWriter(excel_buffer_2, engine="xlsxwriter") as writer:
            df_outros.to_excel(writer, index=False, sheet_name="Outros Órgãos")
        excel_buffer_2.seek(0)
        st.download_button(
            label="⬇️ Baixar Excel (Tabela 2)",
            data=excel_buffer_2.getvalue(),
            file_name="tabela2_outros_orgaos.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )