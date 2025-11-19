import streamlit as st
import pandas as pd
import sqlite3
from database import get_connection, listar_clientes

st.set_page_config(page_title="Clientes - Sistema MTA", layout="wide")
st.title("👥 Gestão de Clientes")
st.write("Cadastre e gerencie os clientes (locatários).")

# util: carregar clientes
def load_clientes():
    return listar_clientes()

clientes = load_clientes()

st.divider()

#Função para validar CPF
def validar_cpf(cpf: str) -> bool:
    cpf = ''.join(filter(str.isdigit, cpf))

    if len(cpf) != 11:
        return False

    if cpf == cpf[0] * 11:
        return False

    # calcular 1º dígito
    soma = sum(int(cpf[i]) * (10 - i) for i in range(9))
    dig1 = (soma * 10 % 11) % 10

    # calcular 2º dígito
    soma = sum(int(cpf[i]) * (11 - i) for i in range(10))
    dig2 = (soma * 10 % 11) % 10

    return dig1 == int(cpf[9]) and dig2 == int(cpf[10])


# -----------------------
# Lista de clientes
# -----------------------
st.subheader("📋 Clientes Cadastrados")

if len(clientes) == 0:
    st.info("Nenhum cliente cadastrado.")
else:
    # tabela simples com botões por linha
    for c in clientes:
        cid, nome, sobrenome, email, telefone, cpf = c
        with st.container():
            cols = st.columns([3,3,2,2,1])
            cols[0].markdown(f"**{nome} {sobrenome}**")
            cols[1].markdown(f"**E-mail:** {email}  \n**Telefone:** {telefone}")
            cols[2].markdown(f"**CPF:** {cpf}")
            cols[3].write("")  # espaço
            if cols[4].button("✏️ Editar", key=f"edit_{cid}"):
                st.session_state["editar_cliente_id"] = cid
            if cols[4].button("🗑 Excluir", key=f"del_{cid}"):
                st.session_state["excluir_cliente_id"] = cid

st.divider()

# -----------------------
# Form: Novo Cliente
# -----------------------
st.subheader("➕ Cadastrar Novo Cliente")
with st.form("novo_cliente"):
    n_nome = st.text_input("Nome")
    n_sobrenome = st.text_input("Sobrenome")
    n_data_nasc = st.date_input("Data de Nascimento (opcional)", 
                                value=None, 
                                max_value=pd.to_datetime("today").date()-pd.Timedelta(days=6575),
                                min_value=pd.to_datetime("1900-01-01").date(),
                                help="Deve ter ao menos 18 anos.")
    n_email = st.text_input("E-mail")
    n_telefone = st.text_input("Telefone")
    n_cpf = st.text_input("CPF (somente números)")

    submit = st.form_submit_button("Cadastrar")

    if submit:
        # validações básicas
        if not n_nome.strip() or not n_sobrenome.strip() or not n_email.strip() or not n_cpf.strip():
            st.error("Nome, sobrenome, e-mail e CPF são obrigatórios.")
        elif not validar_cpf(n_cpf):
            st.error("CPF inválido. Verifique e tente novamente.")
        else:
            # inserir no DB
            try:
                conn = get_connection()
                cur = conn.cursor()
                cur.execute("""
                    INSERT INTO clientes (nome, sobrenome, data_nascimento, email, telefone, cpf)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    n_nome.strip(),
                    n_sobrenome.strip(),
                    n_data_nasc.isoformat() if n_data_nasc else None,
                    n_email.strip(),
                    n_telefone.strip(),
                    n_cpf.strip()
                ))
                conn.commit()
                conn.close()
                st.success("Cliente cadastrado com sucesso.")
                st.experimental_rerun()
            except sqlite3.IntegrityError as e:
                if "UNIQUE constraint failed" in str(e):
                    st.error("CPF já cadastrado. Verifique os dados.")
                else:
                    st.error("Erro ao cadastrar cliente.")
            except Exception as e:
                st.error(f"Erro: {e}")

# -----------------------
# Editar Cliente (quando selecionado)
# -----------------------
if "editar_cliente_id" in st.session_state:
    cid = st.session_state["editar_cliente_id"]
    # buscar dados
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, nome, sobrenome, data_nascimento, email, telefone, cpf FROM clientes WHERE id=?", (cid,))
    row = cur.fetchone()
    conn.close()
    if not row:
        st.error("Cliente não encontrado.")
        del st.session_state["editar_cliente_id"]
        st.experimental_rerun()
    else:
        _, nome, sobrenome, data_nasc, email, telefone, cpf = row
        st.subheader(f"✏️ Editar Cliente — {nome} {sobrenome}")
        with st.form("form_editar_cliente"):
            e_nome = st.text_input("Nome", value=nome)
            e_sobrenome = st.text_input("Sobrenome", value=sobrenome)
            e_data_nasc = st.date_input("Data de Nascimento (opcional)", value=pd.to_datetime(data_nasc).date() if data_nasc else None)
            e_email = st.text_input("E-mail", value=email)
            e_telefone = st.text_input("Telefone", value=telefone)
            e_cpf = st.text_input("CPF", value=cpf)

            salvar = st.form_submit_button("Salvar")
            cancelar = st.form_submit_button("Cancelar")

            if cancelar:
                del st.session_state["editar_cliente_id"]
                st.experimental_rerun()

            if salvar:
                if not validar_cpf(e_cpf):
                    st.error("CPF inválido. Verifique.")
                else:
                    try:
                        conn = get_connection()
                        cur = conn.cursor()
                        cur.execute("""
                            UPDATE clientes
                            SET nome=?, sobrenome=?, data_nascimento=?, email=?, telefone=?, cpf=?
                            WHERE id=?
                        """, (
                            e_nome.strip(), e_sobrenome.strip(),
                            e_data_nasc.isoformat() if e_data_nasc else None,
                            e_email.strip(), e_telefone.strip(), e_cpf.strip(), cid
                        ))
                        conn.commit()
                        conn.close()
                        st.success("Dados do cliente atualizados.")
                        del st.session_state["editar_cliente_id"]
                        st.experimental_rerun()
                    except sqlite3.IntegrityError as e:
                        if "UNIQUE constraint failed" in str(e):
                            st.error("CPF já cadastrado para outro cliente.")
                        else:
                            st.error("Erro ao atualizar cliente.")
                    except Exception as e:
                        st.error(f"Erro: {e}")

# -----------------------
# Excluir Cliente (quando selecionado)
# -----------------------
if "excluir_cliente_id" in st.session_state:
    cid = st.session_state["excluir_cliente_id"]
    st.error(f"Tem certeza que deseja excluir o cliente ID {cid}? Essa ação é irreversível e removerá referências.")
    col1, col2 = st.columns(2)
    if col1.button("Confirmar Exclusão"):
        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("DELETE FROM clientes WHERE id=?", (cid,))
            conn.commit()
            conn.close()
            st.success("Cliente excluído.")
            del st.session_state["excluir_cliente_id"]
            st.experimental_rerun()
        except Exception as e:
            st.error(f"Erro ao excluir: {e}")
    if col2.button("Cancelar"):
        del st.session_state["excluir_cliente_id"]
        st.experimental_rerun()
