import streamlit as st
from datetime import date
import sqlite3
from database import listar_itens, quantidade_locada_no_periodo, encerrar_agendamentos_expirados

st.title("Disponibilidades dos Itens")
st.write("Consulte aqui a disponibilidade dos itens para locação, considerando todos os agendamentos existentes.")

# Atualiza automaticamente agendamentos expirados
encerrar_agendamentos_expirados()

# ==========================
# Carregar itens cadastrados
# ==========================
itens = listar_itens()

if not itens:
    st.warning("Nenhum item cadastrado ainda.")
    st.stop()

# ==========================================================
# Filtro opcional por intervalo de datas (para visualização)
# ==========================================================
st.subheader("Filtro por Período")

col1, col2 = st.columns(2)

data_inicio = col1.date_input("Data Início", value=date.today())
data_fim = col2.date_input("Data Fim", value=date.today())

if data_fim < data_inicio:
    st.error("A data final deve ser maior ou igual à data inicial.")
    st.stop()

st.divider()

# ==========================
# Tabela de disponibilidades
# ==========================
st.subheader("📦 Disponibilidade dos Itens")

for item in itens:
    item_id, nome, descricao, qtd_total = item

    # Quantidade locada no período
    locadas = quantidade_locada_no_periodo(
        item_id,
        data_inicio.isoformat(),
        data_fim.isoformat()
    )

    disponivel = max(0, qtd_total - locadas)

    with st.container(border=True):
        st.markdown(f"### {nome}")
        if descricao:
            st.caption(descricao)

        colA, colB, colC = st.columns(3)
        colA.metric("Total em estoque", qtd_total)
        colB.metric("Locadas no período", locadas)
        colC.metric("Disponíveis", disponivel)

st.markdown("---")
st.caption("Dados atualizados automaticamente com base nos agendamentos.")
