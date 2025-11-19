import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date
from database import get_connection

st.set_page_config(page_title="Relatórios - Sistema MTA", layout="wide")
st.title("📈 Relatórios")
st.write("Visão consolidada (itens por agendamento, valores por item, ocupação).")

# 1) Carregar dados (JOIN agendamentos + agendamento_itens + itens + clientes)
def load_df_items():
    conn = get_connection()
    q = """
    SELECT 
        a.id AS agendamento_id,
        a.cliente_id,
        c.nome || ' ' || c.sobrenome AS cliente_nome,
        a.data_inicio,
        a.data_fim,
        a.status,
        a.criado_em,
        ai.item_id,
        i.nome AS item_nome,
        ai.quantidade AS quantidade_item,
        ai.valor_unitario,
        ai.valor_total
    FROM agendamentos a
    LEFT JOIN clientes c ON c.id = a.cliente_id
    LEFT JOIN agendamento_itens ai ON ai.agendamento_id = a.id
    LEFT JOIN itens i ON i.id = ai.item_id
    ORDER BY a.data_inicio ASC
    """
    df = pd.read_sql_query(q, conn, parse_dates=["data_inicio", "data_fim", "criado_em"])
    conn.close()
    return df

df = load_df_items()

if df.empty:
    st.info("Nenhum agendamento / item para gerar relatórios.")
    st.stop()

# Preprocessamento
df["data_inicio"] = pd.to_datetime(df["data_inicio"])
df["data_fim"] = pd.to_datetime(df["data_fim"])
df["criado_em"] = pd.to_datetime(df["criado_em"])

# Filtros de período
st.sidebar.header("Período do Relatório")
min_date = df["data_inicio"].min().date()
max_date = df["data_fim"].max().date()
period = st.sidebar.date_input("Intervalo de datas", [min_date, max_date], min_value=min_date, max_value=max_date)
if not period or len(period) < 2:
    st.sidebar.warning("Selecione data inicial e final.")
    st.stop()
start, end = pd.to_datetime(period[0]), pd.to_datetime(period[1])

mask = (df["data_inicio"] >= start) & (df["data_inicio"] <= end)
dff = df.loc[mask].copy()
if dff.empty:
    st.info("Nenhum agendamento no período selecionado.")
    st.stop()

# KPIs
st.subheader("📊 KPIs do Período")
col1, col2, col3, col4 = st.columns(4)
col1.metric("Agendamentos Atendidos", dff["agendamento_id"].nunique())
col2.metric("Receita Total (R$)", f"R$ {dff['valor_total'].sum():,.2f}")
col3.metric("Itens Locados (total)", int(dff["quantidade_item"].sum()))
col4.metric("Ticket Médio por Agendamento", f"R$ {dff['valor_total'].sum() / dff['agendamento_id'].nunique():,.2f}")

st.divider()

# Gráfico 1: Receita ao longo do tempo (soma por data_inicio)
st.subheader("Receita por Data")
receita_diaria = dff.groupby(dff["data_inicio"].dt.date)["valor_total"].sum().reset_index()
receita_diaria["data"] = pd.to_datetime(receita_diaria["data_inicio"])
fig1 = px.line(receita_diaria, x="data", y="valor_total", markers=True, title="Receita por Data")
fig1.update_xaxes(tickformat="%d/%m/%Y")
st.plotly_chart(fig1, use_container_width=True)

# Gráfico 2: Ocupação por Item (soma de quantidades)
st.subheader("Ocupação por Item")
ocup_item = dff.groupby("item_nome")["quantidade_item"].sum().reset_index().sort_values("quantidade_item", ascending=False)
fig2 = px.bar(ocup_item, x="quantidade_item", y="item_nome", orientation="h", title="Quantidade reservada por item")
st.plotly_chart(fig2, use_container_width=True)

# Gráfico 3: Receita por Item (usar valor_total por item)
st.subheader("Top itens por receita")
receita_item = dff.groupby("item_nome")["valor_total"].sum().reset_index().sort_values("valor_total", ascending=False).head(20)
fig3 = px.bar(receita_item, x="valor_total", y="item_nome", orientation="h", title="Receita por item (top)")
st.plotly_chart(fig3, use_container_width=True)

# Gráfico 4: Agendamentos por mês
st.subheader("Agendamentos por mês")
dff["mes"] = dff["data_inicio"].dt.to_period("M").dt.to_timestamp()
agend_mes = dff.groupby("mes")["agendamento_id"].nunique().reset_index(name="agendamentos")
fig4 = px.bar(agend_mes, x="mes", y="agendamentos", title="Agendamentos por Mês")
fig4.update_xaxes(tickformat="%b %Y")
st.plotly_chart(fig4, use_container_width=True)

# Tabela detalhada
st.divider()
st.subheader("Detalhes (itens por agendamento)")
display_cols = ["agendamento_id", "item_nome", "cliente_nome", "quantidade_item", "valor_unitario", "valor_total", "data_inicio", "data_fim", "status"]
view = dff[display_cols].rename(columns={
    "agendamento_id": "ID",
    "item_nome": "Item",
    "cliente_nome": "Cliente",
    "quantidade_item": "Qtd",
    "valor_unitario": "Valor Unit (R$)",
    "valor_total": "Valor Item (R$)",
    "data_inicio": "Início",
    "data_fim": "Fim",
    "status": "Status"
})
# formatar datas para exibir
view["Início"] = pd.to_datetime(view["Início"]).dt.strftime("%d/%m/%Y")
view["Fim"] = pd.to_datetime(view["Fim"]).dt.strftime("%d/%m/%Y")
st.dataframe(view.sort_values("Início", ascending=False), use_container_width=True)

st.markdown("---")
st.caption("Relatórios baseados no valor armazenado por item (agendamento_itens.valor_total).")
