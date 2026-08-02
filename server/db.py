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
    verificado    INTEGER NOT NULL DEFAULT 0,
    codigo_verif  TEXT,
    codigo_expira INTEGER,
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
    expira_em     INTEGER,
    criado_em     {_TS} NOT NULL DEFAULT ({_NOW})
);

CREATE TABLE IF NOT EXISTS convites (
    codigo        TEXT PRIMARY KEY,
    criado_por    INTEGER REFERENCES usuarios(id),
    usado_por     INTEGER REFERENCES usuarios(id),
    usado_em      {_TS},
    criado_em     {_TS} NOT NULL DEFAULT ({_NOW})
);

CREATE TABLE IF NOT EXISTS amizades (
    usuario_id    INTEGER NOT NULL REFERENCES usuarios(id),
    amigo_id      INTEGER NOT NULL REFERENCES usuarios(id),
    criado_em     {_TS} NOT NULL DEFAULT ({_NOW}),
    PRIMARY KEY (usuario_id, amigo_id)
);

CREATE TABLE IF NOT EXISTS preferencias (
    usuario_id    INTEGER NOT NULL REFERENCES usuarios(id),
    chave         TEXT NOT NULL,
    valor         TEXT,
    PRIMARY KEY (usuario_id, chave)
);

CREATE TABLE IF NOT EXISTS avisos (
    id            {_PK},
    texto         TEXT NOT NULL,
    criado_por    INTEGER REFERENCES usuarios(id),
    criado_nome   TEXT,
    ativo         INTEGER NOT NULL DEFAULT 1,
    criado_em     {_TS} NOT NULL DEFAULT ({_NOW})
);

CREATE TABLE IF NOT EXISTS maos (
    id            {_PK},
    mesa_id       TEXT,
    torneio_id    TEXT,
    numero        INTEGER,
    board         TEXT,
    criado_em     {_TS} NOT NULL DEFAULT ({_NOW})
);
CREATE INDEX IF NOT EXISTS idx_maos_mesa ON maos(mesa_id);
CREATE INDEX IF NOT EXISTS idx_maos_torneio ON maos(torneio_id);

CREATE TABLE IF NOT EXISTS mao_jogadores (
    mao_id        INTEGER NOT NULL REFERENCES maos(id),
    usuario_id    INTEGER,
    apelido       TEXT,
    cartas        TEXT,
    foldou        INTEGER,
    delta         INTEGER,
    venceu        INTEGER,
    ganho         INTEGER,
    melhor        TEXT
);
CREATE INDEX IF NOT EXISTS idx_maoj_usuario ON mao_jogadores(usuario_id);

CREATE TABLE IF NOT EXISTS bloqueios (
    usuario_id    INTEGER NOT NULL REFERENCES usuarios(id),
    bloqueado_id  INTEGER NOT NULL REFERENCES usuarios(id),
    criado_em     {_TS} NOT NULL DEFAULT ({_NOW}),
    PRIMARY KEY (usuario_id, bloqueado_id)
);

CREATE TABLE IF NOT EXISTS denuncias (
    id            {_PK},
    de_usuario_id INTEGER REFERENCES usuarios(id),
    de_apelido    TEXT,
    alvo_apelido  TEXT,
    motivo        TEXT,
    status        TEXT NOT NULL DEFAULT 'aberta',
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
            # Roda CADA comando isolado: se um falhar, registra e SEGUE (não derruba o
            # app inteiro nem impede a criação das outras tabelas).
            for stmt in script.split(";"):
                s = stmt.strip()
                if not s:
                    continue
                try:
                    cur = self._raw.cursor()
                    cur.execute(s)
                    self._raw.commit()
                except Exception as e:  # noqa
                    try:
                        self._raw.rollback()
                    except Exception:
                        pass
                    print(f"[db] aviso ao criar/ajustar tabela: {type(e).__name__}: {e} "
                          f"| comando: {s[:100]}", flush=True)
        else:
            self._raw.executescript(script)

    def commit(self):
        self._raw.commit()


def conexao() -> Conexao:
    if not hasattr(_LOCAL, "conn"):
        if IS_PG:
            # connect_timeout: se o banco estiver lento/fora, falha em segundos em vez
            # de travar a SUBIDA do app por ~2 min (o que fazia o deploy do Render dar
            # "Timed out"). keepalives: detecta e evita conexões ociosas derrubadas.
            raw = psycopg2.connect(
                DATABASE_URL, connect_timeout=10,
                keepalives=1, keepalives_idle=30,
                keepalives_interval=10, keepalives_count=3,
            )
        else:
            raw = sqlite3.connect(_DB_PATH, check_same_thread=False)
            raw.row_factory = sqlite3.Row
            raw.execute("PRAGMA foreign_keys = ON")
            raw.execute("PRAGMA journal_mode = WAL")
        _LOCAL.conn = Conexao(raw)
    return _LOCAL.conn


# Colunas a garantir em bancos já existentes.
# (tabela, coluna, definição, grandfather) — grandfather=True marca as linhas
# JÁ existentes com 1 (ex.: contas antigas entram como "já verificadas").
_MIGRACOES = [
    ("usuarios", "admin", "INTEGER NOT NULL DEFAULT 0", False),
    ("usuarios", "verificado", "INTEGER NOT NULL DEFAULT 0", True),
    ("usuarios", "codigo_verif", "TEXT", False),
    ("usuarios", "codigo_expira", "INTEGER", False),
    # expiração da sessão (segurança): sessões antigas ficam sem expira_em (=NULL),
    # e o auth trata NULL como "expira já" -> pede login de novo.
    ("sessoes", "expira_em", "INTEGER", False),
]


def _colunas(conn: Conexao, tabela: str) -> set[str]:
    if IS_PG:
        rows = conn.execute(
            "SELECT column_name AS name FROM information_schema.columns "
            "WHERE table_name=?", (tabela,))
    else:
        rows = conn.execute(f"PRAGMA table_info({tabela})")
    return {r["name"] for r in rows}


def _migrar(conn: Conexao) -> None:
    """Adiciona colunas que faltarem em bancos já existentes (SQLite e PostgreSQL).
    Cada coluna é tratada isolada: falha em uma não impede as outras nem quebra o app."""
    cache: dict[str, set[str]] = {}
    for tabela, coluna, tipo, grandfather in _MIGRACOES:
        try:
            if tabela not in cache:
                cache[tabela] = _colunas(conn, tabela)
            if coluna in cache[tabela]:
                continue
            conn.execute(f"ALTER TABLE {tabela} ADD COLUMN {coluna} {tipo}")
            cache[tabela].add(coluna)
            if grandfather:
                # contas que já existiam antes desta coluna são consideradas OK
                conn.execute(f"UPDATE {tabela} SET {coluna}=1")
            conn.commit()
        except Exception as e:  # noqa
            try:
                conn._raw.rollback()
            except Exception:
                pass
            print(f"[db] aviso na migração {tabela}.{coluna}: {type(e).__name__}: {e}",
                  flush=True)


def inicializar() -> None:
    """Cria as tabelas e aplica migrações. NUNCA deixa uma falha aqui derrubar o app:
    o que der errado é registrado no log, e o servidor sobe mesmo assim."""
    conn = conexao()
    try:
        conn.executescript(_schema())
        conn.commit()
    except Exception as e:  # noqa
        print(f"[db] erro geral ao inicializar o schema: {type(e).__name__}: {e}", flush=True)
    try:
        _migrar(conn)
    except Exception as e:  # noqa
        print(f"[db] erro geral na migração: {type(e).__name__}: {e}", flush=True)
