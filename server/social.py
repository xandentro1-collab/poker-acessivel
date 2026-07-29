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


# ==================== presença (em memória) ====================
_online: dict[str, float] = {}      # apelido -> último "visto" (epoch)
JANELA_ONLINE = 15.0                # segundos sem aparecer -> considerado offline


def usuarios_online() -> list[str]:
    agora = time.time()
    with _lock:
        return [ap for ap, t in _online.items() if agora - t <= JANELA_ONLINE]


def online_para(uid: int, meu_apelido: str) -> list[dict]:
    """Lista de pessoas ONLINE (menos você), em ordem alfabética, com os AMIGOS
    primeiro. Cada item: {apelido, amigo: bool}."""
    amigos = {a["apelido"] for a in listar_amigos(uid)}
    pessoas = [ap for ap in usuarios_online() if ap != meu_apelido]
    pessoas.sort(key=lambda ap: (ap not in amigos, ap.lower()))  # amigos primeiro, depois A-Z
    return [{"apelido": ap, "amigo": ap in amigos} for ap in pessoas]


def marcar_online(apelido: str) -> bool:
    """Marca o usuário como online (chamado a cada polling). Retorna True se ele
    ACABOU de conectar (estava offline até agora)."""
    if not apelido:
        return False
    agora = time.time()
    with _lock:
        anterior = _online.get(apelido)
        _online[apelido] = agora
        # limpa quem sumiu há muito tempo (não deixa o dict crescer)
        for ap in [a for a, t in _online.items() if agora - t > 300]:
            _online.pop(ap, None)
    return anterior is None or (agora - anterior) > JANELA_ONLINE


# ==================== preferências (no banco) ====================
def get_pref(uid: int, chave: str, padrao: str = "") -> str:
    conn = db.conexao()
    row = conn.execute("SELECT valor FROM preferencias WHERE usuario_id=? AND chave=?",
                       (uid, chave)).fetchone()
    return row["valor"] if row and row["valor"] is not None else padrao


def set_pref(uid: int, chave: str, valor: str) -> None:
    conn = db.conexao()
    existe = conn.execute("SELECT 1 FROM preferencias WHERE usuario_id=? AND chave=?",
                          (uid, chave)).fetchone()
    if existe:
        conn.execute("UPDATE preferencias SET valor=? WHERE usuario_id=? AND chave=?",
                     (valor, uid, chave))
    else:
        conn.execute("INSERT INTO preferencias (usuario_id, chave, valor) VALUES (?, ?, ?)",
                     (uid, chave, valor))
    conn.commit()


def avisar_conexao_ligado(uid: int) -> bool:
    """Preferência 'receber aviso quando alguém conecta' (padrão: ligado)."""
    return get_pref(uid, "avisar_conexao", "1") != "0"


def notificar_conexao(quem_apelido: str) -> None:
    """Avisa os outros usuários online (que aceitam) que `quem` acabou de entrar."""
    conn = db.conexao()
    for ap in usuarios_online():
        if ap == quem_apelido:
            continue
        row = conn.execute("SELECT id FROM usuarios WHERE lower(apelido)=?",
                           (ap.lower(),)).fetchone()
        if row and avisar_conexao_ligado(row["id"]):
            notificar(ap, "conexao", f"{quem_apelido} entrou na plataforma.",
                      {"de": quem_apelido})


# ==================== quadro de avisos (no banco) ====================
def criar_aviso(uid: int, nome: str, texto: str) -> dict:
    texto = (texto or "").strip()[:300]
    if not texto:
        return {"ok": False, "erro": "Escreva o texto do aviso."}
    conn = db.conexao()
    conn.execute("INSERT INTO avisos (texto, criado_por, criado_nome, ativo) "
                 "VALUES (?, ?, ?, 1)", (texto, uid, nome))
    conn.commit()
    return {"ok": True}


def listar_avisos_ativos() -> list[dict]:
    conn = db.conexao()
    rows = conn.execute("SELECT id, texto, criado_por, criado_nome FROM avisos "
                        "WHERE ativo=1 ORDER BY id DESC").fetchall()
    return [{"id": r["id"], "texto": r["texto"], "criado_por": r["criado_por"],
             "criado_nome": r["criado_nome"]} for r in rows]


def baixar_aviso(uid: int, aviso_id: int, eh_admin: bool) -> dict:
    """Dá baixa (desativa) um aviso. Só o criador ou um admin pode."""
    conn = db.conexao()
    row = conn.execute("SELECT criado_por FROM avisos WHERE id=?", (aviso_id,)).fetchone()
    if not row:
        return {"ok": False, "erro": "Aviso não encontrado."}
    if not eh_admin and row["criado_por"] != uid:
        return {"ok": False, "erro": "Só quem criou o aviso (ou um admin) pode dar baixa."}
    conn.execute("UPDATE avisos SET ativo=0 WHERE id=?", (aviso_id,))
    conn.commit()
    return {"ok": True}


def dispensar_aviso(uid: int, aviso_id: int) -> None:
    """O usuário não quer mais ver ESTE aviso (fica guardado nas preferências)."""
    set_pref(uid, f"aviso_disp_{aviso_id}", "1")


def avisos_para(uid: int) -> list[dict]:
    """Avisos ativos que o usuário ainda NÃO dispensou."""
    return [a for a in listar_avisos_ativos()
            if get_pref(uid, f"aviso_disp_{a['id']}", "0") != "1"]


# ==================== amigos (no banco) ====================
def _uid_por_apelido(apelido: str):
    conn = db.conexao()
    row = conn.execute("SELECT id, apelido FROM usuarios WHERE lower(apelido)=?",
                       ((apelido or "").strip().lower(),)).fetchone()
    return (row["id"], row["apelido"]) if row else (None, None)


def resolver_apelido(valor: str) -> str | None:
    """Aceita um apelido OU um e-mail e devolve o apelido real (ou None)."""
    valor = (valor or "").strip().lower()
    if not valor:
        return None
    conn = db.conexao()
    row = conn.execute("SELECT apelido FROM usuarios WHERE lower(apelido)=? OR lower(email)=?",
                       (valor, valor)).fetchone()
    return row["apelido"] if row else None


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
