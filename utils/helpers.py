import pandas as pd
from services.supabase_client import get_supabase

supabase = get_supabase()

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

#---------------#
def mostrar_erro(ex: Exception, contexto: str = ""):
    st.error(f"❌ Ocorreu um erro {('em ' + contexto) if contexto else ''}: {ex}")

def listar_orgaos_unicos():
    res = supabase.table("orgaos_distintos").select("orgao").execute()
    return [r["orgao"] for r in res.data or []]

def consultar_por_orgao(orgao: str) -> pd.DataFrame:
    try:
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