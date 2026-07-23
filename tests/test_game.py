"""Testes da máquina de estados da mão."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.cards import Deck
from engine.game import MaoDePoker, Player, Street


def novo_jogo(stacks, button=0, sb=25, bb=50, seed=42):
    players = [Player(id=f"p{i}", nome=f"J{i}", stack=s) for i, s in enumerate(stacks)]
    mao = MaoDePoker(players, button_pos=button, small_blind=sb, big_blind=bb, deck=Deck(seed))
    mao.iniciar()
    return mao, players


def test_blinds_postados():
    mao, ps = novo_jogo([1000, 1000, 1000], button=0)
    # 3-handed: SB = pos1, BB = pos2
    assert ps[1].stack == 975   # -25
    assert ps[2].stack == 950   # -50
    assert mao.pote_total == 75
    # primeiro a agir preflop é o botão (pos0) em 3-handed
    assert mao.to_act == 0


def test_heads_up_botao_e_sb():
    mao, ps = novo_jogo([1000, 1000], button=0)
    # heads-up: botão(pos0) = SB, pos1 = BB
    assert ps[0].stack == 975
    assert ps[1].stack == 950
    # preflop no HU: botão/SB age primeiro
    assert mao.to_act == 0


def test_fold_ate_vencedor():
    mao, ps = novo_jogo([1000, 1000, 1000], button=0)
    mao.aplicar_acao("p0", "fold")
    mao.aplicar_acao("p1", "fold")
    assert mao.encerrada
    # p2 (BB) leva SB+BB = 75; tinha 950, fica 1025
    assert ps[2].stack == 1025
    assert mao.vencedores[0]["jogador"] == "p2"


def test_call_e_check_ate_flop():
    mao, ps = novo_jogo([1000, 1000, 1000], button=0)
    mao.aplicar_acao("p0", "call", 50)   # botão paga 50
    mao.aplicar_acao("p1", "call", 50)   # SB completa
    mao.aplicar_acao("p2", "check")      # BB dá check
    assert mao.street == Street.FLOP
    assert len(mao.board) == 3
    assert mao.pote_total == 150


def test_raise_minimo():
    mao, ps = novo_jogo([1000, 1000, 1000], button=0)
    # aposta atual = 50 (BB), min raise = 50 -> total mínimo de raise = 100
    try:
        mao.aplicar_acao("p0", "raise", 70)  # incremento 20 < 50
        assert False, "deveria rejeitar raise abaixo do mínimo"
    except ValueError:
        pass
    mao.aplicar_acao("p0", "raise", 100)  # válido
    assert mao.aposta_atual == 100


def test_reabertura_por_raise():
    mao, ps = novo_jogo([1000, 1000, 1000], button=0)
    mao.aplicar_acao("p0", "call", 50)
    mao.aplicar_acao("p1", "raise", 150)  # SB aumenta
    # BB (p2) ainda tem de agir, e p0 também (reaberto)
    assert mao.to_act == 2
    mao.aplicar_acao("p2", "call", 150)
    assert mao.to_act == 0                # voltou para p0
    mao.aplicar_acao("p0", "call", 150)
    assert mao.street == Street.FLOP


def test_side_pot_all_in():
    # p0 curto (100), p1 e p2 com 1000. p0 all-in preflop.
    mao, ps = novo_jogo([100, 1000, 1000], button=0, sb=25, bb=50)
    # to_act = p0 (botão). p0 all-in 100.
    mao.aplicar_acao("p0", "all_in")           # total 100
    mao.aplicar_acao("p1", "call", 100)        # SB paga
    mao.aplicar_acao("p2", "call", 100)        # BB paga
    # todos com aposta_rodada 100; p0 all-in. Vai direto ao showdown (p0 all-in,
    # mas p1 e p2 ainda podem agir no flop). Não encerrou ainda.
    assert not mao.encerrada
    assert mao.street == Street.FLOP
    # p1 e p2 dão check até o river
    for _ in range(3):  # flop, turn, river
        mao.aplicar_acao("p1", "check")
        mao.aplicar_acao("p2", "check")
    assert mao.encerrada
    # conservação: soma dos stacks == soma inicial
    assert sum(p.stack for p in ps) == 2100


def test_conservacao_de_fichas():
    # Propriedade fundamental: fichas nunca somem nem aparecem.
    import random
    for seed in range(30):
        stacks = [random.Random(seed).randint(100, 1000) for _ in range(4)]
        total_inicial = sum(stacks)
        mao, ps = novo_jogo(stacks, button=seed % 4, seed=seed)
        rng = random.Random(seed + 100)
        guarda = 0
        while not mao.encerrada and guarda < 200:
            guarda += 1
            if mao.to_act is None:
                break
            pid = ps[mao.to_act].id
            validas = mao.acoes_validas()
            escolha = rng.choice(list(validas.keys()))
            try:
                if escolha in ("bet", "raise"):
                    lim = validas[escolha]
                    mao.aplicar_acao(pid, escolha, lim["min"])
                elif escolha == "all_in":
                    mao.aplicar_acao(pid, "all_in")
                elif escolha == "call":
                    mao.aplicar_acao(pid, "call", mao.aposta_atual)
                else:
                    mao.aplicar_acao(pid, escolha)
            except ValueError:
                mao.aplicar_acao(pid, "fold")
        assert mao.encerrada, f"mão não encerrou (seed {seed})"
        assert sum(p.stack for p in ps) == total_inicial, f"fichas não conservadas (seed {seed})"


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
            import traceback
            falhas += 1
            print(f" ERRO {fn.__name__}: {type(e).__name__}: {e}")
            traceback.print_exc()
    print(f"\n{len(fns) - falhas}/{len(fns)} testes passaram")
    return falhas


if __name__ == "__main__":
    sys.exit(1 if _run() else 0)
