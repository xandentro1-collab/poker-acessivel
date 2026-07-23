"""Testes do avaliador de mãos. Rodar: python -m pytest ou python tests/test_evaluator.py"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.cards import parse_hand
from engine.evaluator import (
    CARTA_ALTA, PAR, DOIS_PARES, TRINCA, SEQUENCIA, FLUSH,
    FULL_HOUSE, QUADRA, STRAIGHT_FLUSH,
    evaluate_best, evaluate_5, comparar, descrever_forca,
)


def cat(texto):
    return evaluate_best(parse_hand(texto))[0][0]


def test_categorias_basicas():
    assert cat("As Ks Qs Js 10s") == STRAIGHT_FLUSH   # royal
    assert cat("9h 9d 9c 9s 2h") == QUADRA
    assert cat("Kh Kd Kc 2s 2h") == FULL_HOUSE
    assert cat("As 10s 7s 4s 2s") == FLUSH
    assert cat("5h 6d 7c 8s 9h") == SEQUENCIA
    assert cat("Qh Qd Qc 4s 2h") == TRINCA
    assert cat("Ah Ad Kc Ks 2h") == DOIS_PARES
    assert cat("Ah Ad 9c 5s 2h") == PAR
    assert cat("Ah Kd 9c 5s 2h") == CARTA_ALTA


def test_roda_a2345():
    # A-2-3-4-5: sequência com carta alta 5
    forca = evaluate_5(parse_hand("Ah 2d 3c 4s 5h"))
    assert forca[0] == SEQUENCIA
    assert forca[1] == 5
    # 6-5-4-3-2 deve ganhar da roda (carta alta 6 > 5)
    assert comparar(parse_hand("6h 5d 4c 3s 2h"), parse_hand("Ah 2d 3c 4s 5h")) == 1


def test_straight_flush_roda():
    forca = evaluate_5(parse_hand("As 2s 3s 4s 5s"))
    assert forca[0] == STRAIGHT_FLUSH
    assert forca[1] == 5  # roda de espadas, alta = 5


def test_flush_vs_sequencia():
    # flush ganha de sequência
    assert comparar(parse_hand("As 10s 7s 4s 2s"), parse_hand("5h 6d 7c 8s 9h")) == 1


def test_melhor_de_7():
    # 7 cartas: 2 hole + 5 board. Deve achar o flush.
    mao = "As Ks | 2s 5s 9s 7h 3d".replace("|", "")
    forca, melhores = evaluate_best(parse_hand(mao))
    assert forca[0] == FLUSH
    assert len(melhores) == 5


def test_desempate_kicker():
    # Par de ases, kicker decide
    a = parse_hand("Ah Ad Kc 5s 2h")
    b = parse_hand("As Ac Qc 5s 2h")
    assert comparar(a, b) == 1  # K kicker > Q kicker


def test_empate_exato():
    a = parse_hand("Ah Ad Kc 5s 2h")
    b = parse_hand("As Ac Ks 5d 2c")
    assert comparar(a, b) == 0


def test_full_house_vs_full_house():
    # full de reis > full de damas
    a = parse_hand("Kh Kd Kc 2s 2h")
    b = parse_hand("Qh Qd Qc As Ah")
    assert comparar(a, b) == 1


def test_descricoes():
    assert descrever_forca(evaluate_5(parse_hand("As Ks Qs Js 10s"))) == "Royal flush"
    assert "Quadra" in descrever_forca(evaluate_5(parse_hand("9h 9d 9c 9s 2h")))
    assert "Full house" in descrever_forca(evaluate_5(parse_hand("Kh Kd Kc 2s 2h")))


def _run():
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    falhas = 0
    for fn in fns:
        try:
            fn()
            print(f"  OK  {fn.__name__}")
        except AssertionError as e:
            falhas += 1
            print(f" FALHA {fn.__name__}: {e}")
        except Exception as e:  # noqa
            falhas += 1
            print(f" ERRO {fn.__name__}: {type(e).__name__}: {e}")
    print(f"\n{len(fns) - falhas}/{len(fns)} testes passaram")
    return falhas


if __name__ == "__main__":
    sys.exit(1 if _run() else 0)
