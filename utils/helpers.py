#-------------------- VAGO / NORMALIZAÇÃO
def is_vago(valor) -> bool:
    return isinstance(valor, str) and valor.strip().upper() == "VAGO"

def normalize_str(x):
    return "" if x is None else str(x).strip()