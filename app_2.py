import os
import io
import pandas as pd
import streamlit as st
from supabase import create_client

# -------------------- Sessão --------------------
if "user" not in st.session_state:
    st.session_state.user = None

if "access_token" not in st.session_state:
    st.session_state.access_token = None

# -------------------- Variáveis de ambiente --------------------
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")

if not SUPABASE_URL or not SUPABASE_ANON_KEY:
    st.error("⚠️ Configure SUPABASE_URL e SUPABASE_ANON_KEY nos Secrets.")
    st.stop()

# -------------------- Cliente Supabase (cache) --------------------
#@st.cache_resource
#def get_supabase() -> Client:
    #return create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

#supabase = get_supabase()

# Cria o client com a ANON KEY
supabase = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

# Se o usuário já fez login, aplica a sessão
if st.session_state.access_token and st.session_state.refresh_token:
    supabase.auth.set_session({
        "access_token": st.session_state.access_token,
        "refresh_token": st.session_state.refresh_token
    })
``

#tela de login
def tela_login():
    st.title("🔐 Login")

    email = st.text_input("Email")
    senha = st.text_input("Senha", type="password")

    if st.button("Entrar"):
        try:
            res = supabase_anon.auth.sign_in_with_password({
                "email": email,
                "password": senha
            })

            st.session_state.user = res.user
            st.session_state.access_token = res.session.access_token

            st.success("Login realizado com sucesso!")
            st.rerun()

        except Exception as e:
            st.error("Email ou senha inválidos")
            st.caption(str(e))

if not st.session_state.user:
    tela_login()
    st.stop()

supabase = get_supabase()

#Logout (sidebar)
with st.sidebar:
    if st.session_state.user:
        st.write(f"👤 {st.session_state.user.email}")

        if st.button("Sair"):
            supabase.auth.sign_out()
            st.session_state.user = None
            st.session_state.access_token = None
            st.rerun()

    else:
        st.write("🔒 Não autenticado")

# -------------------- Consulta de teste à tabela ORGAOS --------------------
st.header("Órgãos")

try:
    # Exemplo simples de leitura (ajuste o nome da tabela/colunas conforme seu schema)
    resp = supabase.table("orgaos").select("*").limit(20).execute()
    if getattr(resp, "error", None):
        st.error(f"Erro na consulta: {getattr(resp.error, 'message', resp.error)}")
    elif not resp.data:
        st.warning("Não há Órgãos cadastrados ou houve erro ao carregar a lista.")
    else:
        st.success(f"Carregado: {len(resp.data)} órgão(s).")
        st.dataframe(pd.DataFrame(resp.data))
except Exception as e:
    st.error("Falha inesperada ao consultar órgãos.")
    st.caption(str(e))

#--------------------Retorna True se o valor for 'VAGO' (ignorando espaços/caixa)/Normaliza para string sem espaços nas pontas (útil para comparar membro/mes).
def is_vago(valor) -> bool:
    return isinstance(valor, str) and valor.strip().upper() == "VAGO"

def normalize_str(x):
    return "" if x is None else str(x).strip()

# -------------------- Ordem personalizada (sem Categorical) --------------------
# Mapas para ordem de meses e de designação
MESES_MAP = {
    "JANEIRO": 1, "FEVEREIRO": 2, "MARÇO": 3, "ABRIL": 4, "MAIO": 5, "JUNHO": 6,
    "JULHO": 7, "AGOSTO": 8, "SETEMBRO": 9, "OUTUBRO": 10, "NOVEMBRO": 11, "DEZEMBRO": 12
}

DESIGNACAO_MAP = {
    "TITULAR": 1,
    "DESIGNAÇÃO": 2,
    "DESIGNAÇÃO TEMPORÁRIA": 3,
    "AUXÍLIO": 4,
    "AUXÍLIO TEMPORÁRIO": 5,
}

def ordenar_por_mes_e_designacao(df: pd.DataFrame) -> pd.DataFrame:
    #Ordena sem mudar o dtype das colunas (evita problemas com fillna/replace): - Cria colunas auxiliares numéricas para a ordenação (mes e designacao); - Ordena por essas colunas e por colunas de apoio (membro, orgao) se existirem; - Remove as colunas auxiliares no fim.
    if df.empty:
        return df

    df = df.copy()

    # Chaves de ordenação (sem alterar o tipo original das colunas)
    if "mes" in df.columns:
        df["__mes_ord__"] = df["mes"].map(MESES_MAP).fillna(999)
    if "designacao" in df.columns:
        df["__des_ord__"] = df["designacao"].map(DESIGNACAO_MAP).fillna(999)

    # Monta a lista de colunas para o sort
    sort_cols = []
    ascending = []

    if "__mes_ord__" in df.columns:
        sort_cols.append("__mes_ord__"); ascending.append(True)
    if "__des_ord__" in df.columns:
        sort_cols.append("__des_ord__"); ascending.append(True)
    if "membro" in df.columns:
        sort_cols.append("membro"); ascending.append(True)
    if "orgao" in df.columns:
        sort_cols.append("orgao"); ascending.append(True)

    if sort_cols:
        df = df.sort_values(by=sort_cols, ascending=ascending, kind="mergesort")

    # Remove colunas auxiliares
    for c in ["__mes_ord__", "__des_ord__"]:
        if c in df.columns:
            df.drop(columns=c, inplace=True)

    return df

# -------------------- Config da página --------------------
st.set_page_config(
    page_title="Consulta por Órgão",
    page_icon="🏛️",
    layout="wide",
    menu_items={
        "Get Help": None,
        "Report a bug": None,
        "About": "Consulta de Membros • v1.0",
    },
)

# 1) Título
st.title("🏛️ Consulta de Membros por Órgão")
st.caption("Selecione um Órgão. Em seguida, o app busca automaticamente onde os Membros aparecem no(s) mês(es).")

# 2) Ocultar toolbar/cabeçalho (variações de seletor)
st.markdown(
    """
    <style>
    /* Tentar esconder toolbar padrão */
    [data-testid="stToolbar"] { display: none !important; }

    /* Esconder container do header (algumas versões) */
    header { visibility: hidden !important; }

    /* Esconder botões de ação no cabeçalho (variação) */
    header .stActionButton { display: none !important; }

    /* Em algumas builds, este seletor do header funciona melhor: */
    [data-testid="stHeader"] { display: none !important; }

    /* Ajuste o padding do app após esconder o header */
    .block-container { padding-top: 2rem; }
    </style>
    """,
    unsafe_allow_html=True,
)

# 3) Ocultar botão "Manage app" (apenas na Community Cloud)
st.markdown(
    """
    <style>
    /* Botão de "Manage app" na Cloud */
    [data-testid="manage-app-button"] { display: none !important; }

    /* Às vezes vem dentro de um portal/overlay */
    .stAppViewContainer [class*="ManageAppButton"], .app-controls { display: none !important; }
    </style>
    """,
    unsafe_allow_html=True,
)

# -------------------- Utilitários --------------------
def mostrar_erro(ex: Exception, contexto: str = ""):
    st.error(f"❌ Ocorreu um erro {('em ' + contexto) if contexto else ''}: {ex}")

@st.cache_data(ttl=300)
def listar_orgaos_unicos() -> list:
    #Busca valores de 'orgao' e retorna lista única ordenada.
    #Observação: esta abordagem lê a coluna e deduplica no cliente.
    #Para bases muito grandes, considere criar uma VIEW com SELECT DISTINCT. Usando VIEW via SUPABASE.
    
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
    #Retorna colunas mes, membro, designacao, observacao para o órgão selecionado.
    try:
        q = (
            supabase
            .table("movimentacao")
            .select("ano, mes, membro, designacao, observacao")
            .eq("orgao", orgao)
            # A ordem do Supabase aqui não garante cronologia, mas não atrapalha
            .order("mes", desc=False)
            .order("membro", desc=False)
        )
        res = q.execute()
        rows = res.data if hasattr(res, "data") else []
        df = pd.DataFrame(rows)
        cols = [c for c in ["ano", "mes", "membro", "designacao", "observacao"] if c in df.columns]
        df = df[cols] if not df.empty else df

        #Ordena pela ordem customizada
        df = ordenar_por_mes_e_designacao(df)
        return df
    except Exception as ex:
        mostrar_erro(ex, "na consulta por órgão")
        return pd.DataFrame([])

@st.cache_data(ttl=120)
def consultar_membros_mes_outros_orgaos_pares(df_orgao: pd.DataFrame, orgao_sel: str) -> pd.DataFrame:
    #Usa os membros e meses da Tabela 1 e busca todas as ocorrências em outros órgãos, mas só retorna registros que casem exatamente o PAR (membro, mes) da Tabela 1. Exclui sempre membro = 'VAGO'.
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
        .select("mes, ano, orgao, cod_orgao, membro, designacao, observacao")
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
    cols = [c for c in ["orgao", "cod_orgao", "mes", "ano", "membro", "designacao", "observacao"] if c in df_outros.columns]
    df_outros = df_outros[cols]

    #Ordena pela ordem customizada
    df_outros = ordenar_por_mes_e_designacao(df_outros)

    df_outros.reset_index(drop=True, inplace=True)
    return df_outros

# -------------------- Interface --------------------
#st.markdown("### Filtro")
st.markdown('<h3 style="font-size:0.95rem;line-height:1.2;margin:0 0 .5rem 0;">Filtro</h3>', unsafe_allow_html=True)

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

if consultar and orgao_sel:
    # ---- Tabela 1: resultados do órgão selecionado ----
    df_orgao = consultar_por_orgao(orgao_sel)

    #st.subheader(f"Resultado: **{orgao_sel}**")
    st.markdown(
        f'<h3 style="font-size:1.1rem;margin:0;">Resultado: <strong>{orgao_sel}</strong></h3>',
        unsafe_allow_html=True
    )
    if df_orgao.empty:
        st.info("Nenhum registro encontrado para este Órgão.")
    else:
        st.dataframe(df_orgao, use_container_width=True)

    # ---- Tabela 2: mesmos membros no(s) mesmo(s) mês(es) em outros órgãos (pareamento exato) ----
    st.markdown('<h3 style="font-size:0.95rem;line-height:1.2;margin:0 0 .5rem 0;">🔁 Ocorrências em outros Órgãos</h3>', unsafe_allow_html=True)

    df_outros = consultar_membros_mes_outros_orgaos_pares(df_orgao, orgao_sel)

    if df_outros.empty:
        st.info("Nenhuma ocorrência em outros Órgãos.")
    else:
        st.dataframe(df_outros, use_container_width=True)
    
# -------------------- Downloads ÚNICOS --------------------
    st.divider()
    st.markdown('<h3 style="font-size:0.95rem;line-height:1.2;margin:0 0 .5rem 0;">⬇️ Exportação consolidada</h3>', unsafe_allow_html=True)

    # 1) CSV único com as duas tabelas empilhadas e coluna de origem
    df_orgao_com_tag = df_orgao.copy()
    df_orgao_com_tag["_tabela"] = "Tabela 1 - Órgão Selecionado"

    df_outros_com_tag = df_outros.copy()
    df_outros_com_tag["_tabela"] = "Tabela 2 - Outros Órgãos"

    df_consolidado = pd.concat([df_orgao_com_tag, df_outros_com_tag], ignore_index=True, sort=False)

    csv_bytes_all = df_consolidado.to_csv(index=False).encode("utf-8")

    # 2) Excel único com duas abas (mais organizado para leitura)
    excel_buffer_all = io.BytesIO()
    with pd.ExcelWriter(excel_buffer_all, engine="xlsxwriter") as writer:
        # Se quiser preservar o DataFrame original sem a coluna `_tabela`:
        df_orgao.to_excel(writer, index=False, sheet_name="Órgão Selecionado")
        df_outros.to_excel(writer, index=False, sheet_name="Outros Órgãos")

        # Opcional: também incluir a aba consolidada com a coluna `_tabela`
        # df_consolidado.to_excel(writer, index=False, sheet_name="Consolidado")

    excel_buffer_all.seek(0)

    col_dl_csv, col_dl_xlsx = st.columns(2)
    with col_dl_csv:
        st.download_button(
            label="⬇️ Baixar CSV (Consolidado)",
            data=csv_bytes_all,
            file_name=f"consolidado_{orgao_sel}.csv",
            mime="text/csv",
            use_container_width=True
        )
    with col_dl_xlsx:
        st.download_button(
            label="⬇️ Baixar Excel (2 abas)",
            data=excel_buffer_all.getvalue(),
            file_name=f"consolidado_{orgao_sel}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )
        
    # -------------------- Análises de Auxílios --------------------
    st.divider()
    st.markdown(
        '<h3 style="font-size:0.95rem;line-height:1.2;margin:0 0 .5rem 0;">📊 Análises de Auxílios (Órgão selecionado)</h3>',
        unsafe_allow_html=True
    )

    # Cópia defensiva e filtro por 'auxílio' na designação (case-insensitive, com e sem acento)
    df_auxilio = df_orgao.copy()
    if not df_auxilio.empty:
        df_auxilio["designacao"] = df_auxilio["designacao"].fillna("")
        mask_aux = df_auxilio["designacao"].str.contains(r"aux[ií]lio", case=False, regex=True)
        df_auxilio = df_auxilio[mask_aux].copy()
    else:
        df_auxilio = pd.DataFrame([])

    if df_auxilio.empty:
        st.info("Não há registros de auxílio para o Órgão selecionado.")
    else:
        # Normaliza 'mes' para 'ano_mes' (AAAA-MM) quando possível; senão, mantém o original
        # Tenta converter valores comuns (AAAA-MM, AAAA/MM, AAAA-MM-DD, DD/MM/AAAA, etc.)
        df_auxilio["ano_mes"] = pd.to_datetime(df_auxilio["mes"], errors="coerce").dt.to_period("M").astype(str)
        # Se não conseguiu converter (NaT), usa o valor original de 'mes'
        df_auxilio["ano_mes"] = df_auxilio["ano_mes"].mask(df_auxilio["ano_mes"].isin(["NaT", "nan"]), df_auxilio["mes"])

        # --- Métricas rápidas ---
        total_reg_auxilio = len(df_auxilio)
        meses_com_auxilio = df_auxilio["ano_mes"].nunique()
        membros_distintos_auxilio = df_auxilio["membro"].nunique()

        colm1, colm2, colm3 = st.columns(3)
        with colm1:
            st.metric("Registros de auxílio", value=f"{total_reg_auxilio}")
        with colm2:
            st.metric("Meses com ocorrência de auxílio", value=f"{meses_com_auxilio}")
        with colm3:
            st.metric("Membros distintos (com auxílio)", value=f"{membros_distintos_auxilio}")

        # --- Quantidade por mês ---
        qtd_por_mes = (
            df_auxilio
            .groupby("ano_mes", as_index=False)
            .size()
            .rename(columns={"size": "quantidade"})
        )

        # Ordena cronologicamente quando possível
        qtd_por_mes["ord"] = pd.to_datetime(qtd_por_mes["ano_mes"], errors="coerce")
        qtd_por_mes = qtd_por_mes.sort_values(["ord", "ano_mes"], ascending=[True, True]).drop(columns=["ord"])

        # --- Gráfico de barras por mês ---
        #try:
        #    import altair as alt

        #    chart_mes = (
        #        alt.Chart(qtd_por_mes)
        #        .mark_bar(color="#4E79A7")
        #        .encode(
        #            x=alt.X("ano_mes:N", title="Mês (AAAA-MM)"),
        #            y=alt.Y("quantidade:Q", title="Quantidade de auxílios"),
        #            tooltip=["ano_mes", "quantidade"]
        #        )
        #        .properties(title="Auxílios por mês", width="container", height=220)
        #    )
        #    st.altair_chart(chart_mes, use_container_width=True)
        #except Exception:
        #    # Fallback caso Altair não esteja disponível
        #    st.bar_chart(qtd_por_mes.set_index("ano_mes"))

        # --- Tabela resumo ---
        st.markdown('<h3 style="font-size:0.95rem;line-height:1.2;margin:0 0 .5rem 0;">Resumo por mês</h3>', unsafe_allow_html=True)
        st.dataframe(qtd_por_mes, use_container_width=True)
        
    # -------------------- Análise: designacao == 'DESIGNAÇÃO' --------------------
    st.divider()
    st.markdown(
        '<h3 style="font-size:0.95rem;line-height:1.2;margin:0 0 .5rem 0;">🧾 Ocorrências com Designação</h3>',
        unsafe_allow_html=True
    )

    df_designacao = df_orgao.copy()
    if not df_designacao.empty:
        # Comparação exata, ignorando espaços/acento comuns
        df_designacao["designacao"] = df_designacao["designacao"].fillna("").str.strip()
        df_designacao = df_designacao[df_designacao["designacao"].str.upper() == "DESIGNAÇÃO"]
    else:
        df_designacao = pd.DataFrame([])

    if df_designacao.empty:
        st.info("Não há ocorrências com designação igual a 'DESIGNAÇÃO'.")
    else:
        # Normaliza 'mes' -> 'ano_mes' (AAAA-MM), mantendo original quando não parseável
        df_designacao["ano_mes"] = (
            pd.to_datetime(df_designacao["mes"], errors="coerce")
            .dt.to_period("M").astype(str)
        )
        df_designacao["ano_mes"] = df_designacao["ano_mes"].mask(
            df_designacao["ano_mes"].isin(["NaT", "nan"]),
            df_designacao["mes"]
        )

        # Métricas
        total_designacao = len(df_designacao)
        meses_designacao = df_designacao["ano_mes"].nunique()
        membros_designacao = df_designacao["membro"].nunique()

        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("Registros 'DESIGNAÇÃO'", value=total_designacao)
        with c2:
            st.metric("Meses com 'DESIGNAÇÃO'", value=meses_designacao)
        with c3:
            st.metric("Membros distintos (com 'DESIGNAÇÃO')", value=membros_designacao)

        # Contagem por mês + gráfico compacto
        qtd_designacao_mes = (
            df_designacao.groupby("ano_mes", as_index=False)
            .size()
            .rename(columns={"size": "quantidade"})
        )
        qtd_designacao_mes["ord"] = pd.to_datetime(qtd_designacao_mes["ano_mes"], errors="coerce")
        qtd_designacao_mes = qtd_designacao_mes.sort_values(["ord", "ano_mes"]).drop(columns=["ord"])

        #try:
        #    import altair as alt
        #    chart_desig = (
        #        alt.Chart(qtd_designacao_mes)
        #        .mark_bar(color="#A0CBE8")
        #        .encode(
        #            x=alt.X("ano_mes:N", title="Mês (AAAA-MM)"),
        #            y=alt.Y("quantidade:Q", title="Qtd. 'DESIGNAÇÃO'"),
        #            tooltip=["ano_mes", "quantidade"]
        #        )
        #        .properties(title="DESIGNAÇÃO por mês", width="container", height=180)  # gráfico menor
        #    )
        #    st.altair_chart(chart_desig, use_container_width=True)
        #except Exception:
        #    st.bar_chart(qtd_designacao_mes.set_index("ano_mes"))

# --- Tabela resumo ---
        st.markdown('<h3 style="font-size:0.95rem;line-height:1.2;margin:0 0 .5rem 0;">Resumo por mês</h3>', unsafe_allow_html=True)
        st.dataframe(qtd_designacao_mes, use_container_width=True)

    # -------------------- Análise: membro == 'VAGO' --------------------
    st.divider()
    st.markdown(
        '<h3 style="font-size:0.95rem;line-height:1.2;margin:0 0 .5rem 0;">🚫 Ocorrências com Órgão VAGO</h3>',
        unsafe_allow_html=True
    )

    df_vago = df_orgao.copy()
    if not df_vago.empty:
        df_vago["membro"] = df_vago["membro"].fillna("").str.strip()
        df_vago = df_vago[df_vago["membro"].str.upper() == "VAGO"]
    else:
        df_vago = pd.DataFrame([])

    if df_vago.empty:
        st.info("Não há ocorrências com membro igual a 'VAGO'.")
    else:
        # Normaliza 'mes' -> 'ano_mes'
        df_vago["ano_mes"] = (
            pd.to_datetime(df_vago["mes"], errors="coerce")
            .dt.to_period("M").astype(str)
        )
        df_vago["ano_mes"] = df_vago["ano_mes"].mask(
            df_vago["ano_mes"].isin(["NaT", "nan"]),
            df_vago["mes"]
        )

        # Métricas
        total_vago = len(df_vago)
        meses_vago = df_vago["ano_mes"].nunique()

        c1, c2 = st.columns(2)
        with c1:
            st.metric("Registros com membro 'VAGO'", value=total_vago)
        with c2:
            st.metric("Meses com 'VAGO'", value=meses_vago)

        # Contagem por mês + gráfico compacto
        qtd_vago_mes = (
            df_vago.groupby("ano_mes", as_index=False)
            .size()
            .rename(columns={"size": "quantidade"})
        )
        qtd_vago_mes["ord"] = pd.to_datetime(qtd_vago_mes["ano_mes"], errors="coerce")
        qtd_vago_mes = qtd_vago_mes.sort_values(["ord", "ano_mes"]).drop(columns=["ord"])

        #try:
        #    import altair as alt
        #    chart_vago = (
        #        alt.Chart(qtd_vago_mes)
        #        .mark_bar(color="#59A14F")
        #        .encode(
        #            x=alt.X("ano_mes:N", title="Mês (AAAA-MM)"),
        #            y=alt.Y("quantidade:Q", title="Qtd. membro 'VAGO'"),
        #            tooltip=["ano_mes", "quantidade"]
        #        )
        #        .properties(title="VAGO por mês", width="container", height=180)  # gráfico menor
        #    )
        #    st.altair_chart(chart_vago, use_container_width=True)
        #except Exception:
        #    st.bar_chart(qtd_vago_mes.set_index("ano_mes"))

            # --- Tabela resumo ---
        st.markdown('<h3 style="font-size:0.95rem;line-height:1.2;margin:0 0 .5rem 0;">Resumo por mês</h3>', unsafe_allow_html=True)
        st.dataframe(qtd_vago_mes, use_container_width=True)