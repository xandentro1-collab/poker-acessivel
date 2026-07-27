"""Banco de dados: PostgreSQL (produção) ou SQLite (local/testes).

Se a variável de ambiente DATABASE_URL existir, usamos PostgreSQL (permanente,
como no Render). Caso contrário, usamos um arquivo SQLite local.

O ledger (lançamentos) é imutável (append-only): o saldo é sempre a soma dos
lançamentos, o que evita inconsistências e facilita auditoria.

Para funcionar nos dois bancos com o mesmo código, usamos:
- `?` como placeholder (traduzido para `%s` no PostgreSQL);
- `INSERT ... RETURNING id` para obter o id gerado (suportado por ambos);
- um tipo/default de data por banco (TEXT+datetime('now') no SQLite,
  TIMESTAMP+CURRENT_TIMESTAMP no PostgreSQL).
"""
from __future__ import annotations

import os
import sqlite3
import threading

_LOCAL = threading.local()

DATABASE_URL = os.environ.get("DATABASE_URL", "").strip()
IS_PG = bool(DATABASE_URL)

if IS_PG:
    import psycopg2
    import psycopg2.extras

# Diferenças de dialeto por banco
_PK = "SERIAL PRIMARY KEY" if IS_PG else "INTEGER PRIMARY KEY AUTOINCREMENT"
_TS = "TIMESTAMP" if IS_PG else "TEXT"
_NOW = "CURRENT_TIMESTAMP" if IS_PG else "datetime('now')"


def _schema() -> str:
    return f"""
CREATE TABLE IF NOT EXISTS usuarios (
    id            {_PK},
    email         TEXT UNIQUE NOT NULL,
    apelido       TEXT UNIQUE NOT NULL,
    senha_hash    TEXT NOT NULL,
    salt          TEXT NOT NULL,
    admin         INTEGER NOT NULL DEFAULT 0,
    criado_em     {_TS} NOT NULL DEFAULT ({_NOW})
);

CREATE TABLE IF NOT EXISTS lancamentos (
    id            {_PK},
    usuario_id    INTEGER NOT NULL REFERENCES usuarios(id),
    tipo          TEXT NOT NULL,
    valor         INTEGER NOT NULL,
    descricao     TEXT,
    ref           TEXT,
    criado_em     {_TS} NOT NULL DEFAULT ({_NOW})
);

CREATE INDEX IF NOT EXISTS idx_lanc_usuario ON lancamentos(usuario_id);

CREATE TABLE IF NOT EXISTS sessoes (
    token         TEXT PRIMARY KEY,
    usuario_id    INTEGER NOT NULL REFERENCES usuarios(id),
    criado_em     {_TS} NOT NULL DEFAULT ({_NOW})
);

CREATE TABLE IF NOT EXISTS convites (
    codigo        TEXT PRIMARY KEY,
    criado_por    INTEGER REFERENCES usuarios(id),
    usado_por     INTEGER REFERENCES usuarios(id),
    usado_em      {_TS},
    criado_em     {_TS} NOT NULL DEFAULT ({_NOW})
);
"""

_DB_PATH = os.environ.get(
    "POKER_DB",
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "poker.db"),
)


def definir_caminho(path: str) -> None:
    """Aponta o SQLite para outro arquivo/memória (usado nos testes)."""
    global _DB_PATH
    _DB_PATH = path
    if hasattr(_LOCAL, "conn"):
        try:
            _LOCAL.conn._raw.close()
        except Exception:
            pass
        del _LOCAL.conn


def _adaptar(sql: str) -> str:
    """Ajusta o SQL para o PostgreSQL (placeholders e função de data)."""
    if IS_PG:
        sql = sql.replace("?", "%s")
        sql = sql.replace("datetime('now')", "CURRENT_TIMESTAMP")
    return sql


class Conexao:
    """Fina camada uniforme sobre sqlite3 e psycopg2."""

    def __init__(self, raw):
        self._raw = raw

    def execute(self, sql, params=()):
        sql = _adaptar(sql)
        if IS_PG:
            cur = self._raw.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cur.execute(sql, params)
            return cur
        return self._raw.execute(sql, params)

    def executescript(self, script: str):
        if IS_PG:
            cur = self._raw.cursor()
            cur.execute(script)  # psycopg2 executa vários comandos separados por ;
        else:
            self._raw.executescript(script)

    def commit(self):
        self._raw.commit()


def conexao() -> Conexao:
    if not hasattr(_LOCAL, "conn"):
        if IS_PG:
            raw = psycopg2.connect(DATABASE_URL)
        else:
            raw = sqlite3.connect(_DB_PATH, check_same_thread=False)
            raw.row_factory = sqlite3.Row
            raw.execute("PRAGMA foreign_keys = ON")
            raw.execute("PRAGMA journal_mode = WAL")
        _LOCAL.conn = Conexao(raw)
    return _LOCAL.conn


def _migrar(conn: Conexao) -> None:
    """Migração leve só para SQLite já existente (adiciona coluna admin)."""
    if IS_PG:
        return  # no PostgreSQL a coluna admin já vem no schema
    cols = [r["name"] for r in conn.execute("PRAGMA table_info(usuarios)")]
    if "admin" not in cols:
        conn.execute("ALTER TABLE usuarios ADD COLUMN admin INTEGER NOT NULL DEFAULT 0")
    conn.commit()


def inicializar() -> None:
    conn = conexao()
    conn.executescript(_schema())
    conn.commit()
    _migrar(conn)
