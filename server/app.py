"""Aplicação web Flask: autenticação, carteira, lobby, mesas e WebSocket.

Rodar:  python -m server.app   (a partir da pasta poker-acessivel)
Depois abra http://localhost:5000
"""
from __future__ import annotations

import json
import os
import threading
import time
import uuid

from flask import (Flask, g, jsonify, redirect, render_template, request,
                   session, url_for)
from flask_sock import Sock

from . import auth, db, mailer, wallet
from .mesa import MODOS, Mesa
from .mtt import Torneio

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
app = Flask(
    __name__,
    template_folder=os.path.join(BASE, "web", "templates"),
    static_folder=os.path.join(BASE, "web", "static"),
)
app.secret_key = os.environ.get("POKER_SECRET", "dev-troque-em-producao-" + uuid.uuid4().hex)
sock = Sock(app)


# ==================== gerenciador de mesas ====================
class GerenciadorMesas:
    def __init__(self):
        self.mesas: dict[str, Mesa] = {}
        self.assinantes: dict[str, list] = {}   # mesa_id -> [ws,...]
        self.torneios: dict[str, Torneio] = {}  # torneios MTT
        self.lock = threading.RLock()
        self._ticker_ligado = False

    # ---------- torneios multi-mesa (MTT) ----------
    def criar_torneio(self, nome, num_participantes, stack_inicial, buy_in,
                      jogadores_por_mesa, tempo_acao, duracao_nivel,
                      rebuy_permitido, rebuy_ate_nivel,
                      addon_permitido, addon_valor, addon_fichas) -> Torneio:
        tid = uuid.uuid4().hex[:8]

        def criar_mesa(nome_mesa, maxj):
            mid = uuid.uuid4().hex[:8]
            m = Mesa(mid, nome_mesa, modo="torneio", max_jogadores=maxj,
                     stack_inicial=stack_inicial, on_evento=self._broadcast,
                     torneio=False, auto_iniciar=True, fechar_ao_terminar=False,
                     tempo_acao=tempo_acao)
            m.torneio_id = tid
            self.mesas[mid] = m
            self.assinantes[mid] = []
            return m

        def remover_mesa(mid):
            self.mesas.pop(mid, None)
            self.assinantes.pop(mid, None)

        def on_creditar(usuario_id, valor, colocacao):
            try:
                wallet.creditar_premio(usuario_id, valor, tid, colocacao)
            except Exception:
                pass

        def on_debitar(usuario_id, valor, desc):
            try:
                wallet._lancar(usuario_id, "buy_in", -valor, desc, ref=tid)
            except Exception:
                pass

        t = Torneio(tid, nome, num_participantes, stack_inicial, buy_in,
                    jogadores_por_mesa=jogadores_por_mesa, tempo_acao=tempo_acao,
                    duracao_nivel=duracao_nivel, rebuy_permitido=rebuy_permitido,
                    rebuy_ate_nivel=rebuy_ate_nivel, addon_permitido=addon_permitido,
                    addon_valor=addon_valor, addon_fichas=addon_fichas,
                    criar_mesa=criar_mesa, remover_mesa=remover_mesa,
                    on_creditar=on_creditar, on_debitar=on_debitar)
        self.torneios[tid] = t
        return t

    def criar(self, nome, modo="cash", max_jogadores=6, com_bots=0,
              tempo_acao=30, sb=None, bb=None, duracao_nivel=None,
              auto_iniciar=False, fechar_ao_terminar=True, big_blind_ante=False) -> Mesa:
        cfg = MODOS.get(modo, MODOS["cash"])
        mid = uuid.uuid4().hex[:8]
        torneio = cfg.get("torneio", False)
        mesa = Mesa(mid, nome, modo=modo,
                    sb=(sb if sb else cfg["sb"]), bb=(bb if bb else cfg["bb"]),
                    max_jogadores=max_jogadores, stack_inicial=cfg["stack_inicial"],
                    on_evento=self._broadcast, torneio=torneio,
                    duracao_nivel=(duracao_nivel if duracao_nivel else cfg.get("duracao_nivel", 120)),
                    buy_in=cfg.get("buy_in", 0) if torneio else 0,
                    tempo_acao=tempo_acao, on_premiar=self._premiar(mid),
                    auto_iniciar=auto_iniciar, fechar_ao_terminar=fechar_ao_terminar,
                    big_blind_ante=big_blind_ante)
        if com_bots:
            mesa.preencher_com_bots(com_bots)
        self.mesas[mid] = mesa
        self.assinantes[mid] = []
        return mesa

    def _premiar(self, mesa_id):
        def cb(assento, valor, colocacao):
            # credita prêmio de torneio na carteira do humano (modo simulado)
            if assento.usuario_id and valor > 0:
                try:
                    wallet.creditar_premio(assento.usuario_id, valor, mesa_id, colocacao)
                except Exception:
                    pass
        return cb

    def iniciar_ticker(self):
        """Thread que verifica timeouts de ação (auto-fold) a cada segundo."""
        if self._ticker_ligado:
            return
        self._ticker_ligado = True

        def loop():
            while True:
                time.sleep(1)
                # torneios MTT: avança blinds, elimina, rebuy/addon, rebalanceia
                for tid, t in list(self.torneios.items()):
                    try:
                        if t.tick():
                            for m in list(t.mesas.values()):
                                self.enviar_estado(m)
                    except Exception:
                        pass
                # mesas
                for mid, mesa in list(self.mesas.items()):
                    try:
                        if mesa.tick():
                            self.enviar_estado(mesa)
                        if getattr(mesa, "torneio_id", None):
                            continue  # mesas de torneio são gerenciadas pelo Torneio
                        # remove a mesa: torneio encerrado (fechar) OU abandonada
                        abandonada = (mesa.teve_humano and len(mesa.humanos()) == 0
                                      and len(self.assinantes.get(mid, [])) == 0)
                        if getattr(mesa, "remover", False) or abandonada:
                            self.mesas.pop(mid, None)
                            self.assinantes.pop(mid, None)
                    except Exception:
                        pass

        t = threading.Thread(target=loop, daemon=True)
        t.start()

    def _broadcast(self, mesa, evt):
        mortos = []
        for ws in list(self.assinantes.get(mesa.id, [])):
            try:
                ws.send(json.dumps({"tipo": "evento", "dados": evt}))
            except Exception:
                mortos.append(ws)
        for ws in mortos:
            try:
                self.assinantes[mesa.id].remove(ws)
            except ValueError:
                pass

    def enviar_estado(self, mesa, jogador_id=None):
        """Envia snapshot completo a todos (cada um vê suas próprias cartas)."""
        for ws in list(self.assinantes.get(mesa.id, [])):
            pov = getattr(ws, "_jogador_id", None)
            try:
                ws.send(json.dumps({"tipo": "estado", "dados": mesa.estado(pov)}))
            except Exception:
                pass


GM = GerenciadorMesas()


# ==================== helpers ====================
def usuario_atual():
    return auth.usuario_da_sessao(session.get("token", ""))


def requer_login():
    u = usuario_atual()
    if not u:
        return None
    g.usuario = u
    return u


# ==================== páginas ====================
@app.route("/")
def index():
    return redirect(url_for("lobby") if usuario_atual() else url_for("pagina_login"))


@app.route("/entrar")
def pagina_login():
    if usuario_atual():
        return redirect(url_for("lobby"))
    # Não exige convite do primeiro usuário (que vira administrador).
    exige = auth.exigir_convite() and auth.existe_algum_usuario()
    return render_template("login.html", exige_convite=exige)


@app.route("/verificar")
def pagina_verificar():
    if usuario_atual():
        return redirect(url_for("lobby"))
    return render_template("verificar.html", email=request.args.get("email", ""))


@app.route("/lobby")
def lobby():
    u = requer_login()
    if not u:
        return redirect(url_for("pagina_login"))
    mesas_pub = [
        {"id": m.id, "nome": m.nome, "modo": MODOS[m.modo]["nome"],
         "jogadores": len(m.jogadores_sentados()), "max": m.max_jogadores,
         "bb": m.bb}
        for m in GM.mesas.values()
    ]
    return render_template("lobby.html", usuario=u,
                           saldo=wallet.formatar_reais(wallet.saldo(u["id"])),
                           mesas=mesas_pub, modos=MODOS,
                           eh_admin=auth.is_admin(u["id"]))


@app.route("/mesa/<mesa_id>")
def pagina_mesa(mesa_id):
    u = requer_login()
    if not u:
        return redirect(url_for("pagina_login"))
    mesa = GM.mesas.get(mesa_id)
    if not mesa:
        return redirect(url_for("lobby"))
    tid = getattr(mesa, "torneio_id", None)
    return render_template("mesa.html", usuario=u, mesa_id=mesa_id, mesa_nome=mesa.nome,
                           torneio_id=tid)


@app.route("/torneios")
def pagina_torneios():
    u = requer_login()
    if not u:
        return redirect(url_for("pagina_login"))
    lista = [t.resumo() for t in GM.torneios.values() if t.estado != "encerrado"]
    return render_template("torneios.html", usuario=u, torneios=lista,
                           eh_admin=auth.is_admin(u["id"]))


@app.route("/torneio/<tid>")
def pagina_torneio(tid):
    u = requer_login()
    if not u:
        return redirect(url_for("pagina_login"))
    t = GM.torneios.get(tid)
    if not t:
        return redirect(url_for("pagina_torneios"))
    return render_template("torneio.html", usuario=u, torneio_id=tid,
                           torneio_nome=t.nome, eh_admin=auth.is_admin(u["id"]))


@app.route("/carteira")
def pagina_carteira():
    u = requer_login()
    if not u:
        return redirect(url_for("pagina_login"))
    return render_template("carteira.html", usuario=u,
                           saldo=wallet.formatar_reais(wallet.saldo(u["id"])),
                           extrato=wallet.extrato(u["id"]))


# ==================== admin (beta fechado) ====================
def requer_admin():
    u = usuario_atual()
    if not u or not auth.is_admin(u["id"]):
        return None
    return u


@app.route("/admin")
def pagina_admin():
    u = requer_admin()
    if not u:
        return redirect(url_for("lobby") if usuario_atual() else url_for("pagina_login"))
    usuarios = auth.listar_usuarios()
    for us in usuarios:
        us["saldo_fmt"] = wallet.formatar_reais(us["saldo"])
    return render_template("admin.html", usuario=u, usuarios=usuarios,
                           convites=auth.listar_convites(),
                           exige_convite=auth.exigir_convite())


@app.route("/admin/testar-email")
def admin_testar_email():
    u = requer_admin()
    if not u:
        return redirect(url_for("lobby") if usuario_atual() else url_for("pagina_login"))
    diag = mailer.diagnostico()
    ok, detalhe = mailer.testar_envio(u["email"])
    linhas = [
        "RESULTADO DO ENVIO: " + ("SUCESSO. " + detalhe if ok else "ERRO. " + detalhe),
        "",
        "Configuração atual:",
        f"SMTP_HOST: {diag['host']}",
        f"SMTP_PORT: {diag['port']}",
        f"SMTP_USER: {diag['user']}",
        f"SMTP_FROM: {diag['from']}",
        f"Senha definida: {'sim' if diag['senha_definida'] else 'NÃO'}",
        f"Tamanho da senha: {diag['senha_tamanho']} (o correto do Gmail é 16)",
        f"Senha tem espaço: {'SIM (precisa remover)' if diag['senha_tem_espaco'] else 'não'}",
    ]
    corpo = "<br>".join(l or "&nbsp;" for l in linhas)
    return (f"<!doctype html><html lang=pt-BR><meta charset=utf-8>"
            f"<title>Teste de e-mail</title><body style='font-family:sans-serif;padding:20px'>"
            f"<h1>Teste de e-mail</h1><p aria-live=polite>{corpo}</p>"
            f"<p><a href='/admin'>Voltar para a administração</a></p></body></html>")


@app.post("/api/admin/convites")
def api_gerar_convites():
    u = requer_admin()
    if not u:
        return jsonify({"ok": False, "erro": "acesso negado"}), 403
    d = request.get_json(force=True)
    codigos = auth.gerar_convites(int(d.get("quantidade", 5)), u["id"])
    return jsonify({"ok": True, "codigos": codigos})


@app.post("/api/admin/excluir-usuario")
def api_excluir_usuario():
    u = requer_admin()
    if not u:
        return jsonify({"ok": False, "erro": "acesso negado"}), 403
    d = request.get_json(force=True)
    try:
        uid = int(d.get("id", 0))
    except (TypeError, ValueError):
        return jsonify({"ok": False, "erro": "id inválido"}), 400
    if uid == u["id"]:
        return jsonify({"ok": False, "erro": "você não pode excluir a sua própria conta"}), 400
    auth.excluir_usuario(uid)
    return jsonify({"ok": True})


# ==================== API auth ====================
def _ativar_conta(uid: int, email: str, apelido: str) -> None:
    """Dá o bônus de boas-vindas, envia o e-mail de boas-vindas e loga o usuário."""
    wallet.depositar(uid, 100000, "Bônus de boas-vindas (simulado)")  # R$1000 grátis
    mailer.enviar_boas_vindas(email, apelido, wallet.formatar_reais(100000), request.host_url)
    session["token"] = auth.criar_sessao(uid)


@app.post("/api/registrar")
def api_registrar():
    d = request.get_json(force=True)
    try:
        u = auth.registrar(d.get("email", ""), d.get("apelido", ""), d.get("senha", ""),
                           d.get("convite", ""), verificacao_ativa=mailer.configurado())
        if not u["verificado"]:
            # conta pendente: envia o código e pede verificação (ainda NÃO loga)
            mailer.enviar_codigo_verificacao(u["email"], u["apelido"], u["codigo"])
            return jsonify({"ok": True, "precisa_verificar": True, "email": u["email"]})
        _ativar_conta(u["id"], u["email"], u["apelido"])
        return jsonify({"ok": True, "usuario": {"id": u["id"], "email": u["email"],
                                                "apelido": u["apelido"], "admin": u["admin"]}})
    except auth.ErroAuth as e:
        return jsonify({"ok": False, "erro": str(e)}), 400


@app.post("/api/verificar")
def api_verificar():
    d = request.get_json(force=True)
    try:
        r = auth.verificar_codigo(d.get("email", ""), d.get("codigo", ""))
        if r.get("ja_verificado"):
            session["token"] = auth.criar_sessao(r["id"])  # já ativa: só loga
        else:
            _ativar_conta(r["id"], r["email"], r["apelido"])
        return jsonify({"ok": True})
    except auth.ErroAuth as e:
        return jsonify({"ok": False, "erro": str(e)}), 400


@app.post("/api/reenviar")
def api_reenviar():
    d = request.get_json(force=True)
    email = d.get("email", "")
    codigo = auth.reenviar_codigo(email)
    if codigo:
        mailer.enviar_codigo_verificacao(email, "jogador", codigo)
    # sempre responde ok (não revela se o e-mail existe)
    return jsonify({"ok": True})


@app.post("/api/login")
def api_login():
    d = request.get_json(force=True)
    try:
        u = auth.autenticar(d.get("identificador", ""), d.get("senha", ""))
        session["token"] = auth.criar_sessao(u["id"])
        return jsonify({"ok": True, "usuario": u})
    except auth.ErroAuth as e:
        return jsonify({"ok": False, "erro": str(e)}), 400


@app.post("/api/logout")
def api_logout():
    auth.encerrar_sessao(session.get("token", ""))
    session.clear()
    return jsonify({"ok": True})


# ==================== API carteira ====================
@app.post("/api/carteira/depositar")
def api_depositar():
    u = usuario_atual()
    if not u:
        return jsonify({"ok": False, "erro": "não autenticado"}), 401
    d = request.get_json(force=True)
    try:
        centavos = int(round(float(d.get("valor", 0)) * 100))
        novo = wallet.depositar(u["id"], centavos)
        return jsonify({"ok": True, "saldo": novo, "saldo_fmt": wallet.formatar_reais(novo),
                        "valor_fmt": wallet.formatar_reais(centavos)})
    except (wallet.ErroCarteira, ValueError) as e:
        return jsonify({"ok": False, "erro": str(e)}), 400


@app.post("/api/carteira/sacar")
def api_sacar():
    u = usuario_atual()
    if not u:
        return jsonify({"ok": False, "erro": "não autenticado"}), 401
    d = request.get_json(force=True)
    try:
        centavos = int(round(float(d.get("valor", 0)) * 100))
        novo = wallet.sacar(u["id"], centavos)
        return jsonify({"ok": True, "saldo": novo, "saldo_fmt": wallet.formatar_reais(novo),
                        "valor_fmt": wallet.formatar_reais(centavos)})
    except (wallet.ErroCarteira, ValueError) as e:
        return jsonify({"ok": False, "erro": str(e)}), 400


# ==================== API mesas ====================
@app.post("/api/mesa/criar")
def api_criar_mesa():
    u = usuario_atual()
    if not u:
        return jsonify({"ok": False, "erro": "não autenticado"}), 401
    d = request.get_json(force=True)
    modo = d.get("modo", "cash")
    nome = (d.get("nome") or f"Mesa de {u['apelido']}").strip()[:40]
    com_bots = min(int(d.get("bots", 3)), 5)
    tempo_acao = max(0, min(int(d.get("tempo_acao", 30)), 120))

    def _pos_int(chave):
        try:
            v = int(d.get(chave, 0))
            return v if v > 0 else None
        except (TypeError, ValueError):
            return None

    sb = _pos_int("sb")
    bb = _pos_int("bb")
    if sb and bb and bb <= sb:      # a big precisa ser maior que a small
        bb = sb * 2
    mesa = GM.criar(nome, modo=modo, com_bots=com_bots, tempo_acao=tempo_acao,
                    sb=sb, bb=bb, duracao_nivel=_pos_int("duracao_nivel"),
                    auto_iniciar=bool(d.get("auto_iniciar", False)),
                    fechar_ao_terminar=bool(d.get("fechar_ao_terminar", True)),
                    big_blind_ante=bool(d.get("big_blind_ante", False)))
    return jsonify({"ok": True, "mesa_id": mesa.id})


@app.post("/api/mesa/<mesa_id>/sentar")
def api_sentar(mesa_id):
    u = usuario_atual()
    if not u:
        return jsonify({"ok": False, "erro": "não autenticado"}), 401
    mesa = GM.mesas.get(mesa_id)
    if not mesa:
        return jsonify({"ok": False, "erro": "mesa inexistente"}), 404
    d = request.get_json(force=True)
    try:
        # já sentado?
        if any(a and a.jogador_id == u["apelido"] for a in mesa.assentos):
            return jsonify({"ok": True, "ja_sentado": True})
        if mesa.torneio:
            if mesa.entrantes:  # torneio já começou
                return jsonify({"ok": False, "erro": "torneio já iniciado"}), 400
            custo = mesa.buy_in                    # buy-in fixo (centavos)
            fichas = mesa.stack_inicial            # fichas de torneio
        else:
            custo = int(round(float(d.get("buy_in", 50)) * 100))  # cash: fichas = dinheiro
            fichas = custo
        if wallet.saldo(u["id"]) < custo:
            return jsonify({"ok": False, "erro": "saldo insuficiente"}), 400
        wallet.debitar_buy_in(u["id"], custo, mesa_id)
        mesa.sentar(u["apelido"], u["apelido"], fichas, eh_bot=False, usuario_id=u["id"])
        return jsonify({"ok": True})
    except (wallet.ErroCarteira, ValueError) as e:
        return jsonify({"ok": False, "erro": str(e)}), 400


# ==================== API torneios (MTT) ====================
@app.post("/api/torneio/criar")
def api_criar_torneio():
    u = requer_admin()      # só admin cria torneios
    if not u:
        return jsonify({"ok": False, "erro": "acesso negado"}), 403
    d = request.get_json(force=True)

    def _int(chave, padrao):
        try:
            return int(d.get(chave, padrao))
        except (TypeError, ValueError):
            return padrao
    nome = (d.get("nome") or "Torneio").strip()[:40]
    t = GM.criar_torneio(
        nome, num_participantes=max(2, min(_int("num_participantes", 18), 90)),
        stack_inicial=max(100, _int("stack_inicial", 1500)),
        buy_in=max(0, int(round(float(d.get("buy_in", 10)) * 100))),
        jogadores_por_mesa=9, tempo_acao=max(0, min(_int("tempo_acao", 20), 120)),
        duracao_nivel=max(30, _int("duracao_nivel", 180)),
        rebuy_permitido=bool(d.get("rebuy", False)), rebuy_ate_nivel=_int("rebuy_ate_nivel", 3),
        addon_permitido=bool(d.get("addon", False)),
        addon_valor=int(round(float(d.get("addon_valor", 5)) * 100)),
        addon_fichas=max(0, _int("addon_fichas", 1500)))
    return jsonify({"ok": True, "torneio_id": t.id})


@app.post("/api/torneio/<tid>/inscrever")
def api_inscrever_torneio(tid):
    u = usuario_atual()
    if not u:
        return jsonify({"ok": False, "erro": "não autenticado"}), 401
    t = GM.torneios.get(tid)
    if not t:
        return jsonify({"ok": False, "erro": "torneio inexistente"}), 404
    try:
        if not any(i["jogador_id"] == u["apelido"] for i in t.inscritos):
            if wallet.saldo(u["id"]) < t.buy_in:
                return jsonify({"ok": False, "erro": "saldo insuficiente para o buy-in"}), 400
            wallet.debitar_buy_in(u["id"], t.buy_in, tid)
            t.inscrever(u["apelido"], u["apelido"], usuario_id=u["id"])
        return jsonify({"ok": True})
    except (ValueError, wallet.ErroCarteira) as e:
        return jsonify({"ok": False, "erro": str(e)}), 400


@app.post("/api/torneio/<tid>/iniciar")
def api_iniciar_torneio(tid):
    u = requer_admin()
    if not u:
        return jsonify({"ok": False, "erro": "acesso negado"}), 403
    t = GM.torneios.get(tid)
    if not t:
        return jsonify({"ok": False, "erro": "torneio inexistente"}), 404
    t.iniciar()
    return jsonify({"ok": True})


@app.post("/api/torneio/<tid>/rebuy")
def api_rebuy(tid):
    u = usuario_atual()
    if not u:
        return jsonify({"ok": False, "erro": "não autenticado"}), 401
    t = GM.torneios.get(tid)
    if not t:
        return jsonify({"ok": False, "erro": "torneio inexistente"}), 404
    if wallet.saldo(u["id"]) < t.buy_in:
        return jsonify({"ok": False, "erro": "saldo insuficiente para o rebuy"}), 400
    ok = t.rebuy(u["apelido"])
    return jsonify({"ok": ok})


@app.post("/api/torneio/<tid>/addon")
def api_addon(tid):
    u = usuario_atual()
    if not u:
        return jsonify({"ok": False, "erro": "não autenticado"}), 401
    t = GM.torneios.get(tid)
    if not t:
        return jsonify({"ok": False, "erro": "torneio inexistente"}), 404
    if wallet.saldo(u["id"]) < t.addon_valor:
        return jsonify({"ok": False, "erro": "saldo insuficiente para o add-on"}), 400
    ok = t.addon(u["apelido"])
    return jsonify({"ok": ok})


@app.get("/api/torneio/<tid>/estado")
def api_estado_torneio(tid):
    u = usuario_atual()
    t = GM.torneios.get(tid)
    if not t:
        return jsonify({"ok": False, "erro": "torneio inexistente"}), 404
    r = t.resumo()
    r["ok"] = True
    r["inscrito"] = bool(u) and any(i["jogador_id"] == u["apelido"] for i in t.inscritos)
    # se já começou, indica a mesa do jogador (para redirecionar)
    r["minha_mesa"] = t.jogador_mesa.get(u["apelido"]) if u else None
    return jsonify(r)


# ==================== WebSocket ====================
@sock.route("/ws/mesa/<mesa_id>")
def ws_mesa(ws, mesa_id):
    u = usuario_atual()
    mesa = GM.mesas.get(mesa_id)
    if not u or not mesa:
        ws.close()
        return
    ws._jogador_id = u["apelido"]
    GM.assinantes.setdefault(mesa_id, []).append(ws)
    # envia estado inicial
    ws.send(json.dumps({"tipo": "estado", "dados": mesa.estado(u["apelido"])}))
    try:
        while True:
            raw = ws.receive()
            if raw is None:
                break
            msg = json.loads(raw)
            cmd = msg.get("cmd")
            if cmd == "iniciar":
                mesa.iniciar_mao()
                GM.enviar_estado(mesa)
            elif cmd == "acao":
                try:
                    mesa.acao_humano(u["apelido"], msg.get("acao"),
                                     msg.get("valor"))
                except ValueError as e:
                    ws.send(json.dumps({"tipo": "erro", "mensagem": str(e)}))
                GM.enviar_estado(mesa)
            elif cmd == "estado":
                ws.send(json.dumps({"tipo": "estado", "dados": mesa.estado(u["apelido"])}))
            elif cmd == "equidade":
                pct = mesa.equidade(u["apelido"])
                ws.send(json.dumps({"tipo": "equidade", "pct": pct}))
    finally:
        try:
            GM.assinantes[mesa_id].remove(ws)
        except (ValueError, KeyError):
            pass


def criar_app():
    db.inicializar()
    GM.iniciar_ticker()
    return app


if __name__ == "__main__":
    db.inicializar()
    GM.iniciar_ticker()
    porta = int(os.environ.get("PORT", 5000))
    print(f"Poker Acessível rodando em http://localhost:{porta}")
    app.run(host="0.0.0.0", port=porta, debug=False, threaded=True)
