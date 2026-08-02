"""Jogo Responsável: lembrete de tempo de jogo e pausa/autoexclusão (cool-off).

Guarda tudo nas preferências por usuário (social.get_pref/set_pref, tabela
`preferencias`). Filosofia de segurança:

- O bloqueio de jogo só **estende** o prazo, nunca encurta — assim o jogador não
  desfaz a própria proteção num impulso.
- O **login nunca é bloqueado**: mesmo em pausa, a pessoa entra no site, ajusta
  configurações e vê a data em que poderá jogar de novo. Só **entrar em mesas e
  torneios** é impedido enquanto a pausa está ativa.

Nenhuma função aqui deixa o jogo quebrar: em erro, devolve o valor mais seguro.
"""
import time
from datetime import datetime

from . import social

# chaves na tabela de preferências
K_LIMITE = "jr_limite_sessao_min"   # minutos de lembrete; "0" = desligado
K_BLOQUEIO = "jr_bloqueio_ate"      # epoch: não pode entrar em jogos até aqui

LIMITE_MAX_MIN = 24 * 60            # teto do lembrete: 24 horas


def _int(valor, padrao=0):
    try:
        return int(float(valor))
    except (TypeError, ValueError):
        return padrao


# ---------- lembrete de tempo de jogo ----------
def limite_min(uid: int) -> int:
    return _int(social.get_pref(uid, K_LIMITE, "0"))


def set_limite_min(uid: int, minutos) -> int:
    m = max(0, min(_int(minutos), LIMITE_MAX_MIN))
    social.set_pref(uid, K_LIMITE, str(m))
    return m


# ---------- pausa / autoexclusão (bloqueio de jogo) ----------
def bloqueio_ate(uid: int) -> int:
    return _int(social.get_pref(uid, K_BLOQUEIO, "0"))


def bloqueado(uid: int) -> bool:
    return bloqueio_ate(uid) > time.time()


def bloquear_por(uid: int, horas) -> int:
    """Bloqueia entrar em jogos por `horas`. Só ESTENDE: nunca reduz um prazo já ativo."""
    try:
        horas = max(0.0, float(horas))
    except (TypeError, ValueError):
        horas = 0.0
    novo = int(time.time() + horas * 3600)
    ate = max(novo, bloqueio_ate(uid))
    social.set_pref(uid, K_BLOQUEIO, str(ate))
    return ate


def quando_libera(uid: int) -> str:
    """Data/hora em que o bloqueio termina, em texto pt-BR (ou '' se não há bloqueio)."""
    ate = bloqueio_ate(uid)
    if ate <= time.time():
        return ""
    try:
        return datetime.fromtimestamp(ate).strftime("%d/%m/%Y às %H:%M")
    except (OverflowError, OSError, ValueError):
        return ""


def estado(uid: int, login_ts=None) -> dict:
    agora = int(time.time())
    minutos_jogando = int((agora - int(login_ts)) // 60) if login_ts else 0
    return {
        "limite_min": limite_min(uid),
        "bloqueio_ate": bloqueio_ate(uid),
        "bloqueado": bloqueado(uid),
        "quando_libera": quando_libera(uid),
        "minutos_jogando": max(0, minutos_jogando),
        "agora": agora,
    }
