import pandas as pd

#-------------------- VAGO / NORMALIZAÇÃO

def is_vago(valor) -> bool:
    return isinstance(valor, str) and valor.strip().upper() == "VAGO"


def normalize_str(x):
    return "" if x is None else str(x).strip()


# -------------------- ORDEM --------------------

MESES_MAP = {
    "JANEIRO": 1, "FEVEREIRO": 2, "MARÇO": 3, "ABRIL": 4,
    "MAIO": 5, "JUNHO": 6, "JULHO": 7, "AGOSTO": 8,
    "SETEMBRO": 9, "OUTUBRO": 10, "NOVEMBRO": 11, "DEZEMBRO": 12
}

DESIGNACAO_MAP = {
    "TITULAR": 1,
    "DESIGNAÇÃO": 2,
    "DESIGNAÇÃO TEMPORÁRIA": 3,
    "AUXÍLIO": 4,
    "AUXÍLIO TEMPORÁRIO": 5,
}


def ordenar_por_mes_e_designacao(df: pd.DataFrame) -> pd.DataFrame:

    if df.empty:
        return df

    df = df.copy()

    if "mes" in df.columns:
        df["__mes_ord__"] = df["mes"].map(MESES_MAP).fillna(999)

    if "designacao" in df.columns:
        df["__des_ord__"] = df["designacao"].map(DESIGNACAO_MAP).fillna(999)

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

    for c in ["__mes_ord__", "__des_ord__"]:
        if c in df.columns:
            df.drop(columns=c, inplace=True)

    return df
