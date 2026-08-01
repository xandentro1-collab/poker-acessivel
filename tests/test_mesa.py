"""Teste de integração da Mesa: humano + bots jogando mãos completas."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server.mesa import Mesa


def test_mao_completa_com_bots():
    eventos = []
    mesa = Mesa("m1", "Teste", sb=25, bb=50, max_jogadores=6, stack_inicial=5000,
                on_evento=lambda m, e: eventos.append(e))
    mesa.sentar("humano", "Você", 5000, eh_bot=False)
    mesa.preencher_com_bots(3)
    total_inicial = sum(a.stack for a in mesa.jogadores_sentados())

    for _ in range(20):  # joga várias mãos
        if not mesa.pode_iniciar():
            break
        mesa.iniciar_mao()
        seguranca = 0
        # se a vez for do humano, sempre paga/passa para tocar a mão
        while mesa.mao_ativa and seguranca < 100:
            seguranca += 1
            if not mesa.mao or mesa.mao.to_act is None:
                break
            atual = mesa.mao.players[mesa.mao.to_act].id
            if atual == "humano":
                validas = mesa.mao.acoes_validas()
                if "check" in validas:
                    mesa.acao_humano("humano", "check")
                elif "call" in validas:
                    mesa.acao_humano("humano", "call", mesa.mao.aposta_atual)
                else:
                    mesa.acao_humano("humano", "fold")
            else:
                break  # bots são processados automaticamente
        # conservação de fichas a cada mão
        total = sum(a.stack for a in mesa.jogadores_sentados())
        assert total == total_inicial, f"fichas não conservadas: {total} != {total_inicial}"

    assert mesa.numero_mao >= 1
    assert len(eventos) > 0
    print(f"  jogadas {mesa.numero_mao} mãos, {len(eventos)} eventos, fichas conservadas")


def test_narracao_gerada():
    mesa = Mesa("m2", "Narra", sb=25, bb=50, stack_inicial=5000)
    mesa.sentar("humano", "Você", 5000)
    mesa.preencher_com_bots(2)
    mesa.iniciar_mao()
    assert any("Rodada" in t for t in mesa.log_narracao)
    assert any("small blind" in t for t in mesa.log_narracao)


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
