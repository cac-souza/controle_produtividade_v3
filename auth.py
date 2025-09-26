import streamlit as st

def exigir_login():
    # Checa se existe um usuário logado - 
    if st.session_state.get("usuario") is None:
        st.warning("⚠️ Você precisa estar logado para acessar esta aba.")
        st.stop()



