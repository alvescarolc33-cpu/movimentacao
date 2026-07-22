import pandas as pd
import streamlit as st
#import json
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

    faltando = set(COLUNAS_OBRIGATORIAS) - set(df.columns)

    if faltando:
        erros.append(
            f"Colunas ausentes: {', '.join(faltando)}"
        )
        return erros

    df["data_sessao"] = pd.to_datetime(
        df["data_sessao"],
        errors="coerce"
    )

    linhas = df[df["data_sessao"].isna()]

    if not linhas.empty:
        erros.append(
            f"{len(linhas)} datas inválidas."
        )

    linhas = df[
        ~df["cargo"].isin(CARGOS)
    ]

    if not linhas.empty:
        erros.append(
            f"{len(linhas)} cargos inválidos."
        )

    linhas = df[
        ~df["concurso"].isin(CONCURSOS)
    ]

    if not linhas.empty:
        erros.append(
            f"{len(linhas)} concursos inválidos."
        )

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

    df["data_sessao"] = (
        pd.to_datetime(df["data_sessao"])
        .dt.strftime("%Y-%m-%d")
    )
        
    banco["data_sessao"] = (
        pd.to_datetime(banco["data_sessao"])
        .dt.strftime("%Y-%m-%d")
    )

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

    for coluna in ["data_sessao", "validade"]:
        df[coluna] = (
            pd.to_datetime(df[coluna], errors="coerce")
            .dt.strftime("%Y-%m-%d")
        )

    for coluna in ["ano", "codigo_titular"]:
        df[coluna] = (
            pd.to_numeric(df[coluna], errors="coerce")
            .apply(lambda x: None if pd.isna(x) else int(x))
        )

    df = df.where(pd.notnull(df), None)

    #st.write(df.dtypes)
    #st.write(type(df.iloc[0]["codigo_titular"]))
    #st.write(repr(df.iloc[0]["codigo_titular"]))
    
    registros = df.to_dict("records")

    for registro in registros:
            for campo in ("codigo_titular", "ano"):
                valor = registro.get(campo)

                if valor is None or pd.isna(valor):
                        registro[campo] = None
                else:
                        registro[campo] = int(valor)

    try:

            #st.write("Primeiro registro:")
            #st.json(registros[0])

            #st.write(type(registros[0]["codigo_titular"]))
            #st.write(repr(registros[0]["codigo_titular"]))

            #st.code(json.dumps(registros[0], indent=2, default=str))
                        
            resposta = (
                supabase
                .table(TABELA)
                .insert(registros[0], returning="representation")
                .execute()
            )
                
            st.write(resposta)
            return resposta

    except APIError as e:

        #st.error("Erro retornado pelo Supabase")

        #st.write("Mensagem:")
        #st.write(e.message)

        #st.write("Detalhes:")
        #st.write(e.details)

        #st.write("Código:")
        #st.write(e.code)

        #st.write("Hint:")
        #st.write(e.hint)

        st.error("Erro retornado pelo Supabase")
        st.write(e)
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

    df["codigo_titular"] = (
        pd.to_numeric(df["codigo_titular"], errors="coerce")
        .astype("Int64")
    )

    df["ano"] = (
        pd.to_numeric(df["ano"], errors="coerce")
        .astype("Int64")
    )

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
