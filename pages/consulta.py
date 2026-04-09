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
    #Usa os membros e meses da Tabela 1 e busca todas as ocorrências em outros órgãos, mas só retorna registros que casem exatamente o PAR (membro, mes) da Tabela 1. Exclui sempre membro = 'VAGO'.

    if df_orgao.empty or "membro" not in df_orgao.columns or "mes" not in df_orgao.columns:
        return pd.DataFrame([])

    # Extrai pares (membro, mes) da Tabela 1, excluindo 'VAGO'
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

    # Consulta bruta no Supabase (limitada por conjuntos), excluindo o órgão selecionado e 'VAGO'
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

    # Normaliza os campos para comparação de pares
    df_raw["membro_norm"] = df_raw["membro"].apply(normalize_str)
    df_raw["mes_norm"] = df_raw["mes"].apply(normalize_str)
    df_raw["ano_norm"] = df_raw["ano"].astype(str).apply(normalize_str)

    # Conjunto de pares válidos da Tabela 1
    pairs_set = set(zip(df_pairs["membro_norm"], df_pairs["mes_norm"],df_pairs["ano_norm"]))

    # Filtra mantendo apenas (membro, mes) que existam na Tabela 1
    df_outros = df_raw[df_raw.apply(lambda r: (r["membro_norm"], r["mes_norm"],r["ano_norm"]) in pairs_set, axis=1)].copy()
    
    # Garante ordem e remove colunas auxiliares
    cols = [c for c in ["ano", "mes", "membro", "designacao", "orgao", "observacao"] if c in df_outros.columns]
    df_outros = df_outros[cols]

    #Ordena pela ordem customizada
    df_outros = ordenar_por_mes_e_designacao(df_outros)

    df_outros.reset_index(drop=True, inplace=True)
    return df_outros

# --------------------------- Interface Página

def pagina_consulta():
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
        # spacer para alinhar verticalmente o botão com o selectbox
        st.write("")  # primeira linha vazia
        st.write("")  # segunda linha vazia (ajusta a altura)
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

        # -------------------- Garantir mesma estrutura
        df_orgao["tipo"] = "orgao"
        df_outros["tipo"] = "outros"

        # -------------------- Juntar tudo
        df_all = pd.concat([df_orgao, df_outros], ignore_index=True)

        # -------------------- Ordenar meses corretamente
        ordem_meses = [
            "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
            "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"
        ]

        df_all["mes"] = pd.Categorical(
            df_all["mes"],
            categories=ordem_meses,
            ordered=True
        )

        # -------------------- Montar tabela final
        lista_final = []

        for (ano, mes), grupo in df_all.groupby(["ano", "mes"], sort=True):
            g_orgao = grupo[grupo["tipo"] == "orgao"]
            g_outros = grupo[grupo["tipo"] == "outros"]

            lista_final.append(g_orgao)

            if not g_outros.empty:
                lista_final.append(g_outros)

        # IMPORTANTE: manter "tipo" para formatação
        df_final = pd.concat(lista_final, ignore_index=True)

        # -------------------- Gerar Excel
        excel_buffer_all = io.BytesIO()

        with pd.ExcelWriter(excel_buffer_all, engine="xlsxwriter") as writer:
            df_final.to_excel(writer, index=False, sheet_name="Consolidado")

            workbook = writer.book
            worksheet = writer.sheets["Consolidado"]

            format_orgao = workbook.add_format({"bg_color": "#FFFFFF"})
            format_outros = workbook.add_format({"bg_color": "#FAFAFD"})

            # Aplicar cores por linha
            for i, tipo in enumerate(df_final["tipo"], start=1):  # start=1 por causa do header
                fmt = format_orgao if tipo == "orgao" else format_outros
                worksheet.set_row(i, cell_format=fmt)

        # Remover coluna tipo APÓS formatação (opcional)
        df_final = df_final.drop(columns="tipo")

        excel_buffer_all.seek(0)

        st.download_button(
            label="📥 Baixar Excel Consolidado",
            data=excel_buffer_all,
            file_name="consolidado.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)

        # 1) CSV único com as duas tabelas empilhadas e coluna de origem
        #df_orgao_com_tag = df_orgao.copy()
        #df_orgao_com_tag["_tabela"] = "Tabela 1 - Órgão Selecionado"

        #df_outros_com_tag = df_outros.copy()
        #df_outros_com_tag["_tabela"] = "Tabela 2 - Outros Órgãos"

        #df_consolidado = pd.concat(
        #    [df_orgao_com_tag, df_outros_com_tag], ignore_index=True, sort=False
        #)

        #csv_bytes_all = df_consolidado.to_csv(index=False).encode("utf-8")

        # 2) Excel único com duas abas (mais organizado para leitura)
        #excel_buffer_all = io.BytesIO()
        #with pd.ExcelWriter(excel_buffer_all, engine="xlsxwriter") as writer:
        #    # Se quiser preservar o DataFrame original sem a coluna `_tabela`:
        #    df_orgao.to_excel(writer, index=False, sheet_name="Órgão Selecionado")
        #    df_outros.to_excel(writer, index=False, sheet_name="Outros Órgãos")

            # Opcional: também incluir a aba consolidada com a coluna `_tabela`
            # df_consolidado.to_excel(writer, index=False, sheet_name="Consolidado")

        #excel_buffer_all.seek(0)

        #col_dl_csv, col_dl_xlsx = st.columns(2)
        #with col_dl_csv:
        #    st.download_button(
        #        label="⬇️ Baixar CSV (Consolidado)",
        #        data=csv_bytes_all,
        #        file_name=f"consolidado_{orgao_sel}.csv",
        #        mime="text/csv",
        #        use_container_width=True,
        #    )
        #with col_dl_xlsx:
        #    st.download_button(
        #        label="⬇️ Baixar Excel (2 abas)",
        #        data=excel_buffer_all.getvalue(),
        #        file_name=f"consolidado_{orgao_sel}.xlsx",
        #        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        #        use_container_width=True,
        #    )

        # -------------------- Análises de Auxílios

        st.divider()

        st.markdown(
            '<h3 style="font-size:0.95rem;line-height:1.2;margin:0 0 .5rem 0;">📊 Análises de Auxílios</h3>',
            unsafe_allow_html=True,
        )

        df_auxilio = df_orgao.copy()

        # -------------------- Filtro de auxílio
        if not df_auxilio.empty:
            df_auxilio["designacao"] = df_auxilio["designacao"].fillna("")

            # MAIS FLEXÍVEL (evita perder registros)
            mask_aux = df_auxilio["designacao"].str.contains(
                r"aux", case=False, na=False
            )

            df_auxilio = df_auxilio[mask_aux].copy()
        else:
            df_auxilio = pd.DataFrame([])

        if df_auxilio.empty:
            st.info("Não há registros de auxílio para o Órgão selecionado.")
        else:
            df_auxilio = df_auxilio.dropna(subset=["ano", "mes"])

            # Converter mês (aceita número, texto, etc.)
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
                # -------------------- Métricas
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

                # -------------------- Agrupamento por mês
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
            '<h3 style="font-size:0.95rem;line-height:1.2;margin:0 0 .5rem 0;">🧾 Ocorrências com Designação/Designação Temporária</h3>',
            unsafe_allow_html=True,
        )

        df_designacao = df_orgao.copy()

        # -------------------- Filtro
        if not df_designacao.empty:
            df_designacao["designacao"] = df_designacao["designacao"].fillna("")

            mask_desig = df_designacao["designacao"].str.contains(
                r"designa", case=False, na=False
            )

            df_designacao = df_designacao[mask_desig].copy()
        else:
            df_designacao = pd.DataFrame([])

        # -------------------- Verificação
        if df_designacao.empty:
            st.info("Não há ocorrências com designação para o Órgão selecionado.")
        else:
            df_designacao = df_designacao.dropna(subset=["ano", "mes"])

            # -------------------- Tratamento de mês
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

            # -------------------- Data
            df_designacao["ano_mes"] = pd.to_datetime(
                df_designacao["ano"] + "-" + df_designacao["mes"],
                errors="coerce"
            )

            df_designacao = df_designacao[df_designacao["ano_mes"].notna()]

            if df_designacao.empty:
                st.warning("Os dados de designação existem, mas possuem datas inválidas.")
            else:
                # -------------------- Métricas
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

                # -------------------- Agrupamento
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

        # -------------------- Análise: designacao == 'DESIGNAÇÃO'
    #    st.divider()
    #    st.markdown(
    #        '<h3 style="font-size:0.95rem;line-height:1.2;margin:0 0 .5rem 0;">🧾 Ocorrências com Designação</h3>',
    #        unsafe_allow_html=True,
    #    )

    #    df_designacao = df_orgao.copy()
    #    if not df_designacao.empty:
            # Comparação exata, ignorando espaços/acento comuns
    #        df_designacao["designacao"] = (
    #            df_designacao["designacao"].fillna("").str.strip()
    #        )
    #        df_designacao = df_designacao[
    #            df_designacao["designacao"].str.upper() == "DESIGNAÇÃO"
    #        ]
    #    else:
    #        df_designacao = pd.DataFrame([])

    #    if df_designacao.empty:
    #        st.info("Não há ocorrências com designação igual a 'DESIGNAÇÃO'.")
    #    else:
            # Normaliza 'mes' -> 'ano_mes' (AAAA-MM), mantendo original quando não parseável
    #        df_designacao["ano_mes"] = (
    #            pd.to_datetime(df_designacao["mes"], errors="coerce")
    #            .dt.to_period("M")
    #            .astype(str)
    #        )
    #        df_designacao["ano_mes"] = df_designacao["ano_mes"].mask(
    #            df_designacao["ano_mes"].isin(["NaT", "nan"]), df_designacao["mes"]
    #        )

            # Métricas
    #        total_designacao = len(df_designacao)
    #        meses_designacao = df_designacao["ano_mes"].nunique()
    #        membros_designacao = df_designacao["membro"].nunique()

    #        c1, c2, c3 = st.columns(3)
    #        with c1:
    #            st.metric("Registros 'DESIGNAÇÃO'", value=total_designacao)
    #        with c2:
    #            st.metric("Meses com 'DESIGNAÇÃO'", value=meses_designacao)
    #        with c3:
    #            st.metric(
    #                "Membros distintos (com 'DESIGNAÇÃO')", value=membros_designacao
    #            )

            # Contagem por mês + gráfico compacto
    #        qtd_designacao_mes = (
    #            df_designacao.groupby("ano_mes", as_index=False)
    #            .size()
    #            .rename(columns={"size": "quantidade"})
    #        )
    #        qtd_designacao_mes["ord"] = pd.to_datetime(
    #            qtd_designacao_mes["ano_mes"], errors="coerce"
    #        )
    #        qtd_designacao_mes = qtd_designacao_mes.sort_values(
    #            ["ord", "ano_mes"]
    #        ).drop(columns=["ord"])

            # --- Tabela resumo ---
    #        st.markdown(
    #            '<h3 style="font-size:0.95rem;line-height:1.2;margin:0 0 .5rem 0;">Resumo por mês</h3>',
    #            unsafe_allow_html=True,
    #        )
    #        st.dataframe(qtd_designacao_mes, use_container_width=True)

        # -------------------- Análise: membro == 'VAGO'
        st.divider()
        st.markdown(
            '<h3 style="font-size:0.95rem;line-height:1.2;margin:0 0 .5rem 0;">🚫 Ocorrências com Órgão VAGO</h3>',
            unsafe_allow_html=True,
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
                .dt.to_period("M")
                .astype(str)
            )
            df_vago["ano_mes"] = df_vago["ano_mes"].mask(
                df_vago["ano_mes"].isin(["NaT", "nan"]), df_vago["mes"]
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
            qtd_vago_mes["ord"] = pd.to_datetime(
                qtd_vago_mes["ano_mes"], errors="coerce"
            )
            qtd_vago_mes = qtd_vago_mes.sort_values(["ord", "ano_mes"]).drop(
                columns=["ord"]
            )

            # --- Tabela resumo ---
            st.markdown(
                '<h3 style="font-size:0.95rem;line-height:1.2;margin:0 0 .5rem 0;">Resumo por mês</h3>',
                unsafe_allow_html=True,
            )
            st.dataframe(qtd_vago_mes, use_container_width=True)