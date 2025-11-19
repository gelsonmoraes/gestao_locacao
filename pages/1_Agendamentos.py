import streamlit as st
import sqlite3
from datetime import date
from database import (
    get_connection,
    listar_clientes,
    listar_itens,
    quantidade_locada_no_periodo,
    inserir_agendamento_base,
    inserir_item_agendamento,
    encerrar_agendamentos_expirados,
    atualizar_status,
    excluir_agendamento,
)

st.set_page_config(page_title="Agendamentos - Sistema MTA", layout="wide")
st.title("📅 Agendamentos — Sistema MTA")

# encerra automaticamente agendamentos expirados
encerrar_agendamentos_expirados()


# ------------------------------
# Helpers DB
# ------------------------------
def carregar_agendamentos_completos():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT a.id AS agendamento_id,
               a.cliente_id,
               c.nome || ' ' || c.sobrenome AS cliente_nome,
               a.data_inicio,
               a.data_fim,
               a.valor_total,
               a.status,
               a.criado_em
        FROM agendamentos a
        LEFT JOIN clientes c ON c.id = a.cliente_id
        ORDER BY date(a.data_inicio) DESC
    """)
    ags = cur.fetchall()
    result = []
    for ag in ags:
        ag_id = ag[0]
        cur.execute("""
            SELECT ai.id, ai.item_id, i.nome, ai.quantidade, ai.valor_unitario, ai.valor_total
            FROM agendamento_itens ai
            LEFT JOIN itens i ON i.id = ai.item_id
            WHERE ai.agendamento_id = ?
        """, (ag_id,))
        itens = cur.fetchall()
        result.append({"agendamento": ag, "itens": itens})
    conn.close()
    return result


def fetch_agendamento_header(ag_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, cliente_id, data_inicio, data_fim, valor_total, status FROM agendamentos WHERE id=?", (ag_id,))
    row = cur.fetchone()
    conn.close()
    return row


# ------------------------------
# Layout com abas (Listar / Novo)
# ------------------------------
tab_listar, tab_novo = st.tabs(["📋 Listar Agendamentos", "➕ Novo Agendamento"])

# ------------------------------
# Aba: Listar Agendamentos + edição inline
# ------------------------------
with tab_listar:
    st.subheader("Agendamentos (com itens)")
    ags = carregar_agendamentos_completos()

    if not ags:
        st.info("Nenhum agendamento encontrado.")
    else:
        for row in ags:
            ag = row["agendamento"]
            itens = row["itens"]
            ag_id, cliente_id, cliente_nome, data_inicio, data_fim, valor_total, status, criado_em = ag

            container = st.container()
            with container:
                st.markdown(f"### Agendamento #{ag_id} — {cliente_nome}")
                st.write(f"**Período:** {data_inicio} → {data_fim}")
                st.write(f"**Status:** {status} • **Criado em:** {criado_em}")
                st.write(f"**Valor total (registrado):** R$ {valor_total:,.2f}")

                st.markdown("**Itens do agendamento:**")
                if not itens:
                    st.write("_Nenhum item associado._")
                else:
                    for it in itens:
                        _, item_id, nome_item, qtd_item, valor_unit, valor_item_total = it
                        st.write(f"- {nome_item} — {qtd_item} un. - R\$ {valor_unit:,.2f} (total R$ {valor_item_total:,.2f})")

                cols = st.columns([1, 1, 1, 1])
                if cols[0].button("✅ Encerrar", key=f"enc_{ag_id}"):
                    atualizar_status(ag_id, "Encerrado")
                    st.experimental_rerun()
                if cols[1].button("🚫 Cancelar", key=f"canc_{ag_id}"):
                    atualizar_status(ag_id, "Cancelado")
                    st.experimental_rerun()
                if cols[2].button("✏️ Editar", key=f"edit_{ag_id}"):
                    st.session_state["editar_agendamento_id"] = ag_id
                if cols[3].button("🗑️ Excluir", key=f"del_{ag_id}"):
                    excluir_agendamento(ag_id)
                    st.experimental_rerun()

                # Inline editing modal (aparece quando st.session_state matches)
                if st.session_state.get("editar_agendamento_id", None) == ag_id:
                    st.markdown("---")
                    st.markdown(f"## ✏️ Editar Agendamento #{ag_id}")
                    header = fetch_agendamento_header(ag_id)
                    if not header:
                        st.error("Agendamento não encontrado.")
                        del st.session_state["editar_agendamento_id"]
                        st.experimental_rerun()

                    # carregar itens existentes
                    conn = get_connection()
                    cur = conn.cursor()
                    cur.execute("""
                        SELECT ai.item_id, i.nome, ai.quantidade, ai.valor_unitario, ai.valor_total
                        FROM agendamento_itens ai
                        LEFT JOIN itens i ON i.id = ai.item_id
                        WHERE ai.agendamento_id = ?
                    """, (ag_id,))
                    existing_items = cur.fetchall()
                    conn.close()

                    # preparar seleção de itens
                    clientes = listar_clientes()
                    itens_all = listar_itens()
                    clientes_map = {f"{c[1]} {c[2]} (CPF {c[5]})": c[0] for c in clientes}
                    itens_map = {i[1]: {"id": i[0], "descricao": i[2], "total": int(i[3])} for i in itens_all}
                    nomes_itens = list(itens_map.keys())

                    # pre-seleção
                    init_cliente_label = next((k for k, v in clientes_map.items() if v == header[1]), None)
                    init_data_inicio = header[2]
                    init_data_fim = header[3]

                    # transformar existing_items em dict por nome para facilitar prefill
                    existing_by_item = {}
                    for it in existing_items:
                        iid, iname, iqtd, ivunit, ivtotal = it
                        existing_by_item[iname] = {"id": iid, "quantidade": iqtd, "valor_unitario": ivunit}

                    with st.form(f"form_edit_{ag_id}"):
                        # Cliente e datas
                        cliente_label = st.selectbox("Cliente", options=list(clientes_map.keys()),
                                                    index=list(clients := list(clients_map.keys())).index(init_cliente_label) if init_cliente_label in clients else 0)
                        cliente_id_new = clients[clients.index(cliente_label)]

                        col1, col2 = st.columns(2)
                        data_inicio_new = col1.date_input("Data início", value=st.session_state.get(f"edit_start_{ag_id}", init_data_inicio))
                        data_fim_new = col2.date_input("Data fim", value=st.session_state.get(f"edit_end_{ag_id}", init_data_fim))

                        # selecionar itens (multiselect pre-selecionado)
                        preselected = list(existing_by_item.keys())
                        selecionados = st.multiselect("Itens (selecione para editar/ajustar)", options=nomes_itens, default=preselected)

                        itens_dados = []
                        disponibilidade_erro = False
                        total_calculado = 0.0

                        for nome in selecionados:
                            meta = itens_map[nome]
                            item_id = meta["id"]
                            total_estoque = meta["total"]

                            # quant já existente neste agendamento (para exclusão temporária)
                            own_qty = existing_by_item.get(nome, {}).get("quantidade", 0)

                            locadas_total = quantidade_locada_no_periodo(item_id, data_inicio_new.isoformat(), data_fim_new.isoformat())
                            # disponibilidade: total - (locadas_total - own_qty)
                            disponivel = max(0, total_estoque - max(0, locadas_total - own_qty))

                            st.markdown(f"**{nome}** — Total: {total_estoque} • Disponível (ajustado): {disponivel}")

                            colq, colv = st.columns([1, 1])
                            qtd_init = existing_by_item.get(nome, {}).get("quantidade", 0)
                            vinit = existing_by_item.get(nome, {}).get("valor_unitario", 0.0)

                            qtd_new = colq.number_input(f"Quantidade — {nome}", min_value=0, max_value=disponivel, value=int(qtd_init), key=f"edit_q_{ag_id}_{item_id}")
                            vunit_new = colv.number_input(f"Valor unitário (R$) — {nome}", min_value=0.0, value=float(vinit or 0.0), format="%.2f", key=f"edit_v_{ag_id}_{item_id}")

                            if qtd_new > disponivel:
                                st.error(f"Sem disponibilidade suficiente para {nome}. Disponível: {disponivel}")
                                disponibilidade_erro = True

                            if qtd_new > 0:
                                total_item = int(qtd_new) * float(vunit_new)
                                total_calculado += total_item
                                itens_dados.append({
                                    "item_id": item_id,
                                    "nome": nome,
                                    "quantidade": int(qtd_new),
                                    "valor_unitario": float(vunit_new),
                                    "valor_total": float(total_item)
                                })

                        st.markdown("----")
                        st.write(f"**Valor total recalculado (soma dos itens): R$ {total_calculado:,.2f}**")

                        btn_cancel = st.form_submit_button("Cancelar Edição")
                        btn_save = st.form_submit_button("Salvar Alterações")

                        if btn_cancel:
                            # limpar estado de edição
                            if "editar_agendamento_id" in st.session_state:
                                del st.session_state["editar_agendamento_id"]
                            st.experimental_rerun()

                        if btn_save:
                            if data_fim_new < data_inicio_new:
                                st.error("Data fim não pode ser anterior à data início.")
                            elif not itens_dados:
                                st.error("Adicione ao menos 1 item com quantidade > 0.")
                            elif disponibilidade_erro:
                                st.error("Corrija disponibilidade dos itens.")
                            else:
                                # atualiza cabeçalho
                                conn = get_connection()
                                cur = conn.cursor()
                                cur.execute("""
                                    UPDATE agendamentos
                                    SET cliente_id=?, data_inicio=?, data_fim=?, valor_total=?
                                    WHERE id=?
                                """, (clients[clients.index(cliente_label)], data_inicio_new.isoformat(), data_fim_new.isoformat(), total_calculado, ag_id))
                                conn.commit()
                                # remover itens antigos e inserir novos
                                cur.execute("DELETE FROM agendamento_itens WHERE agendamento_id=?", (ag_id,))
                                conn.commit()
                                conn.close()

                                for it in itens_dados:
                                    inserir_item_agendamento(ag_id, it["item_id"], it["quantidade"], it["valor_unitario"], it["valor_total"])

                                st.success("Agendamento atualizado com sucesso.")
                                if "editar_agendamento_id" in st.session_state:
                                    del st.session_state["editar_agendamento_id"]
                                st.experimental_rerun()


# ------------------------------
# Aba: Novo Agendamento
# ------------------------------
with tab_novo:
    st.subheader("Criar novo agendamento com múltiplos itens")

    clientes = listar_clientes()
    itens = listar_itens()

    if not clientes:
        st.warning("Nenhum cliente cadastrado. Cadastre clientes antes de criar agendamentos.")
    elif not itens:
        st.warning("Nenhum item cadastrado. Cadastre itens antes de criar agendamentos.")
    else:
        clientes_map = {f"{c[1]} {c[2]} (CPF {c[5]})": c[0] for c in clientes}
        itens_map = {i[1]: {"id": i[0], "descricao": i[2], "total": int(i[3])} for i in itens}
        nomes_itens = list(itens_map.keys())

        with st.form("form_novo_agendamento"):
            cliente_label = st.selectbox("Cliente", options=list(clientes_map.keys()))
            cliente_id = clientes_map[cliente_label]

            col1, col2 = st.columns(2)
            data_inicio = col1.date_input("Data início", min_value=date.today())
            data_fim = col2.date_input("Data fim", min_value=data_inicio)

            st.markdown("----")
            st.write("Selecione os itens abaixo. Para cada item selecionado, informe quantidade e valor unitário.")

            selecionados = st.multiselect("Itens", options=nomes_itens)
            itens_selecionados_dados = []
            total_estendido = 0.0
            erro_disponibilidade = False

            for nome in selecionados:
                meta = itens_map[nome]
                item_id = meta["id"]
                total_em_estoque = meta["total"]

                locadas = quantidade_locada_no_periodo(item_id, data_inicio.isoformat(), data_fim.isoformat())
                disponivel = max(0, total_em_estoque - locadas)

                st.markdown(f"**{nome}** — Total em estoque: {total_em_estoque} • Disponível no período: {disponivel}")

                colq, colv = st.columns([1, 1])
                qtd = colq.number_input(f"Quantidade — {nome}", min_value=0, max_value=disponivel, value=0, key=f"new_q_{item_id}")
                valor_unit = colv.number_input(f"Valor unitário (R$) — {nome}", min_value=0.0, value=0.0, format="%.2f", key=f"new_v_{item_id}")

                if qtd > disponivel:
                    st.error(f"Sem disponibilidade suficiente para {nome}. Disponível: {disponivel}")
                    erro_disponibilidade = True

                if qtd > 0:
                    itens_selecionados_dados.append({
                        "item_id": item_id,
                        "nome": nome,
                        "quantidade": int(qtd),
                        "valor_unitario": float(valor_unit),
                        "valor_total": int(qtd) * float(valor_unit)
                    })
                    total_estendido += int(qtd) * float(valor_unit)

            st.markdown("----")
            st.write(f"**Valor total calculado (soma dos itens): R$ {total_estendido:,.2f}**")

            submitted = st.form_submit_button("Salvar Agendamento")

            if submitted:
                if data_fim < data_inicio:
                    st.error("Data fim não pode ser anterior à data início.")
                elif not itens_selecionados_dados:
                    st.error("Adicione pelo menos 1 item com quantidade maior que zero.")
                elif erro_disponibilidade:
                    st.error("Corrija disponibilidade dos itens acima.")
                else:
                    agid = inserir_agendamento_base(cliente_id, data_inicio.isoformat(), data_fim.isoformat(), total_estendido)
                    for it in itens_selecionados_dados:
                        inserir_item_agendamento(agid, it["item_id"], it["quantidade"], it["valor_unitario"], it["valor_total"])
                    st.success(f"Agendamento #{agid} criado com sucesso — Valor total: R$ {total_estendido:,.2f}")
                    st.experimental_rerun()
