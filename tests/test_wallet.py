"""Testes de autenticação e carteira (banco em memória)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server import db, auth, wallet


def setup():
    db.definir_caminho(":memory:")
    db.inicializar()


def test_registro_e_login():
    setup()
    u = auth.registrar("a@b.com", "Fulano", "segredo123")
    assert u["id"] > 0
    logado = auth.autenticar("a@b.com", "segredo123")
    assert logado["id"] == u["id"]
    # login por apelido também
    assert auth.autenticar("Fulano", "segredo123")["id"] == u["id"]


def test_senha_errada():
    setup()
    auth.registrar("a@b.com", "Fulano", "segredo123")
    try:
        auth.autenticar("a@b.com", "errada")
        assert False
    except auth.ErroAuth:
        pass


def test_email_duplicado():
    setup()
    auth.registrar("a@b.com", "Fulano", "segredo123")
    try:
        auth.registrar("a@b.com", "Outro", "segredo123")
        assert False
    except auth.ErroAuth:
        pass


def test_validacoes():
    setup()
    for email, apelido, senha in [
        ("semarroba", "Nome", "segredo123"),
        ("a@b.com", "xy", "segredo123"),      # apelido curto
        ("a@b.com", "Nome", "123"),           # senha curta
    ]:
        try:
            auth.registrar(email, apelido, senha)
            assert False, f"deveria rejeitar {email},{apelido}"
        except auth.ErroAuth:
            pass


def test_sessao():
    setup()
    u = auth.registrar("a@b.com", "Fulano", "segredo123")
    tok = auth.criar_sessao(u["id"])
    assert auth.usuario_da_sessao(tok)["id"] == u["id"]
    auth.encerrar_sessao(tok)
    assert auth.usuario_da_sessao(tok) is None


def test_deposito_saque():
    setup()
    u = auth.registrar("a@b.com", "Fulano", "segredo123")
    assert wallet.saldo(u["id"]) == 0
    wallet.depositar(u["id"], 10000)   # R$100
    assert wallet.saldo(u["id"]) == 10000
    wallet.sacar(u["id"], 3000)
    assert wallet.saldo(u["id"]) == 7000


def test_saque_insuficiente():
    setup()
    u = auth.registrar("a@b.com", "Fulano", "segredo123")
    wallet.depositar(u["id"], 5000)
    try:
        wallet.sacar(u["id"], 6000)
        assert False
    except wallet.ErroCarteira:
        pass


def test_buy_in_e_cash_out():
    setup()
    u = auth.registrar("a@b.com", "Fulano", "segredo123")
    wallet.depositar(u["id"], 20000)
    wallet.debitar_buy_in(u["id"], 5000, "mesa1")
    assert wallet.saldo(u["id"]) == 15000
    # jogou e saiu com 8000 (lucro)
    wallet.creditar_cash_out(u["id"], 8000, "mesa1")
    assert wallet.saldo(u["id"]) == 23000


def test_formatar_reais():
    assert wallet.formatar_reais(12345) == "R$ 123,45"
    assert wallet.formatar_reais(0) == "R$ 0,00"
    assert wallet.formatar_reais(-500) == "-R$ 5,00"


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
