import pandas as pd
import streamlit as st
import json
from postgrest.exceptions import APIError
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
    "orgao_titular",
    "codigo_titular"
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
    df["data_sessao"] = (
        pd.to_datetime(df["data_sessao"])
        .dt.strftime("%Y-%m-%d")
    )
        
    banco["data_sessao"] = (
        pd.to_datetime(banco["data_sessao"])
        .dt.strftime("%Y-%m-%d")
    )

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

def importar(df):

    supabase = get_supabase()

    df = df.copy()

    # Datas
    for coluna in ["data_sessao", "validade"]:
        df[coluna] = (
            pd.to_datetime(df[coluna], errors="coerce")
            .dt.strftime("%Y-%m-%d")
        )

    # Inteiros
    for coluna in ["ano", "codigo_titular"]:
        df[coluna] = (
            pd.to_numeric(df[coluna], errors="coerce")
            .astype("Int64")
        )

    # Substitui NaN por None
    #df = df.replace({pd.NA: None, np.nan: None})
    #df = df.where(pd.notnull(df), None)
    df = df.astype(object).where(pd.notnull(df), None)

    for coluna in df.columns:

        if pd.api.types.is_integer_dtype(df[coluna]):
            df[coluna] = df[coluna].apply(
                    lambda x: int(x) if pd.notna(x) else None
        )

        elif pd.api.types.is_float_dtype(df[coluna]):
            df[coluna] = df[coluna].apply(
                    lambda x: float(x) if pd.notna(x) else None
        )

        else:
            df[coluna] = df[coluna].apply(
                    lambda x: None if pd.isna(x) else x
        )

    registros = df.to_dict("records")

    try:

        ultima_resposta = None
        
        for i in range(0, len(registros), LIMITE):
        
            lote = registros[i:i + LIMITE]
        
            ultima_resposta = (
                supabase
                .table(TABELA)
                #.insert(lote)
                .insert(
                    lote,
                    returning="representation"
                )
                .execute()
            )

        st.success("Importado com sucesso!")
        return ultima_resposta

    except APIError as e:

        st.error("Erro retornado pelo Supabase")

        st.write("Mensagem:")
        st.write(e.message)

        st.write("Detalhes:")
        st.write(e.details)

        st.write("Código:")
        st.write(e.code)

        st.write("Hint:")
        st.write(e.hint)

        raise

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
