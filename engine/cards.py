"""Cartas, naipes e baralho.

Representamos cada carta por um inteiro de rank (2..14) e um naipe (0..3).
Rank 11=J, 12=Q, 13=K, 14=A. O Ás pode valer 1 apenas na sequência A-2-3-4-5
(tratado no avaliador).
"""
from __future__ import annotations

import random
from dataclasses import dataclass

# Ordem de ranks: 2..10, J, Q, K, A
RANKS = list(range(2, 15))  # 14 = Ás
SUITS = list(range(4))      # 0 copas, 1 ouros, 2 paus, 3 espadas

RANK_NOMES = {
    2: "2", 3: "3", 4: "4", 5: "5", 6: "6", 7: "7", 8: "8", 9: "9",
    10: "10", 11: "Valete", 12: "Dama", 13: "Rei", 14: "Ás",
}
RANK_CURTO = {
    2: "2", 3: "3", 4: "4", 5: "5", 6: "6", 7: "7", 8: "8", 9: "9",
    10: "10", 11: "J", 12: "Q", 13: "K", 14: "A",
}
# Naipes: nome falado (para leitor de tela) + símbolo unicode
SUIT_NOMES = {0: "copas", 1: "ouros", 2: "paus", 3: "espadas"}
SUIT_SIMBOLO = {0: "♥", 1: "♦", 2: "♣", 3: "♠"}
SUIT_COR = {0: "vermelho", 1: "vermelho", 2: "preto", 3: "preto"}


@dataclass(frozen=True, order=True)
class Card:
    rank: int  # 2..14
    suit: int  # 0..3

    def __post_init__(self) -> None:
        if self.rank not in RANKS:
            raise ValueError(f"rank inválido: {self.rank}")
        if self.suit not in SUITS:
            raise ValueError(f"naipe inválido: {self.suit}")

    @property
    def nome_falado(self) -> str:
        """Ex.: 'Ás de espadas' — para leitores de tela."""
        return f"{RANK_NOMES[self.rank]} de {SUIT_NOMES[self.suit]}"

    @property
    def codigo(self) -> str:
        """Ex.: 'As' (Ás de espadas), '10h' (10 de copas). Para o front-end."""
        return f"{RANK_CURTO[self.rank]}{'hdcs'[self.suit]}"

    def __str__(self) -> str:
        return f"{RANK_CURTO[self.rank]}{SUIT_SIMBOLO[self.suit]}"


def baralho_completo() -> list[Card]:
    return [Card(r, s) for r in RANKS for s in SUITS]


class Deck:
    """Baralho embaralhável. Aceita `seed` para testes determinísticos."""

    def __init__(self, seed: int | None = None) -> None:
        self._rng = random.Random(seed)
        self.cards: list[Card] = baralho_completo()
        self._rng.shuffle(self.cards)

    def draw(self, n: int = 1) -> list[Card]:
        if n > len(self.cards):
            raise ValueError("cartas insuficientes no baralho")
        out = self.cards[:n]
        self.cards = self.cards[n:]
        return out

    def draw_one(self) -> Card:
        return self.draw(1)[0]

    def __len__(self) -> int:
        return len(self.cards)


def parse_card(codigo: str) -> Card:
    """Converte 'As', '10h', 'Kd' em Card. Útil para testes."""
    codigo = codigo.strip()
    suit_char = codigo[-1].lower()
    rank_str = codigo[:-1].upper()
    suit = {"h": 0, "d": 1, "c": 2, "s": 3}[suit_char]
    rank_map = {v: k for k, v in RANK_CURTO.items()}
    return Card(rank_map[rank_str], suit)


def parse_hand(texto: str) -> list[Card]:
    """'As Ks 10h' -> lista de Cards."""
    return [parse_card(t) for t in texto.split()]
