import sqlite3
from pathlib import Path
from datetime import date

DB_PATH = Path("database.db")

def get_connection():
    return sqlite3.connect(DB_PATH)


# =======================================================
#              INICIALIZAÇÃO + MIGRAÇÕES
# =======================================================
def init_db():
    conn = get_connection()
    cur = conn.cursor()

    # -------------------------
    # TABELA ITENS
    # -------------------------
    cur.execute("""
        CREATE TABLE IF NOT EXISTS itens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL UNIQUE,
            descricao TEXT,
            quantidade_total INTEGER NOT NULL
        )
    """)

    # -------------------------
    # TABELA CLIENTES
    # -------------------------
    cur.execute("""
        CREATE TABLE IF NOT EXISTS clientes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            sobrenome TEXT NOT NULL,
            data_nascimento TEXT,
            email TEXT NOT NULL,
            telefone TEXT,
            cpf TEXT UNIQUE NOT NULL
        )
    """)

    # -------------------------
    # TABELA AGENDAMENTOS (base)
    # -------------------------
    cur.execute("""
        CREATE TABLE IF NOT EXISTS agendamentos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cliente_id INTEGER NOT NULL,
            data_inicio TEXT NOT NULL,
            data_fim TEXT NOT NULL,
            valor_total REAL DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'Em andamento',
            criado_em TEXT NOT NULL,
            FOREIGN KEY (cliente_id) REFERENCES clientes(id)
        )
    """)

    # -------------------------
    # TABELA ITENS DO AGENDAMENTO
    # -------------------------
    cur.execute("""
        CREATE TABLE IF NOT EXISTS agendamento_itens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            agendamento_id INTEGER NOT NULL,
            item_id INTEGER NOT NULL,
            quantidade INTEGER NOT NULL,
            valor_unitario REAL DEFAULT 0,
            valor_total REAL DEFAULT 0,
            FOREIGN KEY (agendamento_id) REFERENCES agendamentos(id),
            FOREIGN KEY (item_id) REFERENCES itens(id)
        )
    """)

    # MIGRAÇÃO: garantir que colunas existam
    cur.execute("PRAGMA table_info(agendamento_itens)")
    cols = [c[1] for c in cur.fetchall()]

    if "valor_unitario" not in cols:
        cur.execute("ALTER TABLE agendamento_itens ADD COLUMN valor_unitario REAL DEFAULT 0")

    if "valor_total" not in cols:
        cur.execute("ALTER TABLE agendamento_itens ADD COLUMN valor_total REAL DEFAULT 0")

    conn.commit()
    conn.close()


init_db()


# =======================================================
#     ROTINA AUTOMÁTICA – ENCERRAR AGENDAMENTOS
# =======================================================
def encerrar_agendamentos_expirados():
    hoje = date.today().isoformat()
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        UPDATE agendamentos
        SET status = 'Encerrado'
        WHERE date(data_fim) < date(?)
          AND status NOT IN ('Cancelado', 'Encerrado')
    """, (hoje,))
    conn.commit()
    conn.close()


# =======================================================
#                 CLIENTES
# =======================================================
def listar_clientes():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, nome, sobrenome, email, telefone, cpf
        FROM clientes
        ORDER BY nome ASC
    """)
    rows = cur.fetchall()
    conn.close()
    return rows


# =======================================================
#                 ITENS CRUD
# =======================================================
def listar_itens():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, nome, descricao, quantidade_total FROM itens")
    rows = cur.fetchall()
    conn.close()
    return rows


def nome_item_existe(nome):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM itens WHERE nome = ?", (nome,))
    existe = cur.fetchone()[0] > 0
    conn.close()
    return existe


def inserir_item(nome, descricao, quantidade_total):
    conn = get_connection()
    conn.execute("""
        INSERT INTO itens (nome, descricao, quantidade_total)
        VALUES (?, ?, ?)
    """, (nome, descricao, quantidade_total))
    conn.commit()
    conn.close()


def atualizar_item(item_id, nome, descricao, quantidade_total):
    conn = get_connection()
    conn.execute("""
        UPDATE itens SET nome=?, descricao=?, quantidade_total=?
        WHERE id=?
    """, (nome, descricao, quantidade_total, item_id))
    conn.commit()
    conn.close()


def excluir_item(item_id):
    conn = get_connection()
    conn.execute("DELETE FROM itens WHERE id=?", (item_id,))
    conn.commit()
    conn.close()


# =======================================================
#              AGENDAMENTOS — MULTI-ITENS
# =======================================================

def inserir_agendamento_base(cliente_id, data_inicio, data_fim, valor_total):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO agendamentos (cliente_id, data_inicio, data_fim, valor_total, status, criado_em)
        VALUES (?, ?, ?, ?, 'Em andamento', date('now'))
    """, (cliente_id, data_inicio, data_fim, valor_total))
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return new_id


def inserir_item_agendamento(agendamento_id, item_id, quantidade, valor_unitario, valor_total):
    conn = get_connection()
    conn.execute("""
        INSERT INTO agendamento_itens
        (agendamento_id, item_id, quantidade, valor_unitario, valor_total)
        VALUES (?, ?, ?, ?, ?)
    """, (agendamento_id, item_id, quantidade, valor_unitario, valor_total))
    conn.commit()
    conn.close()


def excluir_agendamento(agendamento_id):
    conn = get_connection()
    conn.execute("DELETE FROM agendamentos WHERE id=?", (agendamento_id,))
    conn.execute("DELETE FROM agendamento_itens WHERE agendamento_id=?", (agendamento_id,))
    conn.commit()
    conn.close()


def atualizar_status(agendamento_id, novo_status):
    conn = get_connection()
    conn.execute("""
        UPDATE agendamentos SET status=? WHERE id=?
    """, (novo_status, agendamento_id))
    conn.commit()
    conn.close()


# =======================================================
#              DISPONIBILIDADE DE ITENS
# =======================================================
def quantidade_locada_no_periodo(item_id, inicio, fim):
    conn = get_connection()
    cur = conn.cursor()

    sql = """
        SELECT SUM(ai.quantidade)
        FROM agendamento_itens ai
        JOIN agendamentos a ON ai.agendamento_id = a.id
        WHERE ai.item_id = ?
          AND a.status != 'Cancelado'
          AND NOT (date(a.data_fim) < date(?) OR date(a.data_inicio) > date(?))
    """

    cur.execute(sql, (item_id, inicio, fim))
    result = cur.fetchone()[0]
    conn.close()
    return result if result else 0
