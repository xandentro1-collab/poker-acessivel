"""Estrutura de torneio Sit & Go: níveis de blind crescentes e premiação.

Puro e testável. A Mesa consome isto para saber os blinds do nível atual e como
dividir a premiação quando o torneio termina.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Nivel:
    sb: int
    bb: int
    ante: int = 0

    def __str__(self) -> str:
        base = f"Blinds {self.sb}/{self.bb}"
        return base + (f", ante {self.ante}" if self.ante else "")


# Estrutura "turbo" padrão (sobe rápido, boa para testes e Sit & Go).
ESTRUTURA_PADRAO: list[Nivel] = [
    Nivel(10, 20),
    Nivel(15, 30),
    Nivel(25, 50),
    Nivel(50, 100, 10),
    Nivel(75, 150, 15),
    Nivel(100, 200, 25),
    Nivel(150, 300, 30),
    Nivel(200, 400, 50),
    Nivel(300, 600, 75),
    Nivel(500, 1000, 100),
    Nivel(750, 1500, 150),
    Nivel(1000, 2000, 250),
]


def nivel_por_indice(estrutura: list[Nivel], idx: int) -> Nivel:
    """Retorna o nível; se passar do fim, fica no último (blinds máximos)."""
    if idx < 0:
        idx = 0
    return estrutura[min(idx, len(estrutura) - 1)]


def distribuicao_premios(num_jogadores: int) -> list[float]:
    """Fração do prêmio por colocação (índice 0 = campeão).

    Segue a lógica do PokerStars para Sit & Go de mesa única.
    """
    if num_jogadores <= 3:
        return [1.0]                    # winner takes all
    if num_jogadores <= 6:
        return [0.65, 0.35]             # top 2
    return [0.50, 0.30, 0.20]           # top 3


def calcular_premios(buy_in: int, num_jogadores: int) -> list[int]:
    """Prêmio em fichas/centavos por colocação. Ajusta sobras ao campeão."""
    pote = buy_in * num_jogadores
    fracoes = distribuicao_premios(num_jogadores)
    premios = [int(pote * f) for f in fracoes]
    premios[0] += pote - sum(premios)   # sobra de arredondamento vai ao 1º
    return premios
