import io
import pandas as pd
import streamlit as st
from services.supabase_client import get_supabase
from utils.helpers import is_vago, normalize_str
import xlsxwriter

# -------------------- ORDENAMENTO

ANO_MAP = {
    "2026": 1, "2025": 2, "2024": 3, "2023": 4
}

MESES_MAP = {
    "Janeiro": 1, "Fevereiro": 2, "Março": 3, "Abril": 4,
    "Maio": 5, "Junho": 6, "Julho": 7, "Agosto": 8,
    "Setembro": 9, "Outubro": 10, "Novembro": 11, "Dezembro": 12
}

DESIGNACAO_MAP = {
    "TITULAR": 1,
    "DESIGNAÇÃO TEMPORÁRIA": 2,
    "DESIGNAÇÃO": 3,
    "AUXÍLIO": 4,
    "AUXÍLIO TEMPORÁRIO": 5,
}

def ordenar_por_mes_e_designacao(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df

    df = df.copy()

    if "ano" in df.columns:
        df["__ano_ord__"] = df["ano"].astype(str).map(ANO_MAP).fillna(999)

    if "mes" in df.columns:
        df["__mes_ord__"] = df["mes"].map(MESES_MAP).fillna(999)

    if "designacao" in df.columns:
        df["__des_ord__"] = df["designacao"].map(DESIGNACAO_MAP).fillna(999)

    sort_cols = []
    ascending = []

    if "__ano_ord__" in df.columns:
        sort_cols.append("__ano_ord__"); ascending.append(True)
    
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

    df.drop(columns=[c for c in ["__ano_ord__", "__mes_ord__", "__des_ord__"] if c in df.columns], inplace=True)

    return df

def mostrar_erro(ex: Exception, contexto: str = ""):
    st.error(f"❌ Ocorreu um erro {('em ' + contexto) if contexto else ''}: {ex}")

def listar_orgaos_unicos():
    try:
        supabase = get_supabase()
        res = supabase.table("orgaos_distintos").select("orgao").order("orgao").execute()
        dados = [r["orgao"] for r in res.data or []]
        if not dados:
            st.warning("⚠️ Nenhum órgão encontrado na tabela 'orgaos_distintos'")
        return dados
    except Exception as e:
        mostrar_erro(e, "ao listar órgãos")
        return []

def consultar_por_orgao(orgao: str) -> pd.DataFrame:
    try:
        supabase = get_supabase()
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

        df = ordenar_por_mes_e_designacao(df)
        return df

    except Exception as ex:
        mostrar_erro(ex, "na consulta por órgão")
        return pd.DataFrame([])

def consultar_membros_mes_outros_orgaos_pares(df_orgao: pd.DataFrame, orgao_sel: str) -> pd.DataFrame:
    supabase = get_supabase()

    if df_orgao.empty or "membro" not in df_orgao.columns or "mes" not in df_orgao.columns:
        return pd.DataFrame([])

    df_pairs = df_orgao.copy()
    df_pairs["membro_norm"] = df_pairs["membro"].apply(normalize_str)
    df_pairs["mes_norm"] = df_pairs["mes"].apply(normalize_str)
    df_pairs = df_pairs[~df_pairs["membro_norm"].apply(is_vago)]
    df_pairs["ano_norm"] = df_pairs["ano"].astype(str).apply(normalize_str)

    membros = sorted(df_pairs["membro_norm"].dropna().unique().tolist())
    meses = sorted(df_pairs["mes_norm"].dropna().unique().tolist())
    anos = sorted(df_pairs["ano_norm"].dropna().unique().tolist())

    if not membros or not meses:
        return pd.DataFrame([])

    q = (
        supabase
        .table("movimentacao")
        .select("mes, ano, orgao, cod_orgao, membro, designacao, observacao")
        .in_("membro", membros)
        .in_("mes", meses)
        .in_("ano", anos)
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

    df_raw["membro_norm"] = df_raw["membro"].apply(normalize_str)
    df_raw["mes_norm"] = df_raw["mes"].apply(normalize_str)
    df_raw["ano_norm"] = df_raw["ano"].astype(str).apply(normalize_str)

    pairs_set = set(zip(df_pairs["membro_norm"], df_pairs["mes_norm"],df_pairs["ano_norm"]))

    df_outros = df_raw[df_raw.apply(lambda r: (r["membro_norm"], r["mes_norm"],r["ano_norm"]) in pairs_set, axis=1)].copy()
    
    cols = [c for c in ["ano", "mes", "membro", "designacao", "orgao", "observacao"] if c in df_outros.columns]
    df_outros = df_outros[cols]

    df_outros = ordenar_por_mes_e_designacao(df_outros)

    df_outros.reset_index(drop=True, inplace=True)
    return df_outros

# --------------------------- Interface Página

def pagina_consulta():
    st.title("📊 Análise de Movimentações")
    orgaos = listar_orgaos_unicos()
    df_orgao = pd.DataFrame()

    col1, col2 = st.columns([3, 1])

    with col1:
        if not orgaos:
            st.warning("Não há Órgãos cadastrados ou houve erro ao carregar a lista.")
            orgao_sel = None
        else:
            orgao_sel = st.selectbox(
                "Órgão/Promotoria", options=orgaos, index=0, key="orgao_sel_top"
            )

    with col2:
        st.write("")
        st.write("")
        consultar = st.button("🔎 Consultar", use_container_width=True)

    if consultar and orgao_sel:
        # ---- Tabela 1: resultados do órgão selecionado
        df_orgao = consultar_por_orgao(orgao_sel)
        st.markdown(
            f'<h3 style="font-size:1.1rem;margin:0;">Resultado: <strong>{orgao_sel}</strong></h3>',
            unsafe_allow_html=True,
        )
        if df_orgao.empty:
            st.info("Nenhum registro encontrado para este Órgão.")
        else:
            st.dataframe(df_orgao, use_container_width=True)

        # ---- Tabela 2: mesmos membros no(s) mesmo(s) mês(es) em outros órgãos (pareamento exato)
        st.markdown(
            '<h3 style="font-size:0.95rem;line-height:1.2;margin:0 0 .5rem 0;">🔁 Ocorrências em outros Órgãos</h3>',
            unsafe_allow_html=True,
        )

        df_outros = consultar_membros_mes_outros_orgaos_pares(df_orgao, orgao_sel)

        if df_outros.empty:
            st.info("Nenhuma ocorrência em outros Órgãos.")
        else:
            st.dataframe(df_outros, use_container_width=True)

        # -------------------- Downloads ÚNICOS
        st.divider()
        st.markdown(
            '<h3 style="font-size:0.95rem;line-height:1.2;margin:0 0 .5rem 0;">⬇️ Exportação consolidada</h3>',
            unsafe_allow_html=True,
        )

        df_orgao["tipo"] = "orgao"
        df_outros["tipo"] = "outros"

        df_all = pd.concat([df_orgao, df_outros], ignore_index=True)

        ordem_meses = [
            "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
            "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"
        ]

        df_all["mes"] = pd.Categorical(
            df_all["mes"],
            categories=ordem_meses,
            ordered=True
        )

        lista_final = []

        for (ano, mes), grupo in df_all.groupby(["ano", "mes"], sort=True):
            g_orgao = grupo[grupo["tipo"] == "orgao"]
            g_outros = grupo[grupo["tipo"] == "outros"]

            lista_final.append(g_orgao)

            if not g_outros.empty:
                lista_final.append(g_outros)

        df_final = pd.concat(lista_final, ignore_index=True)

        excel_buffer_all = io.BytesIO()

        with pd.ExcelWriter(excel_buffer_all, engine="xlsxwriter") as writer:
            df_final.to_excel(writer, index=False, sheet_name="Consolidado")

            workbook = writer.book
            worksheet = writer.sheets["Consolidado"]

            format_orgao = workbook.add_format({"bg_color": "#FFFFFF"})
            format_outros = workbook.add_format({"bg_color": "#FAFAFD"})

            for i, tipo in enumerate(df_final["tipo"], start=1):
                fmt = format_orgao if tipo == "orgao" else format_outros
                worksheet.set_row(i, cell_format=fmt)

        df_final = df_final.drop(columns="tipo")

        excel_buffer_all.seek(0)

        st.download_button(
            label="📥 Baixar Excel Consolidado",
            data=excel_buffer_all,
            file_name="consolidado.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)

        # -------------------- Análises de Auxílios

        st.divider()

        st.markdown(
            '<h3 style="font-size:0.95rem;line-height:1.2;margin:0 0 .5rem 0;">📊 Ocorrências de Auxílio</h3>',
            unsafe_allow_html=True,
        )

        df_auxilio = df_orgao.copy()

        if not df_auxilio.empty:
            df_auxilio["designacao"] = df_auxilio["designacao"].fillna("")

            mask_aux = df_auxilio["designacao"].str.strip().str.upper() == "AUXÍLIO"

            df_auxilio = df_auxilio[mask_aux].copy()
        else:
            df_auxilio = pd.DataFrame([])

        if df_auxilio.empty:
            st.info("Não há registros de auxílio para o Órgão selecionado.")
        else:
            df_auxilio = df_auxilio.dropna(subset=["ano", "mes"])

            mes_map = {
                "jan": "01", "janeiro": "01",
                "fev": "02", "fevereiro": "02",
                "mar": "03", "março": "03", "marco": "03",
                "abr": "04", "abril": "04",
                "mai": "05", "maio": "05",
                "jun": "06", "junho": "06",
                "jul": "07", "julho": "07",
                "ago": "08", "agosto": "08",
                "set": "09", "setembro": "09",
                "out": "10", "outubro": "10",
                "nov": "11", "novembro": "11",
                "dez": "12", "dezembro": "12"
            }

            df_auxilio["mes"] = (
                df_auxilio["mes"]
                .astype(str)
                .str.lower()
                .str.strip()
                .replace(mes_map)
            )

            df_auxilio["mes"] = df_auxilio["mes"].str.extract(r"(\d+)")[0]
            df_auxilio["mes"] = df_auxilio["mes"].str.zfill(2)

            df_auxilio["ano"] = df_auxilio["ano"].astype(str).str.extract(r"(\d{4})")[0]

            df_auxilio["ano_mes"] = pd.to_datetime(
                df_auxilio["ano"] + "-" + df_auxilio["mes"],
                errors="coerce"
            )

            df_auxilio = df_auxilio[df_auxilio["ano_mes"].notna()]

            if df_auxilio.empty:
                st.warning("Os dados de auxílio existem, mas possuem datas inválidas.")
            else:
                total_reg_auxilio = len(df_auxilio)
                meses_com_auxilio = df_auxilio["ano_mes"].dt.to_period("M").nunique()
                membros_distintos_auxilio = df_auxilio["membro"].nunique()

                colm1, colm2, colm3 = st.columns(3)

                with colm1:
                    st.metric("Auxílios concedidos", value=total_reg_auxilio)

                with colm2:
                    st.metric(
                        "Quantidade de Meses com Auxílio",
                        value=meses_com_auxilio
                    )

                with colm3:
                    st.metric(
                        "Membros distintos",
                        value=membros_distintos_auxilio
                    )

                df_auxilio["ano_mes_str"] = df_auxilio["ano_mes"].dt.to_period("M").astype(str)

                qtd_por_mes = (
                    df_auxilio.groupby("ano_mes_str")
                    .size()
                    .reset_index(name="quantidade")
                )

                qtd_por_mes["ord"] = pd.to_datetime(qtd_por_mes["ano_mes_str"], errors="coerce")
                qtd_por_mes = qtd_por_mes.sort_values("ord")

                qtd_por_mes["ano"] = qtd_por_mes["ord"].dt.year
                qtd_por_mes["mes"] = qtd_por_mes["ord"].dt.month.astype(str).str.zfill(2)

                qtd_por_mes = qtd_por_mes[["ano", "mes", "quantidade"]]

                # -------------------- Tabela
                st.markdown(
                    '<h3 style="font-size:0.95rem;line-height:1.2;margin:0 0 .5rem 0;">Resumo por mês</h3>',
                    unsafe_allow_html=True,
                )

                st.dataframe(qtd_por_mes, use_container_width=True)

        # -------------------- Análise: Designação
        st.divider()

        st.markdown(
            '<h3 style="font-size:0.95rem;line-height:1.2;margin:0 0 .5rem 0;">🧾 Ocorrências de Designação</h3>',
            unsafe_allow_html=True,
        )

        df_designacao = df_orgao.copy()

        # -------------------- Filtro
        if not df_designacao.empty:
            df_designacao["designacao"] = df_designacao["designacao"].fillna("")

            mask_desig = df_designacao["designacao"].str.strip().str.upper() == "DESIGNAÇÃO"

            df_designacao = df_designacao[mask_desig].copy()
        else:
            df_designacao = pd.DataFrame([])

        if df_designacao.empty:
            st.info("Não há ocorrências com designação para o Órgão selecionado.")
        else:
            df_designacao = df_designacao.dropna(subset=["ano", "mes"])

            mes_map = {
                "jan": "01", "janeiro": "01",
                "fev": "02", "fevereiro": "02",
                "mar": "03", "março": "03", "marco": "03",
                "abr": "04", "abril": "04",
                "mai": "05", "maio": "05",
                "jun": "06", "junho": "06",
                "jul": "07", "julho": "07",
                "ago": "08", "agosto": "08",
                "set": "09", "setembro": "09",
                "out": "10", "outubro": "10",
                "nov": "11", "novembro": "11",
                "dez": "12", "dezembro": "12"
            }

            df_designacao["mes"] = (
                df_designacao["mes"]
                .astype(str)
                .str.lower()
                .str.strip()
                .replace(mes_map)
            )

            df_designacao["mes"] = df_designacao["mes"].str.extract(r"(\d+)")[0]
            df_designacao["mes"] = df_designacao["mes"].str.zfill(2)

            df_designacao["ano"] = df_designacao["ano"].astype(str).str.extract(r"(\d{4})")[0]

            df_designacao["ano_mes"] = pd.to_datetime(
                df_designacao["ano"] + "-" + df_designacao["mes"],
                errors="coerce"
            )

            df_designacao = df_designacao[df_designacao["ano_mes"].notna()]

            if df_designacao.empty:
                st.warning("Os dados de designação existem, mas possuem datas inválidas.")
            else:
                total_reg_designacao = len(df_designacao)
                meses_com_designacao = df_designacao["ano_mes"].dt.to_period("M").nunique()
                membros_distintos_designacao = df_designacao["membro"].nunique()

                colm1, colm2, colm3 = st.columns(3)

                with colm1:
                    st.metric("Designações concedidas", value=total_reg_designacao)

                with colm2:
                    st.metric(
                        "Quantidade de Meses com Designação",
                        value=meses_com_designacao
                    )

                with colm3:
                    st.metric(
                        "Membros distintos",
                        value=membros_distintos_designacao
                    )

                df_designacao["ano_mes_str"] = df_designacao["ano_mes"].dt.to_period("M").astype(str)

                qtd_por_mes_designacao = (
                    df_designacao.groupby("ano_mes_str")
                    .size()
                    .reset_index(name="quantidade")
                )

                qtd_por_mes_designacao["ord"] = pd.to_datetime(
                    qtd_por_mes_designacao["ano_mes_str"], errors="coerce"
                )

                qtd_por_mes_designacao = qtd_por_mes_designacao.sort_values("ord")

                qtd_por_mes_designacao["ano"] = qtd_por_mes_designacao["ord"].dt.year
                qtd_por_mes_designacao["mes"] = qtd_por_mes_designacao["ord"].dt.month.astype(str).str.zfill(2)

                qtd_por_mes_designacao = qtd_por_mes_designacao[["ano", "mes", "quantidade"]]

                # -------------------- Tabela
                st.markdown(
                    '<h3 style="font-size:0.95rem;line-height:1.2;margin:0 0 .5rem 0;">Resumo por mês</h3>',
                    unsafe_allow_html=True,
                )

                st.dataframe(qtd_por_mes_designacao, use_container_width=True)

        # -------------------- Análise: NOVO VAGO
        st.divider()

        st.markdown(
            '<h3 style="font-size:0.95rem;line-height:1.2;margin:0 0 .5rem 0;">🚫 Ocorrências de Vacância</h3>',
            unsafe_allow_html=True,
        )

        df_vagos = df_orgao.copy()

        if not df_vagos.empty:
            df_vagos["membro"] = df_vagos["membro"].astype(str).fillna("")

            mask_vagos = df_vagos["membro"].str.contains(
                r"VAGO", case=False, na=False
            )

            df_vagos = df_vagos[mask_vagos].copy()
        else:
            df_vagos = pd.DataFrame([])

        if df_vagos.empty:
            st.info("Não há ocorrências de vacância para o Órgão selecionado.")
        else:
            df_vagos = df_vagos.dropna(subset=["ano", "mes"])

            mes_map = {
                "jan": "01", "janeiro": "01",
                "fev": "02", "fevereiro": "02",
                "mar": "03", "março": "03", "marco": "03",
                "abr": "04", "abril": "04",
                "mai": "05", "maio": "05",
                "jun": "06", "junho": "06",
                "jul": "07", "julho": "07",
                "ago": "08", "agosto": "08",
                "set": "09", "setembro": "09",
                "out": "10", "outubro": "10",
                "nov": "11", "novembro": "11",
                "dez": "12", "dezembro": "12"
            }

            df_vagos["mes"] = (
                df_vagos["mes"]
                .astype(str)
                .str.lower()
                .str.strip()
                .replace(mes_map)
            )

            df_vagos["mes"] = df_vagos["mes"].str.extract(r"(\d+)")[0]
            df_vagos["mes"] = df_vagos["mes"].str.zfill(2)

            df_vagos["ano"] = (
                df_vagos["ano"]
                .astype(str)
                .str.extract(r"(\d{4})")[0]
            )

            df_vagos = df_vagos[df_vagos["ano"].notna()]

            df_vagos["ano_mes"] = pd.to_datetime(
                df_vagos["ano"] + "-" + df_vagos["mes"],
                errors="coerce"
            )

            df_vagos = df_vagos[df_vagos["ano_mes"].notna()]

            if df_vagos.empty:
                st.warning("Os dados de vacância existem, mas possuem datas inválidas.")
            else:
                total_reg_vagos = len(df_vagos)
                meses_com_vagos = df_vagos["ano_mes"].dt.to_period("M").nunique()
                membros_distintos_vagos = df_vagos["membro"].nunique()

                col1, = st.columns(1)

                with col1:
                    st.metric("Meses Vagos", meses_com_vagos)

                df_vagos["ano_mes_str"] = df_vagos["ano_mes"].dt.to_period("M").astype(str)

                # -------------------- Agrupamento por ANO (quantos meses vagos)
                df_vagos["ano"] = df_vagos["ano_mes"].dt.year
                df_vagos["mes"] = df_vagos["ano_mes"].dt.month

                qtd_por_ano_vagos = (
                    df_vagos.groupby("ano")["mes"]
                    .nunique()  # 👈 conta meses distintos
                    .reset_index(name="qtd_meses_vagos")
                )

                qtd_por_ano_vagos = qtd_por_ano_vagos.sort_values("ano")

                st.markdown(
                    '<h3 style="font-size:0.95rem;line-height:1.2;margin:0 0 .5rem 0;">Meses vagos por ano</h3>',
                    unsafe_allow_html=True,
                )

                st.dataframe(qtd_por_ano_vagos, use_container_width=True)

        # -------------------- Análise: Repetição de Membros (Tabela 2)
        st.divider()

        st.markdown(
            '<h3 style="font-size:0.95rem;line-height:1.2;margin:0 0 .5rem 0;">🔁 Repetição de Membros (Outros Órgãos)</h3>',
            unsafe_allow_html=True,
        )

        if "membro" in df_outros.columns:

            df_rep = df_outros.copy()
            df_rep["membro"] = df_rep["membro"].astype(str).str.strip()

            # -------------------- Filtros
            colf1, colf2 = st.columns(2)

            with colf1:
                anos = ["Todos"] + sorted(df_rep["ano"].dropna().astype(str).unique().tolist())
                ano_sel = st.selectbox("Filtrar por Ano", anos, key="filtro_ano_outros")

            # --------- MÊS DEPENDENTE DO ANO
            with colf2:
                if ano_sel == "Todos":
                    df_mes_base = df_rep.copy()
                else:
                    df_mes_base = df_rep[df_rep["ano"].astype(str) == ano_sel]

                #meses = ["Todos"] + sorted(
                #    df_mes_base["mes"].dropna().astype(str).unique().tolist()
                #)
                ordem_meses = {
                    "01": 1, "02": 2, "03": 3, "04": 4,
                    "05": 5, "06": 6, "07": 7, "08": 8,
                    "09": 9, "10": 10, "11": 11, "12": 12
                }

                meses = ["Todos"] + sorted(
                    df_mes_base["mes"].dropna().astype(str).unique().tolist(),
                    key=lambda x: ordem_meses.get(x, 99)
                )

                mes_sel = st.selectbox("Filtrar por Mês", meses, key="filtro_mes_outros")

            # -------------------- Aplicar filtros
            if ano_sel != "Todos":
                df_rep = df_rep[df_rep["ano"].astype(str) == ano_sel]

            if mes_sel != "Todos":
                df_rep = df_rep[df_rep["mes"].astype(str) == mes_sel]

            # -------------------- Verificação
            if df_rep.empty:
                st.info("Nenhum dado encontrado para os filtros selecionados.")
            else:
                # (opcional) remover VAGO
                df_rep = df_rep[~df_rep["membro"].str.upper().eq("VAGO")]

                repeticoes = (
                    df_rep["membro"]
                    .value_counts()
                    .reset_index()
                    .rename(columns={"index": "membro", "membro": "quantidade"})
                )

                repeticoes = repeticoes.sort_values(by="quantidade", ascending=False)

                # Métrica
                st.metric(
                    "Maior repetição",
                    value=repeticoes["quantidade"].max()
                )

                # Tabela
                st.dataframe(repeticoes, use_container_width=True)

        else:
            st.warning("Coluna 'membro' não encontrada na Tabela 2.")