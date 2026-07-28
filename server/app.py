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
        self.lock = threading.RLock()
        self._ticker_ligado = False

    def criar(self, nome, modo="cash", max_jogadores=6, com_bots=0,
              tempo_acao=30) -> Mesa:
        cfg = MODOS.get(modo, MODOS["cash"])
        mid = uuid.uuid4().hex[:8]
        torneio = cfg.get("torneio", False)
        mesa = Mesa(mid, nome, modo=modo, sb=cfg["sb"], bb=cfg["bb"],
                    max_jogadores=max_jogadores, stack_inicial=cfg["stack_inicial"],
                    on_evento=self._broadcast, torneio=torneio,
                    duracao_nivel=cfg.get("duracao_nivel", 120),
                    buy_in=cfg.get("buy_in", 0) if torneio else 0,
                    tempo_acao=tempo_acao,
                    on_premiar=self._premiar(mid))
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
                for mesa in list(self.mesas.values()):
                    try:
                        if mesa.tick():
                            self.enviar_estado(mesa)
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
    return render_template("mesa.html", usuario=u, mesa_id=mesa_id, mesa_nome=mesa.nome)


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
        return jsonify({"ok": True, "saldo": novo, "saldo_fmt": wallet.formatar_reais(novo)})
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
        return jsonify({"ok": True, "saldo": novo, "saldo_fmt": wallet.formatar_reais(novo)})
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
    mesa = GM.criar(nome, modo=modo, com_bots=com_bots, tempo_acao=tempo_acao)
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
