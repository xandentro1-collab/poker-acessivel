"""Banco de dados SQLite: usuários, carteira (ledger) e histórico.

Usamos apenas a stdlib. O ledger é imutável (append-only): o saldo é sempre a
soma dos lançamentos, o que evita inconsistências e facilita auditoria.
"""
from __future__ import annotations

import os
import sqlite3
import threading

_LOCAL = threading.local()

SCHEMA = """
CREATE TABLE IF NOT EXISTS usuarios (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    email         TEXT UNIQUE NOT NULL,
    apelido       TEXT UNIQUE NOT NULL,
    senha_hash    TEXT NOT NULL,
    salt          TEXT NOT NULL,
    criado_em     TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS lancamentos (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id    INTEGER NOT NULL REFERENCES usuarios(id),
    tipo          TEXT NOT NULL,   -- deposito, saque, buy_in, cash_out, premio, rake
    valor         INTEGER NOT NULL, -- em centavos; positivo credita, negativo debita
    descricao     TEXT,
    ref           TEXT,            -- id externo (mesa, transação de pagamento)
    criado_em     TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_lanc_usuario ON lancamentos(usuario_id);

CREATE TABLE IF NOT EXISTS sessoes (
    token         TEXT PRIMARY KEY,
    usuario_id    INTEGER NOT NULL REFERENCES usuarios(id),
    criado_em     TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS convites (
    codigo        TEXT PRIMARY KEY,
    criado_por    INTEGER REFERENCES usuarios(id),
    usado_por     INTEGER REFERENCES usuarios(id),
    usado_em      TEXT,
    criado_em     TEXT NOT NULL DEFAULT (datetime('now'))
);
"""

# Migrações leves para bancos já existentes (adiciona colunas que faltarem).
_MIGRACOES = [
    ("usuarios", "admin", "ALTER TABLE usuarios ADD COLUMN admin INTEGER NOT NULL DEFAULT 0"),
]


def _migrar(conn: sqlite3.Connection) -> None:
    for tabela, coluna, ddl in _MIGRACOES:
        cols = [r["name"] for r in conn.execute(f"PRAGMA table_info({tabela})")]
        if coluna not in cols:
            conn.execute(ddl)
    conn.commit()

_DB_PATH = os.environ.get(
    "POKER_DB",
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "poker.db"),
)


def definir_caminho(path: str) -> None:
    """Permite apontar para um banco em memória/temporário (testes)."""
    global _DB_PATH
    _DB_PATH = path
    if hasattr(_LOCAL, "conn"):
        _LOCAL.conn.close()
        del _LOCAL.conn


def conexao() -> sqlite3.Connection:
    if not hasattr(_LOCAL, "conn"):
        conn = sqlite3.connect(_DB_PATH, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")
        _LOCAL.conn = conn
    return _LOCAL.conn


def inicializar() -> None:
    conn = conexao()
    conn.executescript(SCHEMA)
    conn.commit()
    _migrar(conn)
