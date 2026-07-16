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

    # Padroniza datas
    df["data_sessao"] = pd.to_datetime(df["data_sessao"]).dt.date
    banco["data_sessao"] = pd.to_datetime(banco["data_sessao"]).dt.date

    # Padroniza textos
    for col in ["sessao", "membro", "orgao_disponivel"]:
        df[col] = (
            df[col]
            .fillna("")
            .astype(str)
            .str.strip()
        )

        banco[col] = (
            banco[col]
            .fillna("")
            .astype(str)
            .str.strip()
        )

    banco["existe"] = True

    df = df.merge(
        banco[chave + ["existe"]],
        on=chave,
        how="left"
    )

    return df[df["existe"] != True].drop(columns="existe")
    
#def importar(df):

    #supabase = get_supabase()

    #df = df.copy()

    # Converte todas as colunas de data
    #for coluna in ["data_sessao", "validade"]:
    #    if coluna in df.columns:
    #        df[coluna] = (
    #            pd.to_datetime(df[coluna], errors="coerce")
    #            .dt.strftime("%Y-%m-%d")
    #        )

    # Troca NaN/NaT por None
    #df = df.where(pd.notnull(df), None)

    #registros = df.to_dict(orient="records")

    #resposta = (
    #    supabase
    #    .table("edital")
    #    .insert(registros)
    #    .execute()
    #)

    #return resposta

import json
import pandas as pd
import numpy as np
import streamlit as st

def importar(df):

    supabase = get_supabase()

    df = df.copy()

    # Converte colunas de data
    for col in ["data_sessao", "validade"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce").dt.strftime("%Y-%m-%d")

    # Converte todos os tipos numpy para tipos Python
    for col in df.columns:
        df[col] = df[col].apply(
            lambda x: (
                x.item() if isinstance(x, np.generic) else x
            )
        )

    # Substitui NaN/NaT por None
    df = df.where(pd.notnull(df), None)

    registros = df.to_dict(orient="records")

    # Descobre exatamente qual campo está causando o erro
    for i, registro in enumerate(registros):
        try:
            json.dumps(registro)
        except Exception as e:
            st.error(f"Erro na linha {i+1}")
            st.write(registro)
            st.exception(e)
            return

    st.success("JSON válido!")

    return (
        supabase
        .table("edital")
        .insert(registros)
        .execute()
    )

def pagina_import_edital():

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
