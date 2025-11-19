import streamlit as st
import pandas as pd
from database import listar_itens, inserir_item, atualizar_item, excluir_item
from io import StringIO

st.set_page_config(page_title="Itens - Sistema de Gestão MTA", layout="wide")
st.title("📦 Gestão de Itens")
st.write("Gerencie aqui os itens disponíveis para locação. (CRUD, export CSV, paginação e validação de duplicados)")

# -----------------------------
# Helpers
# -----------------------------
def carregar_itens():
    rows = listar_itens()
    # transformar em lista de dicts para facilitar manipulação
    cols = ["id", "nome", "descricao", "quantidade_total"]
    return [dict(zip(cols, r)) for r in rows]

def nome_ja_existe(nome, excluir_id=None):
    """Verifica se já existe item com mesmo nome (case-insensitive). Se excluir_id for fornecido, ignora esse id."""
    all_items = carregar_itens()
    nome_norm = nome.strip().lower()
    for it in all_items:
        if it["nome"].strip().lower() == nome_norm:
            if excluir_id and it["id"] == excluir_id:
                continue
            return True
    return False

# -----------------------------
# Barra superior: pesquisa e export
# -----------------------------
itens_all = carregar_itens()

col_search, col_export, col_space = st.columns([3, 1, 6])
with col_search:
    q = st.text_input("🔎 Pesquisar por nome", value="").strip()
with col_export:
    # botao de export CSV (base full)
    if st.button("⬇️ Exportar todos (CSV)"):
        df_export = pd.DataFrame(itens_all)
        csv_buf = df_export.to_csv(index=False, sep=",")
        st.download_button("Download CSV", data=csv_buf, file_name="itens_export.csv", mime="text/csv")

st.divider()

# -----------------------------
# Filtros e paginação
# -----------------------------
# filtrar por pesquisa
if q:
    itens_filtered = [it for it in itens_all if q.lower() in it["nome"].lower()]
else:
    itens_filtered = itens_all

# Ordenar por nome
itens_filtered = sorted(itens_filtered, key=lambda x: x["nome"].lower())

# paginação
per_page = st.selectbox("Itens por página", options=[5, 10, 20, 50], index=1)
total = len(itens_filtered)
total_pages = max(1, (total + per_page - 1) // per_page)

# inicializa estado da pagina
if "page_itens" not in st.session_state:
    st.session_state["page_itens"] = 1

col_prev, col_page, col_next = st.columns([1, 2, 1])
with col_prev:
    if st.button("◀ Anterior") and st.session_state["page_itens"] > 1:
        st.session_state["page_itens"] -= 1
with col_page:
    st.write(f"Página {st.session_state['page_itens']} de {total_pages} — {total} item(s) encontrado(s)")
with col_next:
    if st.button("Próxima ▶") and st.session_state["page_itens"] < total_pages:
        st.session_state["page_itens"] += 1

start_idx = (st.session_state["page_itens"] - 1) * per_page
end_idx = start_idx + per_page
itens_page = itens_filtered[start_idx:end_idx]

# -----------------------------
# Lista (paginada)
# -----------------------------
st.subheader("📋 Itens Cadastrados")
if not itens_page:
    st.info("Nenhum item na página atual. Tente outra página ou remova filtros.")
else:
    for it in itens_page:
        item_id = it["id"]
        nome = it["nome"]
        descricao = it["descricao"] or ""
        quantidade = int(it["quantidade_total"])

        with st.expander(f"{nome} — {quantidade} un.", expanded=False):
            cols = st.columns([3, 6, 2, 1])
            cols[0].markdown(f"**Nome:** {nome}")
            cols[1].markdown(f"**Descrição:** {descricao}")
            cols[2].markdown(f"**Estoque Total:** {quantidade}")
            if cols[3].button("✏️ Editar", key=f"edit_{item_id}"):
                st.session_state["editar_item_id"] = item_id
            if cols[3].button("🗑️ Excluir", key=f"del_{item_id}"):
                st.session_state["excluir_item_id"] = item_id

st.divider()

# -----------------------------
# Formulário: Novo Item
# -----------------------------
st.subheader("➕ Cadastrar Novo Item")
with st.form("novo_item_form"):
    novo_nome = st.text_input("Nome do Item")
    nova_descricao = st.text_area("Descrição")
    nova_quantidade = st.number_input("Quantidade Total em Estoque", min_value=1, value=1, step=1)
    submit_novo = st.form_submit_button("Cadastrar")

    if submit_novo:
        if not novo_nome.strip():
            st.error("O nome do item é obrigatório.")
        elif nome_ja_existe(novo_nome):
            st.error("Já existe um item com esse nome. Use um nome diferente ou edite o item existente.")
        else:
            inserir_item(novo_nome.strip(), nova_descricao.strip(), int(nova_quantidade))
            st.success("Item cadastrado com sucesso!")
            st.experimental_rerun()

# -----------------------------
# Edição de Item (quando selecionado)
# -----------------------------
if "editar_item_id" in st.session_state:
    edit_id = st.session_state["editar_item_id"]
    # carrega dados atuais
    item = next((x for x in itens_all if x["id"] == edit_id), None)
    if not item:
        st.error("Item para edição não encontrado.")
        del st.session_state["editar_item_id"]
        st.experimental_rerun()
    else:
        st.subheader(f"✏️ Editar Item — ID {edit_id}")
        with st.form("editar_item_form"):
            edit_nome = st.text_input("Nome do Item", value=item["nome"])
            edit_descricao = st.text_area("Descrição", value=item["descricao"])
            edit_quantidade = st.number_input("Quantidade Total", min_value=1, value=int(item["quantidade_total"]), step=1)
            salvar = st.form_submit_button("Salvar Alterações")
            cancelar = st.form_submit_button("Cancelar")

            if cancelar:
                del st.session_state["editar_item_id"]
                st.experimental_rerun()

            if salvar:
                if not edit_nome.strip():
                    st.error("Nome é obrigatório.")
                elif nome_ja_existe(edit_nome, excluir_id=edit_id):
                    st.error("Já existe outro item com esse nome. Escolha um nome diferente.")
                else:
                    atualizar_item(edit_id, edit_nome.strip(), edit_descricao.strip(), int(edit_quantidade))
                    st.success("Item atualizado com sucesso.")
                    del st.session_state["editar_item_id"]
                    st.experimental_rerun()

# -----------------------------
# Exclusão de Item (confirmação)
# -----------------------------
if "excluir_item_id" in st.session_state:
    del_id = st.session_state["excluir_item_id"]
    st.error(f"Tem certeza que deseja excluir o item ID {del_id}? Esta ação é irreversível.")
    colc1, colc2 = st.columns(2)
    if colc1.button("Confirmar Exclusão"):
        # excluir
        excluir_item(del_id)
        st.success("Item excluído com sucesso.")
        del st.session_state["excluir_item_id"]
        st.experimental_rerun()
    if colc2.button("Cancelar"):
        del st.session_state["excluir_item_id"]
        st.experimental_rerun()

# -----------------------------
# Exportar itens filtrados (CSV)
# -----------------------------
st.divider()
st.subheader("Exportar / Relatório")
csv_col1, csv_col2 = st.columns([3, 1])
with csv_col1:
    st.write("Você pode exportar os itens atualmente filtrados (pesquisa + ordenação) em CSV.")
with csv_col2:
    df_to_export = pd.DataFrame(itens_filtered)
    csv_buffer = df_to_export.to_csv(index=False)
    st.download_button("📥 Exportar CSV", data=csv_buffer, file_name="itens_filtrados.csv", mime="text/csv")

# -----------------------------
# Footer
# -----------------------------
st.markdown("---")
st.caption("Dica: use a pesquisa e a paginação para navegar por grandes catálogos de itens.")
