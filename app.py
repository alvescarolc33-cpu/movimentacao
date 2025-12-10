import os
import math
import pandas as pd
import streamlit as st
from supabase import create_client, Client

# -------------------- Config da página --------------------
st.set_page_config(page_title="Consulta de Dados", page_icon="🔎", layout="wide")

st.title("🔎 Consulta de Dados (Supabase + Streamlit)")
st.caption("Filtre por órgão, nome e tipo. Suporta grandes volumes com paginação.")

# -------------------- Variáveis de ambiente --------------------
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")

if not SUPABASE_URL or not SUPABASE_ANON_KEY:
    st.error("⚠️ Variáveis de ambiente não configuradas: SUPABASE_URL e SUPABASE_ANON_KEY.")
    st.stop()

# -------------------- Cliente Supabase (cache de recurso) --------------------
@st.cache_resource
def get_supabase() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

supabase = get_supabase()

# -------------------- Sidebar: filtros --------------------
st.sidebar.header("Filtros")
orgao = st.sidebar.text_input("Órgão (igual)")
nome = st.sidebar.text_input("Nome (contém, sem diferenciar maiúsculas/minúsculas)")
tipo = st.sidebar.text_input("Tipo (igual)")

# Paginação: tamanho da página e página atual
page_size = st.sidebar.number_input("Registros por página", min_value=10, max_value=5000, value=50, step=10)
page = st.sidebar.number_input("Página", min_value=1, value=1, step=1)

# Botão consultar
consultar = st.sidebar.button("Consultar")

# -------------------- Função de contagem total --------------------
@st.cache_data(ttl=60)
def contar_registros(orgao_filt, nome_filt, tipo_filt):
    q = supabase.table("dados").select("count", count="exact")
    if orgao_filt:
        q = q.eq("orgao", orgao_filt)
    if nome_filt:
        q = q.ilike("nome", f"%{nome_filt}%")
    if tipo_filt:
        q = q.eq("tipo", tipo_filt)
    res = q.execute()
    # Quando count="exact", supabase retorna count em res.count (em versões mais novas).
    total = getattr(res, "count", None)
    if total is None:
        # fallback: se não vier count, carregar tudo (cuidado com grandes volumes)
        data = getattr(res, "data", [])
        total = len(data) if data else 0
    return total

# -------------------- Função de consulta paginada --------------------
@st.cache_data(ttl=60)
def consultar_paginado(orgao_filt, nome_filt, tipo_filt, page_size, page_number):
    offset = (page_number - 1) * page_size
    q = supabase.table("dados").select("*").range(offset, offset + page_size - 1)
    if orgao_filt:
        q = q.eq("orgao", orgao_filt)
    if nome_filt:
        q = q.ilike("nome", f"%{nome_filt}%")
    if tipo_filt:
        q = q.eq("tipo", tipo_filt)
    res = q.execute()
    data = res.data if hasattr(res, "data") else []
    return pd.DataFrame(data)

# -------------------- Execução da consulta --------------------
if consultar:
    # total de registros para os filtros
    total = contar_registros(orgao, nome, tipo)

    if total == 0:
        st.warning("Nenhum registro encontrado para os filtros aplicados.")
    else:
        total_pages = max(1, math.ceil(total / page_size))

        # Segurança: limitar página ao máximo
        if page > total_pages:
            st.warning(f"Página {page} excede o total ({total_pages}). Ajustei para {total_pages}.")
            page = total_pages

        # Dados da página atual
        df = consultar_paginado(orgao, nome, tipo, page_size, page)

        st.success(f"{total} registro(s) no total • Página {page}/{total_pages} • Exibindo {len(df)} registros")
        st.dataframe(df, use_container_width=True)

        # Download CSV
        if not df.empty:
            csv_data = df.to_csv(index=False).encode("utf-8")
            st.download_button(
                "⬇️ Baixar CSV desta página",
                data=csv_data,
                file_name=f"consulta_p{page}.csv",
                mime="text/csv"
            )

        # Navegação rápida
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("⏮️ Primeira página"):
                st.experimental_set_query_params(page=1)
        with col2:
            if st.button("⬅️ Página anterior"):
                st.experimental_set_query_params(page=max(1, page - 1))
        with col3:
            if st.button("➡️ Próxima página"):
                st.experimental_set_query_params(page=min(total_pages, page + 1))

# Ajuda
with st.expander("ℹ️ Dicas de uso"):
    st.markdown("""
- **Órgão** e **Tipo** filtram por igualdade (use o texto exato que está no banco).
- **Nome** aceita pesquisa parcial, sem diferenciar maiúsculas/minúsculas (ex.: `maria` encontra `Maria da Silva`).
- Use **Registros por página** para controlar quanto aparece de cada vez.  
- Para grandes volumes, recomenda-se criar **índices** no banco:
  ```sql
  CREATE INDEX IF NOT EXISTS idx_dados_orgao ON public.dados (orgao);
  CREATE INDEX IF NOT EXISTS idx_dados_nome ON public.dados (nome);
  CREATE INDEX IF NOT EXISTS idx_dados_tipo ON public.dados (tipo);
