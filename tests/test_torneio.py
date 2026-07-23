"""Testes de torneio (blinds crescentes, eliminação, premiação) e timer."""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.torneio import calcular_premios, distribuicao_premios, nivel_por_indice, ESTRUTURA_PADRAO
from server.mesa import Mesa


def test_estrutura_premios():
    # winner-takes-all para <=3
    assert distribuicao_premios(2) == [1.0]
    assert distribuicao_premios(3) == [1.0]
    # top 2 para 4-6
    assert len(distribuicao_premios(6)) == 2
    # top 3 para 7+
    assert len(distribuicao_premios(9)) == 3
    # prêmios somam o pote total (conservação)
    for n in [2, 4, 6, 9]:
        premios = calcular_premios(1000, n)
        assert sum(premios) == 1000 * n, f"premios não somam pote para {n}"


def test_niveis_crescentes():
    n0 = nivel_por_indice(ESTRUTURA_PADRAO, 0)
    n5 = nivel_por_indice(ESTRUTURA_PADRAO, 5)
    assert n5.bb > n0.bb
    # além do fim, fica no último
    ultimo = nivel_por_indice(ESTRUTURA_PADRAO, 999)
    assert ultimo == ESTRUTURA_PADRAO[-1]


def test_sitngo_completa_com_campeao():
    premios_pagos = []
    mesa = Mesa("t1", "SitGo", modo="sitngo", torneio=True, duracao_nivel=0,
                buy_in=1000, stack_inicial=1500, max_jogadores=6,
                on_premiar=lambda a, v, c: premios_pagos.append((a.nome, v, c)))
    mesa.preencher_com_bots(4)
    total_fichas = sum(a.stack for a in mesa.jogadores_sentados())

    guarda = 0
    while mesa.pode_iniciar() and not mesa.torneio_encerrado and guarda < 500:
        guarda += 1
        mesa.iniciar_mao()
        # bots jogam sozinhos; a mão já resolve no iniciar/processar_bots
        # mas se parar numa vez de humano não há humano aqui, então segue
        if mesa.mao_ativa:
            # força resolução: todos os que faltam são bots -> já resolveu
            break_guard = 0
            while mesa.mao_ativa and break_guard < 100:
                break_guard += 1
                if mesa.mao and mesa.mao.to_act is not None:
                    # só bots nesta mesa; se travar, aborta
                    break
                break

    assert mesa.torneio_encerrado, "torneio deveria terminar com um campeão"
    # todos os 4 entrantes classificados
    assert len(mesa.classificacao) == 4, f"esperado 4 classificados, veio {len(mesa.classificacao)}"
    colocacoes = sorted(r["colocacao"] for r in mesa.classificacao)
    assert colocacoes == [1, 2, 3, 4], colocacoes
    # prêmios somam o pote (conservação de prêmios)
    total_premios = sum(r["premio"] for r in mesa.classificacao)
    assert total_premios == 1000 * 4, f"prêmios {total_premios} != pote {4000}"


def test_timer_auto_fold():
    mesa = Mesa("t2", "Timer", modo="cash", sb=25, bb=50, stack_inicial=5000,
                tempo_acao=30)
    mesa.sentar("humano", "Você", 5000, eh_bot=False)
    mesa.preencher_com_bots(1)  # heads-up
    mesa.iniciar_mao()
    # se for a vez do humano, há deadline
    if mesa.mao and mesa.mao.to_act is not None and \
       mesa.mao.players[mesa.mao.to_act].id == "humano":
        assert mesa.deadline is not None
        # força expiração
        mesa.deadline = time.time() - 1
        mudou = mesa.tick()
        assert mudou, "tick deveria aplicar auto-ação ao expirar"
        assert any("não agiu a tempo" in t for t in mesa.log_narracao)


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
