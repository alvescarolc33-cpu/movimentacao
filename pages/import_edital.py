import pandas as pd
import streamlit as st
from services.supabase_client import get_supabase

TABELA = "edital"

COLUNAS_OBRIGATORIAS = [
    "data_sessao",
    "sessao",
    "ano",
    "concurso",
    "cargo",
    "validade",
    "criterio",
    "orgao_disponivel",
    "membro",
    "orgao_titular"
]

CARGOS = [
    "Promotor de Justiça",
    "Procurador de Justiça"
]

CONCURSOS = [
    "Promoção",
    "Remoção"
]

def validar_dataframe(df):

    erros = []

    # Colunas obrigatórias
    faltando = set(COLUNAS_OBRIGATORIAS) - set(df.columns)

    if faltando:
        erros.append(
            f"Colunas ausentes: {', '.join(faltando)}"
        )
        return erros

    # Datas
    df["data_sessao"] = pd.to_datetime(
        df["data_sessao"],
        errors="coerce"
    )

    linhas = df[df["data_sessao"].isna()]

    if not linhas.empty:
        erros.append(
            f"{len(linhas)} datas inválidas."
        )

    # Cargo

    linhas = df[
        ~df["cargo"].isin(CARGOS)
    ]

    if not linhas.empty:
        erros.append(
            f"{len(linhas)} cargos inválidos."
        )

    # Concurso

    linhas = df[
        ~df["concurso"].isin(CONCURSOS)
    ]

    if not linhas.empty:
        erros.append(
            f"{len(linhas)} concursos inválidos."
        )

    # Campos vazios

    obrigatorios = [
        "data_sessao",
        "sessao",
        "membro",
        "orgao_disponivel"
    ]

    for campo in obrigatorios:

        linhas = df[df[campo].isna()]

        if not linhas.empty:
            erros.append(
                f"Campo '{campo}' possui {len(linhas)} valores vazios."
            )

    return erros

def remover_duplicados(df):

    supabase = get_supabase()

    resposta = (
        supabase
        .table(TABELA)
        .select(
            "data_sessao,sessao,membro,orgao_disponivel"
        )
        .execute()
    )

    banco = pd.DataFrame(resposta.data)

    if banco.empty:
        return df

    chave = [
        "data_sessao",
        "sessao",
        "membro",
        "orgao_disponivel"
    ]

    banco["existe"] = True

    df = df.merge(
        banco[chave + ["existe"]],
        on=chave,
        how="left"
    )

    return df[df["existe"] != True].drop(columns="existe")

def importar(df):

    supabase = get_supabase()

    registros = df.to_dict("records")

    resposta = (
        supabase
        .table(TABELA)
        .insert(registros)
        .execute()
    )

    return resposta

def pagina_importacao():

    st.title("📤 Importar Edital")

    arquivo = st.file_uploader(
        "Selecione o Excel",
        type=["xlsx"]
    )

    if arquivo is None:
        return

    df = pd.read_excel(arquivo)

    st.subheader("Prévia")

    st.dataframe(df.head())

    erros = validar_dataframe(df)

    if erros:

        st.error("Foram encontrados erros:")

        for erro in erros:
            st.write("•", erro)

        return

    df = remover_duplicados(df)

    st.success(
        f"{len(df)} registros prontos para importação."
    )

    if st.button("Importar para o Supabase"):

        importar(df)

        st.success("Importação concluída.")
