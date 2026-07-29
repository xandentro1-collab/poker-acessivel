"""Testes de convite (beta fechado) e admin."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server import auth, db


def setup(exigir=False):
    os.environ["POKER_EXIGIR_CONVITE"] = "1" if exigir else "0"
    os.environ.pop("POKER_ADMIN_EMAILS", None)
    db.definir_caminho(":memory:")
    db.inicializar()


def test_primeiro_usuario_vira_admin():
    setup(exigir=True)
    # primeiro é isento de convite e vira admin
    u = auth.registrar("chefe@ex.com", "Chefe", "segredo123")
    assert u["admin"] is True
    assert auth.is_admin(u["id"])


def test_segundo_sem_convite_falha():
    setup(exigir=True)
    auth.registrar("chefe@ex.com", "Chefe", "segredo123")
    try:
        auth.registrar("novo@ex.com", "Novo", "segredo123")
        assert False, "deveria exigir convite"
    except auth.ErroAuth as e:
        assert "convite" in str(e).lower()


def test_convite_valido_e_reuso():
    setup(exigir=True)
    admin = auth.registrar("chefe@ex.com", "Chefe", "segredo123")
    cods = auth.gerar_convites(2, admin["id"])
    assert len(cods) == 2
    # usa um código
    u2 = auth.registrar("novo@ex.com", "Novo", "segredo123", convite=cods[0])
    assert u2["admin"] is False
    # reusar o mesmo código falha
    try:
        auth.registrar("outro@ex.com", "Outro", "segredo123", convite=cods[0])
        assert False, "código já usado deveria falhar"
    except auth.ErroAuth:
        pass
    # código inválido falha
    try:
        auth.registrar("mais@ex.com", "Mais", "segredo123", convite="ZZZZZZZZ")
        assert False
    except auth.ErroAuth:
        pass


def test_email_admin_isento_de_convite():
    # e-mails em POKER_ADMIN_EMAILS entram sem convite e viram admin, mesmo com
    # beta fechado e outros usuários já existentes.
    setup(exigir=True)
    os.environ["POKER_ADMIN_EMAILS"] = "dono@ex.com"
    auth.registrar("primeiro@ex.com", "Primeiro", "segredo123")  # ocupa o banco
    # dono@ex.com não tem código, mas é admin designado -> deve entrar como admin
    dono = auth.registrar("dono@ex.com", "Dono", "segredo123", convite="qualquer")
    assert dono["admin"] is True
    os.environ.pop("POKER_ADMIN_EMAILS", None)


def test_cadastro_aberto_ignora_convite():
    setup(exigir=False)
    auth.registrar("chefe@ex.com", "Chefe", "segredo123")
    # sem exigência, cadastra sem código normalmente
    u = auth.registrar("livre@ex.com", "Livre", "segredo123")
    assert u["id"] > 0


def test_listagens_admin():
    setup(exigir=True)
    admin = auth.registrar("chefe@ex.com", "Chefe", "segredo123")
    cods = auth.gerar_convites(3, admin["id"])
    auth.registrar("novo@ex.com", "Novo", "segredo123", convite=cods[0])
    usuarios = auth.listar_usuarios()
    assert len(usuarios) == 2
    convites = auth.listar_convites()
    usados = [c for c in convites if c["usado_em"]]
    assert len(usados) == 1


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
