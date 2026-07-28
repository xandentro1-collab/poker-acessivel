"""Avaliação de mãos de poker (5 melhores cartas de 7).

A força de uma mão é um tuple comparável: (categoria, *desempates).
Categorias maiores = mão melhor. Comparação lexicográfica resolve os desempates.
"""
from __future__ import annotations

from collections import Counter
from itertools import combinations

from .cards import Card, RANK_NOMES, baralho_completo

# Categorias (maior = melhor)
CARTA_ALTA = 0
PAR = 1
DOIS_PARES = 2
TRINCA = 3
SEQUENCIA = 4
FLUSH = 5
FULL_HOUSE = 6
QUADRA = 7
STRAIGHT_FLUSH = 8

CATEGORIA_NOME = {
    CARTA_ALTA: "Carta alta",
    PAR: "Par",
    DOIS_PARES: "Dois pares",
    TRINCA: "Trinca",
    SEQUENCIA: "Sequência",
    FLUSH: "Flush",
    FULL_HOUSE: "Full house",
    QUADRA: "Quadra",
    STRAIGHT_FLUSH: "Straight flush",
}


def _straight_high(ranks: set[int]) -> int | None:
    """Retorna o rank mais alto de uma sequência de 5, ou None.

    Trata a roda A-2-3-4-5 (Ás como 1), cuja carta alta é 5.
    """
    if len(ranks) < 5:
        return None
    # Roda: A,2,3,4,5
    if {14, 2, 3, 4, 5}.issubset(ranks):
        melhor = 5
    else:
        melhor = None
    ordenados = sorted(ranks, reverse=True)
    for alto in ordenados:
        if alto < 5:
            break
        if all((alto - i) in ranks for i in range(5)):
            melhor = max(melhor or 0, alto)
            break
    return melhor


def evaluate_5(cards: list[Card]) -> tuple:
    """Avalia exatamente 5 cartas. Retorna tuple de força comparável."""
    assert len(cards) == 5
    ranks = sorted((c.rank for c in cards), reverse=True)
    suits = [c.suit for c in cards]
    rank_count = Counter(ranks)
    # ordena por (frequência, rank) desc — chave para pares/trincas/etc.
    por_freq = sorted(rank_count.items(), key=lambda kv: (kv[1], kv[0]), reverse=True)
    freqs = [f for _, f in por_freq]
    kickers = [r for r, _ in por_freq]

    is_flush = len(set(suits)) == 1
    straight_high = _straight_high(set(ranks))

    if is_flush and straight_high is not None:
        return (STRAIGHT_FLUSH, straight_high)
    if freqs[0] == 4:
        return (QUADRA, kickers[0], kickers[1])
    if freqs[0] == 3 and freqs[1] == 2:
        return (FULL_HOUSE, kickers[0], kickers[1])
    if is_flush:
        return (FLUSH, *ranks)
    if straight_high is not None:
        return (SEQUENCIA, straight_high)
    if freqs[0] == 3:
        return (TRINCA, kickers[0], kickers[1], kickers[2])
    if freqs[0] == 2 and freqs[1] == 2:
        return (DOIS_PARES, kickers[0], kickers[1], kickers[2])
    if freqs[0] == 2:
        return (PAR, kickers[0], kickers[1], kickers[2], kickers[3])
    return (CARTA_ALTA, *ranks)


def evaluate_best(cards: list[Card]) -> tuple[tuple, list[Card]]:
    """Melhor mão de 5 dentre 5, 6 ou 7 cartas.

    Retorna (forca, melhores_5_cartas).
    """
    if len(cards) < 5:
        raise ValueError("são necessárias ao menos 5 cartas")
    melhor_forca = None
    melhor_combo: list[Card] = []
    for combo in combinations(cards, 5):
        forca = evaluate_5(list(combo))
        if melhor_forca is None or forca > melhor_forca:
            melhor_forca = forca
            melhor_combo = list(combo)
    return melhor_forca, melhor_combo


def descrever_forca(forca: tuple) -> str:
    """Descrição falável da mão, para leitor de tela."""
    cat = forca[0]
    nome = CATEGORIA_NOME[cat]
    r = RANK_NOMES
    if cat == STRAIGHT_FLUSH:
        if forca[1] == 14:
            return "Royal flush"
        return f"Straight flush até {r[forca[1]]}"
    if cat == QUADRA:
        return f"Quadra de {r[forca[1]]}"
    if cat == FULL_HOUSE:
        return f"Full house de {r[forca[1]]} com {r[forca[2]]}"
    if cat == FLUSH:
        return f"Flush, carta alta {r[forca[1]]}"
    if cat == SEQUENCIA:
        return f"Sequência até {r[forca[1]]}"
    if cat == TRINCA:
        return f"Trinca de {r[forca[1]]}"
    if cat == DOIS_PARES:
        return f"Dois pares, {r[forca[1]]} e {r[forca[2]]}"
    if cat == PAR:
        return f"Par de {r[forca[1]]}"
    return f"Carta alta {r[forca[1]]}"


def comparar(cards_a: list[Card], cards_b: list[Card]) -> int:
    """Compara duas mãos (5-7 cartas). 1 se A ganha, -1 se B, 0 empate."""
    fa, _ = evaluate_best(cards_a)
    fb, _ = evaluate_best(cards_b)
    return (fa > fb) - (fa < fb)


def equidade(hole: list[Card], board: list[Card], num_oponentes: int,
             iteracoes: int | None = None) -> float:
    """Chance (%) de vencer a mão, por Monte Carlo, contra N oponentes aleatórios.

    Considera o board atual (pré-flop/flop/turn/river) e completa o resto ao acaso.
    Empates contam meia vitória (dividido). Usa a força OFICIAL das mãos.
    """
    import random as _random
    if not hole or len(hole) < 2:
        return 0.0
    if num_oponentes < 1:
        return 100.0
    if iteracoes is None:   # menos iterações com mais oponentes -> resposta rápida
        iteracoes = max(400, min(1500, 2200 // num_oponentes))
    usadas = set(hole) | set(board)
    baralho = [c for c in baralho_completo() if c not in usadas]
    faltam_board = 5 - len(board)
    precisa = faltam_board + num_oponentes * 2
    if precisa > len(baralho):
        return 0.0
    rng = _random.Random()
    vitorias = 0.0
    for _ in range(iteracoes):
        rng.shuffle(baralho)
        i = 0
        board_sim = board + baralho[i:i + faltam_board]; i += faltam_board
        minha, _c = evaluate_best(hole + board_sim)
        melhor_op = None
        for _o in range(num_oponentes):
            op = baralho[i:i + 2]; i += 2
            fop, _c2 = evaluate_best(op + board_sim)
            if melhor_op is None or fop > melhor_op:
                melhor_op = fop
        if minha > melhor_op:
            vitorias += 1.0
        elif minha == melhor_op:
            vitorias += 0.5
    return round(100.0 * vitorias / iteracoes, 1)


def descrever_melhor(cards: list[Card]) -> str:
    """Melhor combinação FEITA com as cartas atuais (mão + board parcial).

    Se a melhor coisa for só carta alta (nenhum par), retorna 'Nada'.
    Funciona com 2 a 7 cartas (pré-flop tem só 2).
    """
    if not cards or len(cards) < 2:
        return "Nada"
    if len(cards) >= 5:
        forca, _ = evaluate_best(cards)
        return "Nada" if forca[0] == CARTA_ALTA else descrever_forca(forca)
    # 2 a 4 cartas: procura par/trinca/quadra entre o que há
    cont = Counter(c.rank for c in cards)
    freq = max(cont.values())
    r = RANK_NOMES
    if freq >= 4:
        return f"Quadra de {r[max(k for k, v in cont.items() if v == 4)]}"
    if freq == 3:
        return f"Trinca de {r[max(k for k, v in cont.items() if v == 3)]}"
    if freq == 2:
        pares = sorted((k for k, v in cont.items() if v == 2), reverse=True)
        if len(pares) >= 2:
            return f"Dois pares, {r[pares[0]]} e {r[pares[1]]}"
        return f"Par de {r[pares[0]]}"
    return "Nada"
