import pandas as pd
import streamlit as st
from services.supabase_client import get_supabase

# --------------------------- Interface Página
def pagina_vacancia():
    st.title("⏳ Vacâncias")

    supabase = get_supabase()

    with st.form("cadastro_vacancias", clear_on_submit=True):

        st.subheader("Novo")
        orgao = st.text_input("Órgão")
        membro = st.text_input("Titular")
        vacancia = st.date_input("Data Vacância")
        publicacao = st.date_input("Data Publicação")
        
        submit_button = st.form_submit_button("✔️ Cadastrar")

    if submit_button:
        if not orgao:
            st.error("A identificação do órgão é obrigatória.")
        else:
            # Inserir no Supabase
            response = supabase.table("vacancias").insert({
                "orgao": orgao,
                "membro": membro,
                "vacancia": vacancia.strftime("%Y-%m-%d"),
                "publicacao": publicacao.strftime("%Y-%m-%d"),
            }).execute()
            
            if response.data:
                st.success("✔️ Cadastrado realizado com sucesso!")
            else:
                st.error("Erro ao cadastrar.")

    # ---- Visualização dos últimos processos
    st.divider()
    st.subheader("Vacâncias recentes")
    response = supabase.table("vacancias").select("*").order("created_at", desc=True).limit(20).execute()
    if response.data:
        df = pd.DataFrame(response.data)
        st.dataframe(df[['orgao', 'membro', 'vacancia', 'publicacao']], use_container_width=True)
