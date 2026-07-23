"""IA simples para bots. Heurística por força relativa da mão + posição.

Não é um solver — é o suficiente para treino e para preencher mesas. A força é
estimada por Monte Carlo leve no preflop e pela avaliação real pós-flop.
"""
from __future__ import annotations

import random

from engine.evaluator import evaluate_best


def _forca_relativa(hole, board) -> float:
    """Retorna 0..1 estimando quão forte é a mão atual (heurística)."""
    if len(board) >= 3:
        forca, _ = evaluate_best(hole + board)
        # categoria 0..8 -> normaliza
        return min(1.0, forca[0] / 8.0 + 0.05 * (forca[1] if len(forca) > 1 else 0) / 14)
    # preflop: pontuação estilo Chen simplificada
    r = sorted((c.rank for c in hole), reverse=True)
    par = r[0] == r[1]
    suited = hole[0].suit == hole[1].suit
    base = r[0] / 14.0
    if par:
        base = 0.5 + r[0] / 28.0
    if suited:
        base += 0.08
    gap = abs(r[0] - r[1])
    if gap <= 1 and not par:
        base += 0.05
    return min(1.0, base)


def decidir(mao, jogador_id: str) -> tuple[str, int | None]:
    """Decide a ação do bot. Retorna (acao, valor_total_ou_None)."""
    validas = mao.acoes_validas()
    p = next(pl for pl in mao.players if pl.id == jogador_id)
    forca = _forca_relativa(p.hole, mao.board)
    ruido = random.uniform(-0.1, 0.1)
    f = max(0.0, min(1.0, forca + ruido))

    tem_check = "check" in validas
    custo_call = validas.get("call", 0)

    # Mão fraca
    if f < 0.35:
        if tem_check:
            return ("check", None)
        # paga só se barato (<= 5% do stack)
        if custo_call and custo_call <= p.stack * 0.05:
            return ("call", mao.aposta_atual)
        return ("fold", None)

    # Mão média
    if f < 0.65:
        if "raise" in validas and random.random() < 0.2:
            return ("raise", validas["raise"]["min"])
        if "call" in validas:
            return ("call", mao.aposta_atual)
        if "bet" in validas and random.random() < 0.3:
            return ("bet", validas["bet"]["min"])
        return ("check", None) if tem_check else ("fold", None)

    # Mão forte: agride
    if "raise" in validas:
        lim = validas["raise"]
        alvo = min(lim["max"], int(lim["min"] * random.uniform(1.0, 2.0)))
        return ("raise", alvo)
    if "bet" in validas:
        lim = validas["bet"]
        alvo = min(lim["max"], int(max(lim["min"], mao.pote_total * random.uniform(0.5, 1.0))))
        return ("bet", alvo)
    if "call" in validas:
        return ("call", mao.aposta_atual)
    return ("check", None) if tem_check else ("all_in", None)
