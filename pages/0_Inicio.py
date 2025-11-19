import streamlit as st

with open("styles.css") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

st.set_page_config(page_title="Início - Sistema de Gestão MTA", layout="wide")  
st.title("Bem-vindo ao Sistema de Gestão da MTA")    
st.write("Use o menu lateral para navegar entre as diferentes seções do sistema.")