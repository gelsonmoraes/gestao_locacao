import streamlit as st
from database import init_db

# Configuração da página principal
st.set_page_config(page_title="Sistema de Gestão MTA", layout="wide")

# Inicializa o banco de dados
init_db()

# Referência das páginas
inicio = st.Page("pages/0_Inicio.py", title="Início", icon="🏠")
agendamentos = st.Page("pages/1_Agendamentos.py", title="Agendamentos", icon="📅")
disponibilidades = st.Page("pages/2_Disponibilidades.py", title="Disponibilidades", icon="✅")
itens = st.Page("pages/3_Itens.py", title="Itens", icon="📦")
clientes = st.Page("pages/4_Clientes.py", title="Clientes", icon="👥")
relatorios = st.Page("pages/5_Relatorios.py", title="Relatórios", icon="📊")

pg = st.navigation(pages=[inicio, agendamentos, disponibilidades, itens, clientes, relatorios])
st.sidebar.caption("Sistema de Gestão MTA")

pg.run()