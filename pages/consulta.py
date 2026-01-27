import io
import pandas as pd
import streamlit as st

from utils.helpers import (
    is_vago,
    normalize_str,
    ordenar_por_mes_e_designacao,
    consultar_membros_mes_outros_orgaos_pares,
    listar_orgaos_unicos,
    consultar_por_orgao,
)

def pagina_consulta():

    # st.title("🏛️ Consulta de Membros por Órgão")
    # st.caption("Selecione um Órgão. Em seguida, o app busca automaticamente onde os Membros aparecem no(s) mês(es).")
    # st.markdown(
    #     '<h3 style="font-size:0.95rem;line-height:1.2;margin:0 0 .5rem 0;">Filtro</h3>',
    #     unsafe_allow_html=True,
    # )

    orgaos = listar_orgaos_unicos()
    df_orgao = pd.DataFrame()  # evita NameError

    col1, col2 = st.columns([3, 1])

    with col1:
        if not orgaos:
            st.write(orgaos)
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
        # ---- Tabela 1: resultados do órgão selecionado ----
        df_orgao = consultar_por_orgao(orgao_sel)

        # st.subheader(f"Resultado: **{orgao_sel}**")
        st.markdown(
            f'<h3 style="font-size:1.1rem;margin:0;">Resultado: <strong>{orgao_sel}</strong></h3>',
            unsafe_allow_html=True,
        )
        if df_orgao.empty:
            st.info("Nenhum registro encontrado para este Órgão.")
        else:
            st.dataframe(df_orgao, use_container_width=True)

        # ---- Tabela 2: mesmos membros no(s) mesmo(s) mês(es) em outros órgãos (pareamento exato) ----
        st.markdown(
            '<h3 style="font-size:0.95rem;line-height:1.2;margin:0 0 .5rem 0;">🔁 Ocorrências em outros Órgãos</h3>',
            unsafe_allow_html=True,
        )

        df_outros = consultar_membros_mes_outros_orgaos_pares(df_orgao, orgao_sel)

        if df_outros.empty:
            st.info("Nenhuma ocorrência em outros Órgãos.")
        else:
            st.dataframe(df_outros, use_container_width=True)

        # -------------------- Downloads ÚNICOS --------------------
        st.divider()
        st.markdown(
            '<h3 style="font-size:0.95rem;line-height:1.2;margin:0 0 .5rem 0;">⬇️ Exportação consolidada</h3>',
            unsafe_allow_html=True,
        )

        # 1) CSV único com as duas tabelas empilhadas e coluna de origem
        df_orgao_com_tag = df_orgao.copy()
        df_orgao_com_tag["_tabela"] = "Tabela 1 - Órgão Selecionado"

        df_outros_com_tag = df_outros.copy()
        df_outros_com_tag["_tabela"] = "Tabela 2 - Outros Órgãos"

        df_consolidado = pd.concat(
            [df_orgao_com_tag, df_outros_com_tag], ignore_index=True, sort=False
        )

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
                use_container_width=True,
            )
        with col_dl_xlsx:
            st.download_button(
                label="⬇️ Baixar Excel (2 abas)",
                data=excel_buffer_all.getvalue(),
                file_name=f"consolidado_{orgao_sel}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )

        # -------------------- Análises de Auxílios --------------------
        st.divider()
        st.markdown(
            '<h3 style="font-size:0.95rem;line-height:1.2;margin:0 0 .5rem 0;">📊 Análises de Auxílios (Órgão selecionado)</h3>',
            unsafe_allow_html=True,
        )

        # Cópia defensiva e filtro por 'auxílio' na designação (case-insensitive, com e sem acento)
        df_auxilio = df_orgao.copy()
        if not df_auxilio.empty:
            df_auxilio["designacao"] = df_auxilio["designacao"].fillna("")
            mask_aux = df_auxilio["designacao"].str.contains(
                r"aux[ií]lio", case=False, regex=True
            )
            df_auxilio = df_auxilio[mask_aux].copy()
        else:
            df_auxilio = pd.DataFrame([])

        if df_auxilio.empty:
            st.info("Não há registros de auxílio para o Órgão selecionado.")
        else:
            # Normaliza 'mes' para 'ano_mes' (AAAA-MM) quando possível; senão, mantém o original
            # Tenta converter valores comuns (AAAA-MM, AAAA/MM, AAAA-MM-DD, DD/MM/AAAA, etc.)
            df_auxilio["ano_mes"] = (
                pd.to_datetime(df_auxilio["mes"], errors="coerce")
                .dt.to_period("M")
                .astype(str)
            )
            # Se não conseguiu converter (NaT), usa o valor original de 'mes'
            df_auxilio["ano_mes"] = df_auxilio["ano_mes"].mask(
                df_auxilio["ano_mes"].isin(["NaT", "nan"]), df_auxilio["mes"]
            )

            # --- Métricas rápidas ---
            total_reg_auxilio = len(df_auxilio)
            meses_com_auxilio = df_auxilio["ano_mes"].nunique()
            membros_distintos_auxilio = df_auxilio["membro"].nunique()

            colm1, colm2, colm3 = st.columns(3)
            with colm1:
                st.metric("Registros de auxílio", value=f"{total_reg_auxilio}")
            with colm2:
                st.metric(
                    "Meses com ocorrência de auxílio", value=f"{meses_com_auxilio}"
                )
            with colm3:
                st.metric(
                    "Membros distintos (com auxílio)",
                    value=f"{membros_distintos_auxilio}",
                )

            # --- Quantidade por mês ---
            qtd_por_mes = (
                df_auxilio.groupby("ano_mes", as_index=False)
                .size()
                .rename(columns={"size": "quantidade"})
            )

            # Ordena cronologicamente quando possível
            qtd_por_mes["ord"] = pd.to_datetime(qtd_por_mes["ano_mes"], errors="coerce")
            qtd_por_mes = qtd_por_mes.sort_values(
                ["ord", "ano_mes"], ascending=[True, True]
            ).drop(columns=["ord"])

            # --- Tabela resumo ---
            st.markdown(
                '<h3 style="font-size:0.95rem;line-height:1.2;margin:0 0 .5rem 0;">Resumo por mês</h3>',
                unsafe_allow_html=True,
            )
            st.dataframe(qtd_por_mes, use_container_width=True)

        # -------------------- Análise: designacao == 'DESIGNAÇÃO' --------------------
        st.divider()
        st.markdown(
            '<h3 style="font-size:0.95rem;line-height:1.2;margin:0 0 .5rem 0;">🧾 Ocorrências com Designação</h3>',
            unsafe_allow_html=True,
        )

        df_designacao = df_orgao.copy()
        if not df_designacao.empty:
            # Comparação exata, ignorando espaços/acento comuns
            df_designacao["designacao"] = (
                df_designacao["designacao"].fillna("").str.strip()
            )
            df_designacao = df_designacao[
                df_designacao["designacao"].str.upper() == "DESIGNAÇÃO"
            ]
        else:
            df_designacao = pd.DataFrame([])

        if df_designacao.empty:
            st.info("Não há ocorrências com designação igual a 'DESIGNAÇÃO'.")
        else:
            # Normaliza 'mes' -> 'ano_mes' (AAAA-MM), mantendo original quando não parseável
            df_designacao["ano_mes"] = (
                pd.to_datetime(df_designacao["mes"], errors="coerce")
                .dt.to_period("M")
                .astype(str)
            )
            df_designacao["ano_mes"] = df_designacao["ano_mes"].mask(
                df_designacao["ano_mes"].isin(["NaT", "nan"]), df_designacao["mes"]
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
                st.metric(
                    "Membros distintos (com 'DESIGNAÇÃO')", value=membros_designacao
                )

            # Contagem por mês + gráfico compacto
            qtd_designacao_mes = (
                df_designacao.groupby("ano_mes", as_index=False)
                .size()
                .rename(columns={"size": "quantidade"})
            )
            qtd_designacao_mes["ord"] = pd.to_datetime(
                qtd_designacao_mes["ano_mes"], errors="coerce"
            )
            qtd_designacao_mes = qtd_designacao_mes.sort_values(
                ["ord", "ano_mes"]
            ).drop(columns=["ord"])

            # --- Tabela resumo ---
            st.markdown(
                '<h3 style="font-size:0.95rem;line-height:1.2;margin:0 0 .5rem 0;">Resumo por mês</h3>',
                unsafe_allow_html=True,
            )
            st.dataframe(qtd_designacao_mes, use_container_width=True)

        # -------------------- Análise: membro == 'VAGO' --------------------
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
