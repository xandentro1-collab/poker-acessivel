"""Testes da camada web (rotas HTTP) usando o test client do Flask.

Não sobe servidor nem navegador: usa app.test_client(), que roda tudo na mesma
thread — por isso o SQLite ':memory:' funciona aqui.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import server.app as srvapp
from server import db, social
from server.app import GM, app


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
    srvapp._login_falhas.clear()
    app.config["TESTING"] = True


def cliente():
    return app.test_client()


_cpf_contador = [100000000]


def _cpf_gerado():
    """Gera um CPF válido e único para os testes (calcula os dígitos verificadores)."""
    _cpf_contador[0] += 1
    base = str(_cpf_contador[0])[-9:].rjust(9, "0")

    def dig(nums):
        s = sum(int(n) * p for n, p in zip(nums, range(len(nums) + 1, 1, -1)))
        r = (s * 10) % 11
        return "0" if r == 10 else str(r)

    d1 = dig(base)
    return base + d1 + dig(base + d1)


def registrar(c, apelido, email, senha="senha123", cpf=None):
    if cpf is None:
        cpf = _cpf_gerado()
    return c.post("/api/registrar",
                  json={"apelido": apelido, "email": email, "senha": senha, "cpf": cpf})


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
    # o estado expõe os dados do resumo de confirmação (entrada/fichas/jogadores por mesa)
    for campo in ("buy_in", "stack_inicial", "jogadores_por_mesa", "premio_total"):
        assert campo in est, campo
    assert a.get("/torneios").status_code == 200
    assert a.get(f"/torneio/{tid}").status_code == 200


def test_relatorio_rota():
    reset()
    a = cliente(); registrar(a, "Ana", "ana@ex.com")
    mid = a.post("/api/mesa/criar", json={"modo": "cash", "bots": 1}).get_json()["mesa_id"]
    a.post(f"/api/mesa/{mid}/sentar", json={"buy_in": 50})
    r = a.post(f"/api/mesa/{mid}/relatorio", json={"escopo": "proprio"}).get_json()
    assert r["ok"] is True and "texto" in r


def test_historico_no_banco_e_stats():
    reset()
    from server import historia
    from server.mesa import Mesa
    m = Mesa("mh", "T", sb=25, bb=50, max_jogadores=6, stack_inicial=5000,
             on_mao_gravada=historia.salvar_mao_registro)
    m.sentar("Ana", "Ana", 5000, eh_bot=False, usuario_id=1)
    m.preencher_com_bots(2)
    for _ in range(5):
        if not m.pode_iniciar():
            break
        m.iniciar_mao()
        g = 0
        while m.mao_ativa and g < 300:
            g += 1
            ta = m.mao.to_act
            if ta is None:
                break
            p = m.mao.players[ta]
            if p.id != "Ana":
                break  # bots jogam sozinhos (via _processar_bots interno)
            a = m.mao.acoes_validas()
            m.acao_humano("Ana", "check" if "check" in a else ("call" if "call" in a else "fold"))
    # gravou no banco
    conn = db.conexao()
    n_maos = conn.execute("SELECT COUNT(*) AS c FROM maos WHERE mesa_id='mh'").fetchone()["c"]
    n_linhas_ana = conn.execute(
        "SELECT COUNT(*) AS c FROM mao_jogadores WHERE usuario_id=1").fetchone()["c"]
    assert n_maos >= 1
    # estatísticas do usuário 1 são consistentes (Ana pode ter quebrado antes do fim,
    # então esteve em ALGUMAS das mãos — nunca em mais do que o total).
    st = historia.stats_usuario(1)
    assert st["maos_jogadas"] >= 1
    assert st["maos_jogadas"] == n_linhas_ana <= n_maos
    assert st["maos_ganhas"] <= st["maos_jogadas"]


def test_csrf_origem_invalida_bloqueia():
    reset()
    registrar(cliente(), "Ana", "ana@ex.com")
    c = cliente()
    # POST vindo de outro site (Origin diferente) é bloqueado
    r = c.post("/api/login", json={"identificador": "Ana", "senha": "senha123"},
               headers={"Origin": "http://site-malicioso.com"})
    assert r.status_code == 403
    # mesmo site (Origin bate com o host do test client) passa
    r2 = c.post("/api/login", json={"identificador": "Ana", "senha": "senha123"},
                headers={"Origin": "http://localhost"})
    assert r2.status_code == 200 and r2.get_json()["ok"] is True


def test_rate_limit_login():
    reset()
    registrar(cliente(), "Ana", "ana@ex.com")
    c = cliente()
    # erra a senha várias vezes
    for _ in range(srvapp.LOGIN_MAX_FALHAS):
        assert c.post("/api/login", json={"identificador": "Ana", "senha": "errada"}).status_code == 400
    # a próxima (mesmo com a senha certa) é bloqueada por excesso de tentativas
    r = c.post("/api/login", json={"identificador": "Ana", "senha": "senha123"})
    assert r.status_code == 429


def test_bloquear_silencia_no_chat():
    reset()
    a = cliente(); registrar(a, "Ana", "ana@ex.com")
    registrar(cliente(), "Bruno", "bruno@ex.com")
    registrar(cliente(), "Carlos", "carlos@ex.com")
    # Ana bloqueia Bruno
    assert a.post("/api/bloquear", json={"apelido": "Bruno"}).get_json()["ok"]
    assert [x["apelido"] for x in a.get("/api/bloqueados").get_json()["bloqueados"]] == ["Bruno"]
    # mesa com Ana, Bruno (remetente) e Carlos
    wa, wb, wc = _FakeWS("Ana"), _FakeWS("Bruno"), _FakeWS("Carlos")
    GM.assinantes["m1"] = [wa, wb, wc]
    ok, _ = GM.enviar_chat("m1", "Bruno", "oi a todos")
    assert ok
    assert not wa.enviados          # Ana bloqueou Bruno -> não recebe
    assert wb.enviados              # o proprio Bruno vê o que mandou
    assert wc.enviados              # Carlos (não bloqueou) recebe
    # desbloquear volta a receber
    a.post("/api/desbloquear", json={"apelido": "Bruno"})
    wa.enviados.clear()
    GM.enviar_chat("m1", "Bruno", "de novo")
    assert wa.enviados


def test_denunciar_e_admin_ve():
    reset()
    a = cliente(); registrar(a, "Ana", "ana@ex.com")    # 1º = admin
    b = cliente(); registrar(b, "Bruno", "bruno@ex.com")
    # Bruno denuncia (não-admin pode denunciar)
    assert b.post("/api/denunciar", json={"apelido": "Ana", "motivo": "xingou"}).get_json()["ok"]
    # admin (Ana) vê a denúncia; não-admin não
    assert b.get("/api/denuncias").status_code == 403
    dl = a.get("/api/denuncias").get_json()["denuncias"]
    assert len(dl) == 1 and dl[0]["alvo"] == "Ana" and dl[0]["de"] == "Bruno"
    did = dl[0]["id"]
    # resolver
    assert a.post(f"/api/denuncias/{did}/resolver").get_json()["ok"]
    assert a.get("/api/denuncias").get_json()["denuncias"][0]["status"] == "resolvida"


def test_perfil_rota():
    reset()
    a = cliente(); registrar(a, "Ana", "ana@ex.com")
    assert a.get("/perfil").status_code == 200
    j = a.get("/api/perfil").get_json()
    assert j["ok"] and "stats" in j and j["apelido"] == "Ana"


def test_avatar_escolha_e_no_assento():
    reset()
    a = cliente(); registrar(a, "Ana", "ana@ex.com")
    # padrão: sem boneco escolhido
    assert a.get("/api/preferencias/avatar").get_json()["avatar"] == ""
    # id inválido é recusado
    assert a.post("/api/preferencias/avatar", json={"avatar": "xx"}).status_code == 400
    # escolhe um válido e persiste
    assert a.post("/api/preferencias/avatar", json={"avatar": "f2"}).get_json()["avatar"] == "f2"
    assert a.get("/api/preferencias/avatar").get_json()["avatar"] == "f2"
    # ao sentar, o assento leva o boneco escolhido e ele vai no estado do cliente
    mid = a.post("/api/mesa/criar", json={"modo": "cash", "bots": 0}).get_json()["mesa_id"]
    a.post(f"/api/mesa/{mid}/sentar", json={"buy_in": 50})
    ana = next(x for x in GM.mesas[mid].assentos if x and x.jogador_id == "Ana")
    assert ana.avatar == "f2"
    est = GM.mesas[mid].estado(ponto_de_vista="Ana")
    assert any(s and s.get("avatar") == "f2" for s in est["assentos"])


def test_cadastro_exige_cpf_valido():
    reset()
    # sem CPF -> recusa
    r = cliente().post("/api/registrar",
                       json={"apelido": "Ana", "email": "ana@ex.com", "senha": "senha123"})
    assert r.status_code == 400 and "CPF" in r.get_json()["erro"]
    # CPF inválido -> recusa
    r = cliente().post("/api/registrar", json={"apelido": "Ana", "email": "ana@ex.com",
                                               "senha": "senha123", "cpf": "111.111.111-11"})
    assert r.status_code == 400
    # CPF válido -> ok
    cpf = _cpf_gerado()
    assert registrar(cliente(), "Ana", "ana@ex.com", cpf=cpf).get_json()["ok"] is True
    # o MESMO CPF em outra conta -> recusa (evita duplicidade)
    r2 = registrar(cliente(), "Bruno", "bruno@ex.com", cpf=cpf)
    assert r2.status_code == 400 and "CPF" in r2.get_json()["erro"]


def test_loja_fichas_e_assinatura_sandbox():
    reset()
    from server import pagamentos, wallet
    a = cliente(); registrar(a, "Ana", "ana@ex.com")
    conn = db.conexao()
    uid = conn.execute("SELECT id FROM usuarios WHERE apelido='Ana'").fetchone()["id"]
    prod = a.get("/api/loja/produtos").get_json()
    assert prod["ok"] and prod["sandbox"] is True and len(prod["produtos"]) >= 3
    saldo0 = wallet.saldo(uid)
    # compra fichas -> cria cobrança -> simula pagamento -> credita o bônus
    c = a.post("/api/loja/comprar", json={"produto": "fichas_20"}).get_json()
    assert c["ok"] and c["sandbox"] and c["simular_url"]
    e = a.post(c["simular_url"]).get_json()
    assert e["ok"] and e["tipo"] == "fichas"
    assert wallet.saldo(uid) == saldo0 + 2200
    # idempotente: simular de novo não credita outra vez
    assert a.post(c["simular_url"]).get_json().get("ja_paga") is True
    assert wallet.saldo(uid) == saldo0 + 2200
    # assinatura ativa após pagar
    assert pagamentos.assinatura_estado(uid)["ativa"] is False
    ca = a.post("/api/loja/comprar", json={"produto": "premium_mes"}).get_json()
    a.post(ca["simular_url"])
    assert pagamentos.assinatura_estado(uid)["ativa"] is True
    # produto inválido e página da loja
    assert a.post("/api/loja/comprar", json={"produto": "xx"}).status_code == 400
    assert a.get("/loja").status_code == 200


# ---------------- tela inicial enxuta (menu) + páginas dedicadas ----------------
def test_lobby_menu_e_paginas_dedicadas():
    reset()
    a = cliente(); registrar(a, "Ana", "ana@ex.com")
    # a tela inicial agora é um menu que aponta para as páginas dedicadas
    r = a.get("/lobby")
    assert r.status_code == 200
    html = r.get_data(as_text=True)
    for destino in ("/mesas", "/torneios", "/amigos", "/avisos"):
        assert destino in html, destino
    # cada página dedicada abre
    for url in ("/mesas", "/amigos", "/avisos"):
        assert a.get(url).status_code == 200, url
    # criar mesa continua funcionando a partir da página de Mesas
    mid = a.post("/api/mesa/criar", json={"modo": "cash", "bots": 1}).get_json()["mesa_id"]
    assert mid in GM.mesas
    assert "Entrar na mesa" in a.get("/mesas").get_data(as_text=True) or \
           "Voltar para a mesa" in a.get("/mesas").get_data(as_text=True)
    # sem login, redireciona
    assert cliente().get("/mesas").status_code in (301, 302)


# ---------------- configurações (central + páginas) ----------------
def test_configuracoes_paginas():
    reset()
    a = cliente(); registrar(a, "Ana", "ana@ex.com")
    for url in ("/configuracoes", "/configuracoes/acessibilidade",
                "/configuracoes/jogo-responsavel", "/configuracoes/ajuda",
                "/configuracoes/privacidade", "/configuracoes/termos",
                "/configuracoes/seguranca"):
        assert a.get(url).status_code == 200, url
    # seção inexistente volta para a central (redireciona)
    assert a.get("/configuracoes/inexistente").status_code in (301, 302)
    # sem login, a central manda para o login
    assert cliente().get("/configuracoes").status_code in (301, 302)


# ---------------- jogo responsável ----------------
def test_jogo_responsavel_limite_e_pausa():
    reset()
    a = cliente(); registrar(a, "Ana", "ana@ex.com")
    # limite de tempo salva e volta no estado
    assert a.post("/api/jogo-responsavel/limite", json={"minutos": 30}).get_json()["limite_min"] == 30
    est = a.get("/api/jogo-responsavel/estado").get_json()
    assert est["ok"] and est["limite_min"] == 30 and est["bloqueado"] is False
    # sem pausa, consigo sentar numa mesa
    mid = a.post("/api/mesa/criar", json={"modo": "cash", "bots": 1}).get_json()["mesa_id"]
    assert a.post(f"/api/mesa/{mid}/sentar", json={"buy_in": 50}).get_json()["ok"] is True
    # ativa uma pausa -> entrar em mesa passa a ser bloqueado (403)
    rp = a.post("/api/jogo-responsavel/pausa", json={"horas": 1}).get_json()
    assert rp["ok"] and rp["bloqueado"] is True and rp["quando_libera"]
    mid2 = a.post("/api/mesa/criar", json={"modo": "cash", "bots": 1}).get_json()["mesa_id"]
    r = a.post(f"/api/mesa/{mid2}/sentar", json={"buy_in": 50})
    assert r.status_code == 403 and r.get_json()["ok"] is False
    # e inscrição em torneio também é bloqueada
    tid = a.post("/api/torneio/criar", json={"nome": "T", "num_participantes": 6,
                                             "stack_inicial": 5000, "buy_in": 0}).get_json()["torneio_id"]
    assert a.post(f"/api/torneio/{tid}/inscrever").status_code == 403


def test_jogo_responsavel_pausa_so_estende():
    reset()
    from server import responsavel
    a = cliente(); registrar(a, "Ana", "ana@ex.com")
    # descobre o id do usuário (1º registrado)
    conn = db.conexao()
    uid = conn.execute("SELECT id FROM usuarios WHERE apelido='Ana'").fetchone()["id"]
    a.post("/api/jogo-responsavel/pausa", json={"horas": 48})
    ate1 = responsavel.bloqueio_ate(uid)
    # pedir uma pausa MENOR não encurta o prazo já ativo
    a.post("/api/jogo-responsavel/pausa", json={"horas": 1})
    assert responsavel.bloqueio_ate(uid) == ate1


# ---------------- cash: sair da mesa devolve fichas + lista de espera ----------------
def test_levantar_devolve_fichas():
    reset()
    a = cliente(); registrar(a, "Ana", "ana@ex.com")
    conn = db.conexao()
    uid = conn.execute("SELECT id FROM usuarios WHERE apelido='Ana'").fetchone()["id"]
    from server import wallet
    saldo0 = wallet.saldo(uid)
    mid = a.post("/api/mesa/criar", json={"modo": "cash", "bots": 0}).get_json()["mesa_id"]
    a.post(f"/api/mesa/{mid}/sentar", json={"buy_in": 3})   # R$3,00 = 300 centavos
    assert wallet.saldo(uid) == saldo0 - 300
    # sem mão em andamento (só Ana): sai na hora e as fichas voltam
    r = a.post(f"/api/mesa/{mid}/levantar").get_json()
    assert r["ok"] and r["deferido"] is False
    assert wallet.saldo(uid) == saldo0
    assert all(x is None or x.jogador_id != "Ana" for x in GM.mesas[mid].assentos)


def test_levantar_devolve_stack_atual_nao_inicial():
    reset()
    from server import wallet
    a = cliente(); registrar(a, "Ana", "ana@ex.com")
    conn = db.conexao()
    uid = conn.execute("SELECT id FROM usuarios WHERE apelido='Ana'").fetchone()["id"]
    mid = a.post("/api/mesa/criar", json={"modo": "cash", "bots": 0}).get_json()["mesa_id"]
    a.post(f"/api/mesa/{mid}/sentar", json={"buy_in": 3})   # entra com 300 fichas
    saldo_sentado = wallet.saldo(uid)
    # simula que a Ana GANHOU fichas durante o jogo: stack sobe para 1275
    ana = next(x for x in GM.mesas[mid].assentos if x and x.jogador_id == "Ana")
    ana.stack = 1275
    a.post(f"/api/mesa/{mid}/levantar")
    # volta o STACK ATUAL (1275), não os 300 da entrada
    assert wallet.saldo(uid) == saldo_sentado + 1275


def test_fila_de_espera_notifica_ao_abrir_vaga():
    reset()
    a = cliente(); registrar(a, "Ana", "ana@ex.com")
    b = cliente(); registrar(b, "Bruno", "bruno@ex.com")
    # mesa cheia: 5 bots + Ana = 6
    mid = a.post("/api/mesa/criar", json={"modo": "cash", "bots": 5}).get_json()["mesa_id"]
    a.post(f"/api/mesa/{mid}/sentar", json={"buy_in": 3})
    assert len(GM.mesas[mid].jogadores_sentados()) == 6
    # Bruno não consegue sentar (cheia), então entra na fila
    fj = b.post(f"/api/mesa/{mid}/fila/entrar").get_json()
    assert fj["ok"] and fj["posicao"] == 1
    # Ana sai -> abre vaga -> Bruno é avisado
    a.post(f"/api/mesa/{mid}/levantar")
    notifs = b.get("/api/notificacoes").get_json()["notificacoes"]
    assert any(n["tipo"] == "vaga_mesa" and n["dados"]["mesa_id"] == mid for n in notifs)
    # e a fila esvazia (Bruno foi chamado)
    assert GM.filas_espera.get(mid) == []


def test_fila_sentar_remove_da_fila():
    reset()
    a = cliente(); registrar(a, "Ana", "ana@ex.com")
    mid = a.post("/api/mesa/criar", json={"modo": "cash", "bots": 0}).get_json()["mesa_id"]
    a.post(f"/api/mesa/{mid}/fila/entrar")
    assert GM.filas_espera.get(mid) and len(GM.filas_espera[mid]) == 1
    a.post(f"/api/mesa/{mid}/sentar", json={"buy_in": 3})   # ao sentar, sai da fila
    assert GM.filas_espera.get(mid) == []


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
