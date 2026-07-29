"""Cadastro, login e sessões. Senhas com PBKDF2 (stdlib hashlib)."""
from __future__ import annotations

import hashlib
import hmac
import os
import re
import secrets
import time

from . import db

ITERACOES = 200_000
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
CODIGO_VALIDADE_SEG = 15 * 60  # o código de verificação vale 15 minutos


def _gerar_codigo() -> str:
    """Código numérico de 6 dígitos para verificação de conta."""
    return f"{secrets.randbelow(1_000_000):06d}"


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


def registrar(email: str, apelido: str, senha: str, convite: str | None = None,
              verificacao_ativa: bool = False) -> dict:
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

    # regra de convite (beta fechado). São isentos de convite: o primeiro usuário
    # e os e-mails designados como admin (POKER_ADMIN_EMAILS) — ambos viram admin.
    total = conn.execute("SELECT COUNT(*) AS n FROM usuarios").fetchone()["n"]
    primeiro = total == 0
    eh_admin_email = email in _emails_admin()
    codigo = (convite or "").strip().upper()
    linha_convite = None
    if exigir_convite() and not primeiro and not eh_admin_email:
        if not codigo:
            raise ErroAuth("código de convite obrigatório")
        linha_convite = conn.execute(
            "SELECT * FROM convites WHERE codigo=? AND usado_por IS NULL", (codigo,)
        ).fetchone()
        if not linha_convite:
            raise ErroAuth("código de convite inválido ou já usado")

    admin = 1 if (primeiro or eh_admin_email) else 0
    # Verificação por e-mail: exigida para testadores comuns (não para o dono nem
    # admins designados), e só quando o envio de e-mail está configurado.
    exigir_verif = verificacao_ativa and not primeiro and not eh_admin_email
    verificado = 0 if exigir_verif else 1
    cod_verif = _gerar_codigo() if exigir_verif else None
    cod_expira = int(time.time()) + CODIGO_VALIDADE_SEG if exigir_verif else None

    salt = secrets.token_hex(16)
    senha_hash = _hash_senha(senha, salt)
    cur = conn.execute(
        "INSERT INTO usuarios (email, apelido, senha_hash, salt, admin, "
        "verificado, codigo_verif, codigo_expira) "
        "VALUES (?,?,?,?,?,?,?,?) RETURNING id",
        (email, apelido, senha_hash, salt, admin, verificado, cod_verif, cod_expira),
    )
    uid = cur.fetchone()["id"]
    if linha_convite is not None:
        conn.execute(
            "UPDATE convites SET usado_por=?, usado_em=datetime('now') WHERE codigo=?",
            (uid, codigo),
        )
    conn.commit()
    return {"id": uid, "email": email, "apelido": apelido, "admin": bool(admin),
            "verificado": bool(verificado), "codigo": cod_verif}


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


def excluir_usuario(usuario_id: int) -> None:
    """Remove um usuário e seus dados (lançamentos, sessões). Libera convites."""
    conn = db.conexao()
    conn.execute("UPDATE convites SET usado_por=NULL WHERE usado_por=?", (usuario_id,))
    conn.execute("UPDATE convites SET criado_por=NULL WHERE criado_por=?", (usuario_id,))
    conn.execute("DELETE FROM lancamentos WHERE usuario_id=?", (usuario_id,))
    conn.execute("DELETE FROM sessoes WHERE usuario_id=?", (usuario_id,))
    conn.execute("DELETE FROM usuarios WHERE id=?", (usuario_id,))
    conn.commit()


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
    if not row["verificado"]:
        raise ErroAuth("conta ainda não verificada. Confira o código enviado ao seu e-mail.")
    return {"id": row["id"], "email": row["email"], "apelido": row["apelido"]}


# ---------- verificação de conta por código ----------
def verificar_codigo(email: str, codigo: str) -> dict:
    """Confere o código de verificação; se válido, ativa a conta e a retorna."""
    email = (email or "").strip().lower()
    codigo = (codigo or "").strip()
    conn = db.conexao()
    row = conn.execute("SELECT * FROM usuarios WHERE email=?", (email,)).fetchone()
    if not row:
        raise ErroAuth("conta não encontrada")
    if row["verificado"]:
        return {"id": row["id"], "email": row["email"], "apelido": row["apelido"],
                "ja_verificado": True}
    if not row["codigo_verif"] or not codigo:
        raise ErroAuth("código inválido")
    if row["codigo_expira"] and int(time.time()) > int(row["codigo_expira"]):
        raise ErroAuth("código expirado. Peça um novo código.")
    if not hmac.compare_digest(str(row["codigo_verif"]), codigo):
        raise ErroAuth("código incorreto")
    conn.execute(
        "UPDATE usuarios SET verificado=1, codigo_verif=NULL, codigo_expira=NULL WHERE id=?",
        (row["id"],),
    )
    conn.commit()
    return {"id": row["id"], "email": row["email"], "apelido": row["apelido"],
            "ja_verificado": False}


def reenviar_codigo(email: str) -> str | None:
    """Gera um novo código para uma conta não verificada e o retorna (p/ envio)."""
    email = (email or "").strip().lower()
    conn = db.conexao()
    row = conn.execute("SELECT * FROM usuarios WHERE email=?", (email,)).fetchone()
    if not row or row["verificado"]:
        return None
    novo = _gerar_codigo()
    expira = int(time.time()) + CODIGO_VALIDADE_SEG
    conn.execute("UPDATE usuarios SET codigo_verif=?, codigo_expira=? WHERE id=?",
                 (novo, expira, row["id"]))
    conn.commit()
    return novo


# Tempo de inatividade que mantém a sessão viva. Enquanto a pessoa usa o site (ou
# tem uma aba aberta, que faz polling), a sessão é renovada. Depois de ficar todo
# esse tempo SEM uso (ex.: navegador fechado), a sessão expira e pede login de novo.
SESSAO_INATIVIDADE_SEG = int(float(os.environ.get("POKER_SESSAO_HORAS", "2")) * 3600)
# Só regrava a expiração no banco quando falta menos disto (evita escrever a cada
# batida de presença de 4s).
_RENOVAR_QUANDO_FALTAR = SESSAO_INATIVIDADE_SEG // 2


def criar_sessao(usuario_id: int) -> str:
    token = secrets.token_urlsafe(32)
    conn = db.conexao()
    expira = int(time.time()) + SESSAO_INATIVIDADE_SEG
    conn.execute("INSERT INTO sessoes (token, usuario_id, expira_em) VALUES (?,?,?)",
                 (token, usuario_id, expira))
    conn.commit()
    return token


def usuario_da_sessao(token: str) -> dict | None:
    if not token:
        return None
    conn = db.conexao()
    row = conn.execute(
        "SELECT u.id, u.email, u.apelido, u.admin, s.expira_em FROM sessoes s "
        "JOIN usuarios u ON u.id = s.usuario_id WHERE s.token=?",
        (token,),
    ).fetchone()
    if not row:
        return None
    agora = int(time.time())
    expira = row["expira_em"]
    # sessão sem expiração (antiga) ou já vencida -> encerra e exige novo login
    if expira is None or agora >= expira:
        try:
            conn.execute("DELETE FROM sessoes WHERE token=?", (token,))
            conn.commit()
        except Exception:
            pass
        return None
    # renova por inatividade (throttle: só grava quando já passou da metade)
    if expira - agora < _RENOVAR_QUANDO_FALTAR:
        try:
            conn.execute("UPDATE sessoes SET expira_em=? WHERE token=?",
                         (agora + SESSAO_INATIVIDADE_SEG, token))
            conn.commit()
        except Exception:
            pass
    d = dict(row)
    d.pop("expira_em", None)
    return d


def encerrar_sessao(token: str) -> None:
    conn = db.conexao()
    conn.execute("DELETE FROM sessoes WHERE token=?", (token,))
    conn.commit()
