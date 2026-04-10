import pandas as pd
import streamlit as st
from services.supabase_client import get_supabase

# --------------------------- Interface Página
def pagina_atos():
    st.title("⚖️ Atos TJRJ")

    supabase = get_supabase()

    with st.form("cadastro_atos", clear_on_submit=True):

        st.subheader("Novo Ato")
        ato = st.text_input("Ato/Origem")
        numero = st.text_input("Número")
        ementa = st.text_input("Ementa")
        data_doe = st.date_input("Data DOe")
        folha_doe = st.text_input("Folha DOe")
        link_doe = st.text_input("Link DOe")
        comentarios = st.text_input("Comentário")
        
        submit_button = st.form_submit_button("Cadastrar Ato")

    if submit_button:
        if not numero:
            st.error("O número do ato é obrigatório.")
        else:
            # Inserir no Supabase
            response = supabase.table("atos_tj").insert({
                "ato": ato,
                "numero": numero,
                "ementa": ementa,
                "data_doe": data_doe.strftime("%Y-%m-%d"),
                "folha_doe": folha_doe,
                "link_doe": link_doe,
                "comentarios": comentarios,
            }).execute()
            
            if response.data:
                st.success("Ato cadastrado com sucesso!")
            else:
                st.error("Erro ao cadastrar.")

    # ---- Visualização dos últimos processos
    st.divider()
    st.subheader("Atos Cadastrados")
    response = supabase.table("atos_tj").select("*").order("created_at", desc=True).limit(20).execute()
    if response.data:
        df = pd.DataFrame(response.data)
        st.dataframe(df[['ato', 'numero', 'ementa', 'data_doe', 'folha_doe', 'link_doe', 'comentarios']], use_container_width=True)