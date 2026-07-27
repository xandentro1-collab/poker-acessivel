"""Cadastro, login e sessões. Senhas com PBKDF2 (stdlib hashlib)."""
from __future__ import annotations

import hashlib
import hmac
import os
import re
import secrets

from . import db

ITERACOES = 200_000
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def exigir_convite() -> bool:
    """Se ligado, novos cadastros precisam de um código de convite válido.

    Controlado pela variável de ambiente POKER_EXIGIR_CONVITE (1 = liga).
    O primeiro usuário do sistema é sempre isento (vira admin).
    """
    return os.environ.get("POKER_EXIGIR_CONVITE", "0") == "1"


def _emails_admin() -> set[str]:
    raw = os.environ.get("POKER_ADMIN_EMAILS", "")
    return {e.strip().lower() for e in raw.split(",") if e.strip()}


def existe_algum_usuario() -> bool:
    """True se já há ao menos um usuário cadastrado.

    Usado para NÃO exigir convite do primeiríssimo usuário (que vira admin).
    """
    conn = db.conexao()
    return conn.execute("SELECT 1 FROM usuarios LIMIT 1").fetchone() is not None


class ErroAuth(Exception):
    pass


def _hash_senha(senha: str, salt: str) -> str:
    dk = hashlib.pbkdf2_hmac("sha256", senha.encode(), salt.encode(), ITERACOES)
    return dk.hex()


def registrar(email: str, apelido: str, senha: str, convite: str | None = None) -> dict:
    email = (email or "").strip().lower()
    apelido = (apelido or "").strip()
    if not EMAIL_RE.match(email):
        raise ErroAuth("e-mail inválido")
    if not (3 <= len(apelido) <= 20) or not re.match(r"^[\w ]+$", apelido):
        raise ErroAuth("apelido deve ter 3 a 20 caracteres (letras, números, espaço)")
    if len(senha) < 6:
        raise ErroAuth("a senha precisa ter ao menos 6 caracteres")

    conn = db.conexao()
    if conn.execute("SELECT 1 FROM usuarios WHERE email=?", (email,)).fetchone():
        raise ErroAuth("e-mail já cadastrado")
    if conn.execute("SELECT 1 FROM usuarios WHERE apelido=?", (apelido,)).fetchone():
        raise ErroAuth("apelido já em uso")

    # regra de convite (beta fechado). Primeiro usuário é isento e vira admin.
    total = conn.execute("SELECT COUNT(*) AS n FROM usuarios").fetchone()["n"]
    primeiro = total == 0
    codigo = (convite or "").strip().upper()
    linha_convite = None
    if exigir_convite() and not primeiro:
        if not codigo:
            raise ErroAuth("código de convite obrigatório")
        linha_convite = conn.execute(
            "SELECT * FROM convites WHERE codigo=? AND usado_por IS NULL", (codigo,)
        ).fetchone()
        if not linha_convite:
            raise ErroAuth("código de convite inválido ou já usado")

    admin = 1 if (primeiro or email in _emails_admin()) else 0
    salt = secrets.token_hex(16)
    senha_hash = _hash_senha(senha, salt)
    cur = conn.execute(
        "INSERT INTO usuarios (email, apelido, senha_hash, salt, admin) "
        "VALUES (?,?,?,?,?) RETURNING id",
        (email, apelido, senha_hash, salt, admin),
    )
    uid = cur.fetchone()["id"]
    if linha_convite is not None:
        conn.execute(
            "UPDATE convites SET usado_por=?, usado_em=datetime('now') WHERE codigo=?",
            (uid, codigo),
        )
    conn.commit()
    return {"id": uid, "email": email, "apelido": apelido, "admin": bool(admin)}


# ---------- convites e admin ----------
def is_admin(usuario_id: int) -> bool:
    conn = db.conexao()
    row = conn.execute("SELECT admin FROM usuarios WHERE id=?", (usuario_id,)).fetchone()
    return bool(row and row["admin"])


def gerar_convites(quantidade: int, criado_por: int) -> list[str]:
    quantidade = max(1, min(int(quantidade), 100))
    conn = db.conexao()
    codigos = []
    for _ in range(quantidade):
        codigo = secrets.token_hex(4).upper()  # 8 caracteres, ex.: 'A1B2C3D4'
        conn.execute("INSERT INTO convites (codigo, criado_por) VALUES (?,?)",
                     (codigo, criado_por))
        codigos.append(codigo)
    conn.commit()
    return codigos


def listar_convites(limite: int = 200) -> list[dict]:
    conn = db.conexao()
    rows = conn.execute(
        "SELECT c.codigo, c.criado_em, c.usado_em, u.apelido AS usado_apelido "
        "FROM convites c LEFT JOIN usuarios u ON u.id = c.usado_por "
        "ORDER BY c.criado_em DESC LIMIT ?", (limite,)
    ).fetchall()
    return [dict(r) for r in rows]


def listar_usuarios(limite: int = 500) -> list[dict]:
    conn = db.conexao()
    rows = conn.execute(
        "SELECT u.id, u.apelido, u.email, u.admin, u.criado_em, "
        "COALESCE((SELECT SUM(valor) FROM lancamentos l WHERE l.usuario_id=u.id),0) AS saldo "
        "FROM usuarios u ORDER BY u.id DESC LIMIT ?", (limite,)
    ).fetchall()
    return [dict(r) for r in rows]


def autenticar(email_ou_apelido: str, senha: str) -> dict:
    ident = (email_ou_apelido or "").strip().lower()
    conn = db.conexao()
    row = conn.execute(
        "SELECT * FROM usuarios WHERE email=? OR lower(apelido)=?", (ident, ident)
    ).fetchone()
    if not row:
        raise ErroAuth("usuário ou senha incorretos")
    esperado = row["senha_hash"]
    calculado = _hash_senha(senha, row["salt"])
    if not hmac.compare_digest(esperado, calculado):
        raise ErroAuth("usuário ou senha incorretos")
    return {"id": row["id"], "email": row["email"], "apelido": row["apelido"]}


def criar_sessao(usuario_id: int) -> str:
    token = secrets.token_urlsafe(32)
    conn = db.conexao()
    conn.execute("INSERT INTO sessoes (token, usuario_id) VALUES (?,?)", (token, usuario_id))
    conn.commit()
    return token


def usuario_da_sessao(token: str) -> dict | None:
    if not token:
        return None
    conn = db.conexao()
    row = conn.execute(
        "SELECT u.id, u.email, u.apelido FROM sessoes s "
        "JOIN usuarios u ON u.id = s.usuario_id WHERE s.token=?",
        (token,),
    ).fetchone()
    return dict(row) if row else None


def encerrar_sessao(token: str) -> None:
    conn = db.conexao()
    conn.execute("DELETE FROM sessoes WHERE token=?", (token,))
    conn.commit()
