"""Testes da camada web (rotas HTTP) usando o test client do Flask.

Não sobe servidor nem navegador: usa app.test_client(), que roda tudo na mesma
thread — por isso o SQLite ':memory:' funciona aqui.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server import db, social
from server.app import app, GM


def reset():
    os.environ["POKER_EXIGIR_CONVITE"] = "0"
    os.environ.pop("POKER_ADMIN_EMAILS", None)
    db.definir_caminho(":memory:")
    db.inicializar()
    GM.mesas.clear()
    GM.assinantes.clear()
    GM.torneios.clear()
    social._notifs.clear()
    social._online.clear()
    app.config["TESTING"] = True


def cliente():
    return app.test_client()


def registrar(c, apelido, email, senha="senha123"):
    return c.post("/api/registrar", json={"apelido": apelido, "email": email, "senha": senha})


# ---------------- auth / sessão ----------------
def test_registrar_e_lobby():
    reset()
    c = cliente()
    r = registrar(c, "Ana", "ana@ex.com")
    assert r.status_code == 200 and r.get_json()["ok"] is True
    # já logado: lobby acessível
    assert c.get("/lobby").status_code == 200
    # sem login: redireciona para /entrar
    assert cliente().get("/lobby").status_code in (301, 302)


def test_login_e_logout():
    reset()
    registrar(cliente(), "Ana", "ana@ex.com")  # cria a conta
    c = cliente()
    r = c.post("/api/login", json={"identificador": "Ana", "senha": "senha123"})
    assert r.get_json()["ok"] is True
    c.post("/api/logout")
    assert c.get("/lobby").status_code in (301, 302)   # deslogado


def test_login_senha_errada():
    reset()
    registrar(cliente(), "Ana", "ana@ex.com")
    r = cliente().post("/api/login", json={"identificador": "Ana", "senha": "errada"})
    assert r.get_json()["ok"] is False


# ---------------- mesa ----------------
def test_criar_e_sentar():
    reset()
    c = cliente()
    registrar(c, "Ana", "ana@ex.com")
    r = c.post("/api/mesa/criar", json={"modo": "cash", "bots": 1, "tempo_acao": 0})
    mid = r.get_json()["mesa_id"]
    assert mid in GM.mesas
    r2 = c.post(f"/api/mesa/{mid}/sentar", json={"buy_in": 50})
    assert r2.get_json()["ok"] is True
    assert c.get(f"/mesa/{mid}").status_code == 200


# ---------------- amigos / online ----------------
def test_amigos_fluxo():
    reset()
    a = cliente(); registrar(a, "Ana", "ana@ex.com")
    b = cliente(); registrar(b, "Bruno", "bruno@ex.com")
    # adicionar mútuo
    assert a.post("/api/amigos/adicionar", json={"apelido": "Bruno"}).get_json()["ok"]
    assert [x["apelido"] for x in a.get("/api/amigos").get_json()["amigos"]] == ["Bruno"]
    assert [x["apelido"] for x in b.get("/api/amigos").get_json()["amigos"]] == ["Ana"]
    # inexistente e a si mesmo falham
    assert a.post("/api/amigos/adicionar", json={"apelido": "Ninguem"}).status_code == 400
    assert a.post("/api/amigos/adicionar", json={"apelido": "Ana"}).status_code == 400
    # remover apaga dos dois lados
    a.post("/api/amigos/remover", json={"apelido": "Bruno"})
    assert a.get("/api/amigos").get_json()["amigos"] == []
    assert b.get("/api/amigos").get_json()["amigos"] == []


def test_adicionar_varios():
    reset()
    a = cliente(); registrar(a, "Ana", "ana@ex.com")
    registrar(cliente(), "Bruno", "bruno@ex.com")
    registrar(cliente(), "Carlos", "carlos@ex.com")
    r = a.post("/api/amigos/adicionar_varios", json={"apelidos": ["Bruno", "Carlos"]})
    assert set(r.get_json()["adicionados"]) == {"Bruno", "Carlos"}


def test_online_amigos_primeiro():
    reset()
    a = cliente(); registrar(a, "Ana", "ana@ex.com")
    b = cliente(); registrar(b, "Bruno", "bruno@ex.com")
    d = cliente(); registrar(d, "Carlos", "carlos@ex.com")
    a.post("/api/amigos/adicionar", json={"apelido": "Carlos"})
    # todos ficam online (heartbeat via /api/online ou /api/notificacoes)
    for cl in (a, b, d):
        cl.get("/api/notificacoes")
    online = a.get("/api/online").get_json()["online"]
    # Carlos (amigo) antes de Bruno (não amigo)
    assert online[0]["apelido"] == "Carlos" and online[0]["amigo"] is True
    assert any(p["apelido"] == "Bruno" and p["amigo"] is False for p in online)


# ---------------- convite de mesa + notificações ----------------
def test_convite_mesa_notifica():
    reset()
    a = cliente(); registrar(a, "Ana", "ana@ex.com")
    b = cliente(); registrar(b, "Bruno", "bruno@ex.com")
    mid = a.post("/api/mesa/criar", json={"modo": "cash", "bots": 0}).get_json()["mesa_id"]
    a.post(f"/api/mesa/{mid}/sentar", json={"buy_in": 50})
    assert a.post(f"/api/mesa/{mid}/convidar", json={"apelido": "Bruno"}).get_json()["ok"]
    notifs = b.get("/api/notificacoes").get_json()["notificacoes"]
    assert any(n["tipo"] == "convite_mesa" and n["dados"]["mesa_id"] == mid for n in notifs)
    # ler de novo esvazia (semântica de polling)
    assert b.get("/api/notificacoes").get_json()["notificacoes"] == []


# ---------------- avisos (quadro) ----------------
def test_avisos_admin_e_dispensar():
    reset()
    a = cliente(); registrar(a, "Ana", "ana@ex.com")   # 1º usuário = admin
    b = cliente(); registrar(b, "Bruno", "bruno@ex.com")
    assert a.post("/api/avisos/criar", json={"texto": "Torneio hoje 20h"}).get_json()["ok"]
    # não-admin não publica
    assert b.post("/api/avisos/criar", json={"texto": "spam"}).status_code == 403
    avisos = b.get("/api/avisos").get_json()["avisos"]
    assert len(avisos) == 1
    aid = avisos[0]["id"]
    # Bruno dispensa só para si
    b.post(f"/api/avisos/{aid}/dispensar")
    assert b.get("/api/avisos").get_json()["avisos"] == []
    assert len(a.get("/api/avisos").get_json()["avisos"]) == 1
    # admin dá baixa para todos
    a.post(f"/api/avisos/{aid}/baixar")
    assert a.get("/api/avisos").get_json()["avisos"] == []


def test_preferencia_conexao():
    reset()
    a = cliente(); registrar(a, "Ana", "ana@ex.com")
    assert a.get("/api/preferencias/avisar_conexao").get_json()["ligado"] is True  # padrão
    a.post("/api/preferencias/avisar_conexao", json={"ligado": False})
    assert a.get("/api/preferencias/avisar_conexao").get_json()["ligado"] is False


# ---------------- chat (via GM, sem WebSocket) ----------------
class _FakeWS:
    def __init__(self, jid):
        self._jogador_id = jid
        self.enviados = []

    def send(self, s):
        import json
        self.enviados.append(json.loads(s))


def test_chat_publico_e_pv():
    reset()
    registrar(cliente(), "Ana", "ana@ex.com")
    registrar(cliente(), "Bruno", "bruno@ex.com")
    a, b = _FakeWS("Ana"), _FakeWS("Bruno")
    GM.assinantes["m1"] = [a, b]
    # público: os dois recebem
    ok, _ = GM.enviar_chat("m1", "Ana", "oi galera")
    assert ok and a.enviados[-1]["texto"] == "oi galera" and b.enviados[-1]["texto"] == "oi galera"
    # PV por e-mail (Bruno está na mesa) -> só Ana e Bruno
    a.enviados.clear(); b.enviados.clear()
    ok, _ = GM.enviar_chat("m1", "Ana", "segredo", para="bruno@ex.com")
    assert ok and b.enviados and b.enviados[0]["privado"] is True
    # PV para quem não existe
    ok, motivo = GM.enviar_chat("m1", "Ana", "x", para="ninguem@ex.com")
    assert ok is False


def test_chat_pv_para_online_fora_da_mesa():
    reset()
    registrar(cliente(), "Ana", "ana@ex.com")
    registrar(cliente(), "Carlos", "carlos@ex.com")
    social.marcar_online("Carlos")            # online, mas não na mesa
    a = _FakeWS("Ana")
    GM.assinantes["m1"] = [a]
    ok, _ = GM.enviar_chat("m1", "Ana", "oi carlos", para="Carlos")
    assert ok is True
    notifs = social.pegar_notificacoes("Carlos")
    assert any(n["tipo"] == "chat_pv" for n in notifs)


# ---------------- torneio ----------------
def test_torneio_criar_e_convidar():
    reset()
    a = cliente(); registrar(a, "Ana", "ana@ex.com")   # admin
    b = cliente(); registrar(b, "Bruno", "bruno@ex.com")
    a.post("/api/amigos/adicionar", json={"apelido": "Bruno"})
    r = a.post("/api/torneio/criar", json={"nome": "Torneio", "num_participantes": 6,
                                           "stack_inicial": 5000, "buy_in": 0})
    tid = r.get_json()["torneio_id"]
    assert tid in GM.torneios
    # convidar todos os amigos ([] = todos)
    assert a.post(f"/api/torneio/{tid}/convidar", json={"apelidos": []}).get_json()["ok"]
    notifs = b.get("/api/notificacoes").get_json()["notificacoes"]
    assert any(n["tipo"] == "convite_torneio" and n["dados"]["tid"] == tid for n in notifs)


def test_torneio_inscrever_e_estado():
    reset()
    a = cliente(); registrar(a, "Ana", "ana@ex.com")   # admin
    tid = a.post("/api/torneio/criar", json={"nome": "T", "num_participantes": 6,
                                             "stack_inicial": 5000, "buy_in": 0}).get_json()["torneio_id"]
    assert a.post(f"/api/torneio/{tid}/inscrever").get_json()["ok"] is True
    est = a.get(f"/api/torneio/{tid}/estado").get_json()
    assert est["ok"] is True and est["inscrito"] is True
    assert a.get("/torneios").status_code == 200
    assert a.get(f"/torneio/{tid}").status_code == 200


def test_relatorio_rota():
    reset()
    a = cliente(); registrar(a, "Ana", "ana@ex.com")
    mid = a.post("/api/mesa/criar", json={"modo": "cash", "bots": 1}).get_json()["mesa_id"]
    a.post(f"/api/mesa/{mid}/sentar", json={"buy_in": 50})
    r = a.post(f"/api/mesa/{mid}/relatorio", json={"escopo": "proprio"}).get_json()
    assert r["ok"] is True and "texto" in r


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    falhas = 0
    for fn in fns:
        try:
            fn(); print(f"  OK  {fn.__name__}")
        except Exception as e:  # noqa
            import traceback
            falhas += 1
            print(f" FALHA {fn.__name__}: {type(e).__name__}: {e}")
            traceback.print_exc()
    print(f"\n{len(fns) - falhas}/{len(fns)} passaram")
    sys.exit(1 if falhas else 0)
