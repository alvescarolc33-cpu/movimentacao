import pandas as pd
import streamlit as st
import json
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

    registros = []

    for _, row in df.iterrows():

        registro = {}

        for coluna, valor in row.items():

            # valores vazios
            if pd.isna(valor):
                registro[coluna] = None

            # datas
            elif isinstance(valor, (pd.Timestamp,)):
                registro[coluna] = valor.strftime("%Y-%m-%d")

            # numpy.int64 / float64 / bool_
            elif hasattr(valor, "item"):
                registro[coluna] = valor.item()

            else:
                registro[coluna] = valor

        registros.append(registro)

    # Apenas para descobrir qual registro falha
    try:
        json.dumps(registros)
        st.success("JSON válido!")
    except Exception as e:
        st.error(e)
        st.write(registros[0])
        raise

    return (
        supabase
        .table(TABELA)
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
