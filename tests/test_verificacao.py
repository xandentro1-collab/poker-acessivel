"""Testes de verificação de conta por código (anti-bot)."""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server import db, auth


def setup():
    os.environ["POKER_EXIGIR_CONVITE"] = "1"
    os.environ.pop("POKER_ADMIN_EMAILS", None)
    db.definir_caminho(":memory:")
    db.inicializar()


def _dono_e_convite():
    """Cria o dono (primeiro, verificado) e devolve um código de convite válido."""
    dono = auth.registrar("dono@ex.com", "Dono", "segredo123", verificacao_ativa=True)
    assert dono["verificado"] is True  # primeiro usuário não precisa verificar
    return auth.gerar_convites(1, dono["id"])[0]


def test_dono_nao_precisa_verificar():
    setup()
    dono = auth.registrar("dono@ex.com", "Dono", "segredo123", verificacao_ativa=True)
    assert dono["verificado"] is True
    assert dono["codigo"] is None


def test_testador_precisa_verificar():
    setup()
    cod = _dono_e_convite()
    u = auth.registrar("teste@ex.com", "Teste", "segredo123", convite=cod,
                       verificacao_ativa=True)
    assert u["verificado"] is False
    assert u["codigo"] is not None and len(u["codigo"]) == 6


def test_login_bloqueado_ate_verificar():
    setup()
    cod = _dono_e_convite()
    auth.registrar("teste@ex.com", "Teste", "segredo123", convite=cod, verificacao_ativa=True)
    # login antes de verificar -> erro
    try:
        auth.autenticar("teste@ex.com", "segredo123")
        assert False, "login deveria ser bloqueado antes da verificação"
    except auth.ErroAuth as e:
        assert "verificada" in str(e).lower()


def test_verificar_codigo_correto_e_login():
    setup()
    cod = _dono_e_convite()
    u = auth.registrar("teste@ex.com", "Teste", "segredo123", convite=cod, verificacao_ativa=True)
    # código errado falha
    try:
        auth.verificar_codigo("teste@ex.com", "000000")
        assert False
    except auth.ErroAuth:
        pass
    # código certo funciona
    r = auth.verificar_codigo("teste@ex.com", u["codigo"])
    assert r["ja_verificado"] is False
    # agora o login funciona
    logado = auth.autenticar("teste@ex.com", "segredo123")
    assert logado["email"] == "teste@ex.com"


def test_codigo_expirado():
    setup()
    cod = _dono_e_convite()
    u = auth.registrar("teste@ex.com", "Teste", "segredo123", convite=cod, verificacao_ativa=True)
    # força expiração no banco
    conn = db.conexao()
    conn.execute("UPDATE usuarios SET codigo_expira=? WHERE email=?",
                 (int(time.time()) - 10, "teste@ex.com"))
    conn.commit()
    try:
        auth.verificar_codigo("teste@ex.com", u["codigo"])
        assert False
    except auth.ErroAuth as e:
        assert "expirado" in str(e).lower()


def test_reenviar_gera_novo_codigo():
    setup()
    cod = _dono_e_convite()
    u = auth.registrar("teste@ex.com", "Teste", "segredo123", convite=cod, verificacao_ativa=True)
    novo = auth.reenviar_codigo("teste@ex.com")
    assert novo is not None and len(novo) == 6
    # o código antigo não vale mais; o novo vale
    try:
        auth.verificar_codigo("teste@ex.com", u["codigo"])
        assert False, "código antigo não deveria funcionar após reenvio"
    except auth.ErroAuth:
        pass
    r = auth.verificar_codigo("teste@ex.com", novo)
    assert r["ja_verificado"] is False


def test_sem_smtp_nao_exige_verificacao():
    setup()
    cod = _dono_e_convite()
    # verificacao_ativa=False (sem SMTP) -> testador entra verificado direto
    u = auth.registrar("teste@ex.com", "Teste", "segredo123", convite=cod,
                       verificacao_ativa=False)
    assert u["verificado"] is True
    assert auth.autenticar("teste@ex.com", "segredo123")["email"] == "teste@ex.com"


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
    os.environ.pop("POKER_EXIGIR_CONVITE", None)
    print(f"\n{len(fns) - falhas}/{len(fns)} testes passaram")
    return falhas


if __name__ == "__main__":
    sys.exit(1 if _run() else 0)
