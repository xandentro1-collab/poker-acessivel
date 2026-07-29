"""Social: amigos, convites para mesa e notificações por usuário.

- Amigos ficam no banco (tabela `amizades`), amizade é mútua (adicionar cria os
  dois lados).
- Notificações ficam em memória (dict por apelido). O navegador busca por polling
  em /api/notificacoes. Serve para convites de mesa (Fase 3) e para os avisos de
  presença/quadro de avisos (Fase 4).
"""
from __future__ import annotations

import itertools
import threading
import time

from . import db


# ==================== notificações (em memória) ====================
_lock = threading.RLock()
_notifs: dict[str, list[dict]] = {}     # apelido -> lista de notificações
_seq = itertools.count(1)


def notificar(apelido: str, tipo: str, texto: str, dados: dict | None = None) -> None:
    """Guarda uma notificação para o usuário `apelido` (entregue por polling)."""
    if not apelido:
        return
    with _lock:
        _notifs.setdefault(apelido, []).append({
            "id": next(_seq),
            "tipo": tipo,
            "texto": texto,
            "dados": dados or {},
            "ts": time.time(),
        })
        # não deixa crescer sem limite
        if len(_notifs[apelido]) > 50:
            _notifs[apelido] = _notifs[apelido][-50:]


def pegar_notificacoes(apelido: str, limpar: bool = True) -> list[dict]:
    """Devolve (e por padrão limpa) as notificações pendentes do usuário."""
    with _lock:
        itens = _notifs.get(apelido, [])
        if limpar:
            _notifs[apelido] = []
        return list(itens)


# ==================== amigos (no banco) ====================
def _uid_por_apelido(apelido: str):
    conn = db.conexao()
    row = conn.execute("SELECT id, apelido FROM usuarios WHERE lower(apelido)=?",
                       ((apelido or "").strip().lower(),)).fetchone()
    return (row["id"], row["apelido"]) if row else (None, None)


def _apelido_por_uid(uid):
    conn = db.conexao()
    row = conn.execute("SELECT apelido FROM usuarios WHERE id=?", (uid,)).fetchone()
    return row["apelido"] if row else None


def adicionar_amigo(uid: int, apelido_amigo: str) -> dict:
    """Cria amizade mútua entre `uid` e o dono de `apelido_amigo`.

    Retorna {"ok": bool, "erro"/"amigo": ...}.
    """
    amigo_id, nome_real = _uid_por_apelido(apelido_amigo)
    if not amigo_id:
        return {"ok": False, "erro": "Não encontrei ninguém com esse apelido."}
    if amigo_id == uid:
        return {"ok": False, "erro": "Você não pode adicionar você mesmo."}
    conn = db.conexao()
    # insere os dois lados (ignora se já existir)
    for a, b in ((uid, amigo_id), (amigo_id, uid)):
        ja = conn.execute("SELECT 1 FROM amizades WHERE usuario_id=? AND amigo_id=?",
                          (a, b)).fetchone()
        if not ja:
            conn.execute("INSERT INTO amizades (usuario_id, amigo_id) VALUES (?, ?)",
                         (a, b))
    conn.commit()
    # avisa o novo amigo
    meu_apelido = _apelido_por_uid(uid)
    notificar(nome_real, "amigo_novo",
              f"{meu_apelido} adicionou você como amigo.",
              {"de": meu_apelido})
    return {"ok": True, "amigo": nome_real}


def remover_amigo(uid: int, apelido_amigo: str) -> dict:
    amigo_id, nome_real = _uid_por_apelido(apelido_amigo)
    if not amigo_id:
        return {"ok": False, "erro": "Não encontrei ninguém com esse apelido."}
    conn = db.conexao()
    conn.execute("DELETE FROM amizades WHERE (usuario_id=? AND amigo_id=?) "
                 "OR (usuario_id=? AND amigo_id=?)",
                 (uid, amigo_id, amigo_id, uid))
    conn.commit()
    return {"ok": True, "amigo": nome_real}


def listar_amigos(uid: int) -> list[dict]:
    """Lista os amigos do usuário (apelido), em ordem alfabética."""
    conn = db.conexao()
    rows = conn.execute(
        "SELECT u.apelido AS apelido FROM amizades a "
        "JOIN usuarios u ON u.id = a.amigo_id "
        "WHERE a.usuario_id=? ORDER BY lower(u.apelido)", (uid,)).fetchall()
    return [{"apelido": r["apelido"]} for r in rows]


def sao_amigos(uid: int, apelido_amigo: str) -> bool:
    amigo_id, _ = _uid_por_apelido(apelido_amigo)
    if not amigo_id:
        return False
    conn = db.conexao()
    return conn.execute("SELECT 1 FROM amizades WHERE usuario_id=? AND amigo_id=?",
                        (uid, amigo_id)).fetchone() is not None


# ==================== convite para mesa ====================
def convidar_para_mesa(de_apelido: str, para_apelido: str, mesa_id: str,
                       mesa_nome: str) -> dict:
    """Envia a `para_apelido` um convite para entrar na mesa `mesa_id`."""
    alvo_id, nome_real = _uid_por_apelido(para_apelido)
    if not alvo_id:
        return {"ok": False, "erro": "Não encontrei ninguém com esse apelido."}
    if nome_real == de_apelido:
        return {"ok": False, "erro": "Você não pode convidar você mesmo."}
    notificar(nome_real, "convite_mesa",
              f"{de_apelido} convidou você para a mesa {mesa_nome}. "
              f"Aperte a tecla F2 para aceitar e entrar.",
              {"de": de_apelido, "mesa_id": mesa_id, "mesa_nome": mesa_nome})
    return {"ok": True, "convidado": nome_real}
