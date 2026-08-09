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

from flask import Flask, g, jsonify, redirect, render_template, request, session, url_for
from flask_sock import Sock

from . import auth, db, historia, mailer, responsavel, social, wallet
from .mesa import MODOS, Mesa
from .mtt import Torneio

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
app = Flask(
    __name__,
    template_folder=os.path.join(BASE, "web", "templates"),
    static_folder=os.path.join(BASE, "web", "static"),
)
app.secret_key = os.environ.get("POKER_SECRET", "dev-troque-em-producao-" + uuid.uuid4().hex)

# Segurança do cookie de sessão:
# - não-permanente (sem Max-Age): o navegador APAGA o cookie ao fechar -> logout.
# - HttpOnly: o JavaScript da página não consegue ler o cookie (protege contra XSS).
# - SameSite=Lax: não vai em requisições de outros sites (protege contra CSRF).
# - Secure em produção (HTTPS no Render); local é HTTP, então fica desligado.
app.config.update(
    SESSION_PERMANENT=False,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=bool(os.environ.get("DATABASE_URL")),
)
sock = Sock(app)

# Versão dos arquivos estáticos: muda a cada início do servidor (ou seja, a cada
# deploy). Vira "?v=..." nos <script>/<link>, então o navegador SEMPRE baixa a versão
# nova depois de uma atualização (evita ficar com JS antigo em cache, que quebra o jogo).
VERSAO_ESTATICOS = str(int(time.time()))


@app.context_processor
def _injeta_versao_estaticos():
    return {"versao_est": VERSAO_ESTATICOS}


@app.after_request
def _sem_cache_no_html(resp):
    """As PÁGINAS (HTML) nunca são guardadas em cache: assim o navegador sempre
    pega a página nova, que por sua vez aponta para o JS/CSS com a versão certa
    (?v=...). Isso evita ficar com a mistura 'página nova + JavaScript velho'."""
    ctype = resp.headers.get("Content-Type", "")
    if ctype.startswith("text/html"):
        resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        resp.headers["Pragma"] = "no-cache"
        resp.headers["Expires"] = "0"
    return resp


# ==================== gerenciador de mesas ====================
class GerenciadorMesas:
    def __init__(self):
        self.mesas: dict[str, Mesa] = {}
        self.assinantes: dict[str, list] = {}   # mesa_id -> [ws,...]
        self.torneios: dict[str, Torneio] = {}  # torneios MTT
        self.filas_espera: dict[str, list] = {}  # mesa_id -> [{apelido, usuario_id}]
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
                     tempo_acao=tempo_acao, on_mao_gravada=historia.salvar_mao_registro)
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
                    big_blind_ante=big_blind_ante,
                    on_mao_gravada=historia.salvar_mao_registro,
                    on_saiu=self._ao_sair)
        if com_bots:
            mesa.preencher_com_bots(com_bots)
        self.mesas[mid] = mesa
        self.assinantes[mid] = []
        return mesa

    def _ao_sair(self, mesa_id=None, usuario_id=None, apelido=None, nome=None,
                 stack=0, torneio=False):
        """Chamado pela mesa quando um jogador sai: no cash, devolve as fichas à
        carteira (viram dinheiro); depois chama o próximo da fila de espera."""
        if not torneio and usuario_id and stack and stack > 0:
            try:
                wallet.creditar_cash_out(usuario_id, stack, mesa_id)
            except Exception:
                pass
        self._chamar_proximo_da_fila(mesa_id)
        mesa = self.mesas.get(mesa_id)
        if mesa:
            self.enviar_estado(mesa)

    def _chamar_proximo_da_fila(self, mesa_id):
        """Avisa o primeiro da fila de espera que abriu uma vaga na mesa."""
        fila = self.filas_espera.get(mesa_id) or []
        mesa = self.mesas.get(mesa_id)
        if not fila or not mesa:
            return
        if len(mesa.jogadores_sentados()) >= mesa.max_jogadores:
            return   # ainda está cheia (bots ou outros ocuparam)
        prox = fila.pop(0)
        try:
            social.notificar(prox["apelido"], "vaga_mesa",
                             f"Abriu uma vaga na mesa {mesa.nome}. Entre para jogar!",
                             {"mesa_id": mesa_id, "mesa_nome": mesa.nome})
        except Exception:
            pass

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

    def enviar_chat(self, mesa_id, de, texto, para=None):
        """Entrega uma mensagem de chat.

        Público (para=None): todos na mesa. Privado (PV): só o remetente e o
        destinatário. O destinatário pode ser apelido OU e-mail, e pode estar em
        OUTRA tela — nesse caso a PV chega como aviso (notificação).
        Retorna (ok, motivo)."""
        texto = (texto or "").strip()[:500]
        if not texto:
            return False, "mensagem vazia"
        subs = {getattr(ws, "_jogador_id", None)
                for ws in self.assinantes.get(mesa_id, [])}
        # quem bloqueou o remetente NÃO recebe as mensagens dele (o remetente não sabe)
        bloqueadores = social.apelidos_que_bloquearam(de)
        privado = bool(para)
        alvo = None
        if privado:
            alvo = social.resolver_apelido(para)     # aceita apelido ou e-mail
            if not alvo:
                return False, "não encontrei essa pessoa"
            if alvo == de:
                return False, "você não pode mandar PV para você mesmo"
            # destinatário fora da mesa mas online -> entrega como notificação
            if alvo not in subs:
                if alvo in social.usuarios_online():
                    if alvo not in bloqueadores:      # se te bloqueou, não recebe
                        social.notificar(alvo, "chat_pv",
                                         f"{de} te mandou no privado: {texto}", {"de": de})
                    # mostra a mensagem no painel do próprio remetente
                    self._chat_para_ws(mesa_id, {de}, de, texto, True, alvo, bloqueadores)
                    return True, "ok"
                return False, "essa pessoa não está online"
        # WS: público (todos) ou PV com o alvo na mesa (remetente + alvo)
        destinos = None if not privado else {de, alvo}
        entregue = self._chat_para_ws(mesa_id, destinos, de, texto, privado, alvo, bloqueadores)
        return entregue, "ok" if entregue else "ninguém recebeu"

    def _chat_para_ws(self, mesa_id, destinos, de, texto, privado, para, bloqueadores=None):
        payload = {"tipo": "chat", "de": de, "texto": texto,
                   "privado": privado, "para": para, "ts": time.time()}
        bloqueadores = bloqueadores or set()
        entregue = False
        for ws in list(self.assinantes.get(mesa_id, [])):
            jid = getattr(ws, "_jogador_id", None)
            if destinos is not None and jid not in destinos:
                continue
            if jid != de and jid in bloqueadores:   # bloqueou o remetente -> não entrega
                continue
            try:
                ws.send(json.dumps(payload))
                entregue = True
            except Exception:
                pass
        return entregue


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


# ==================== segurança (CSRF + rate limit) ====================
import urllib.parse as _urlparse  # noqa: E402


# Proteção CSRF: toda ação que MUDA estado (POST/PUT/DELETE/PATCH) precisa vir do
# próprio site. O navegador sempre manda o cabeçalho Origin numa requisição de outro
# site — se não bater com o nosso host, recusamos. Requisições sem Origin/Referer
# (ex.: curl, testes) não são vetor de CSRF, então passam.
def _hosts_aceitos() -> set[str]:
    """Hostnames que contam como 'o próprio site' (cobre o proxy do Render)."""
    aceitos = {request.host.split(":")[0]}
    xfh = request.headers.get("X-Forwarded-Host", "")
    for h in xfh.split(","):
        h = h.strip().split(":")[0]
        if h:
            aceitos.add(h)
    extra = os.environ.get("POKER_HOST", "").strip().split(":")[0]
    if extra:
        aceitos.add(extra)
    return aceitos


@app.before_request
def _protecao_csrf():
    if request.method in ("GET", "HEAD", "OPTIONS"):
        return
    origem = request.headers.get("Origin") or request.headers.get("Referer")
    if origem:
        host_origem = _urlparse.urlparse(origem).hostname
        if host_origem and host_origem not in _hosts_aceitos():
            return jsonify({"ok": False, "erro": "origem inválida (bloqueado por segurança)"}), 403


# Rate limit de login: trava tentativas repetidas de senha errada por IP (força bruta).
_login_falhas: dict[str, list] = {}
LOGIN_MAX_FALHAS = int(os.environ.get("POKER_LOGIN_MAX", "8"))
LOGIN_JANELA_SEG = int(os.environ.get("POKER_LOGIN_JANELA", "300"))  # 5 minutos


def _ip_cliente() -> str:
    xff = request.headers.get("X-Forwarded-For", "")
    return (xff.split(",")[0].strip() if xff else request.remote_addr) or "?"


def _login_bloqueado(ip: str) -> bool:
    agora = time.time()
    tent = [t for t in _login_falhas.get(ip, []) if agora - t < LOGIN_JANELA_SEG]
    _login_falhas[ip] = tent
    return len(tent) >= LOGIN_MAX_FALHAS


def _registrar_falha_login(ip: str) -> None:
    _login_falhas.setdefault(ip, []).append(time.time())


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
    # tela inicial enxuta: só o menu (Mesas/Torneios/Amigos/Avisos)
    return render_template("lobby.html", usuario=u,
                           eh_admin=auth.is_admin(u["id"]))


def _mesas_publicas(u):
    """Lista das mesas para a tela de Mesas (Restaurar / Entrar em andamento)."""
    return [
        {"id": m.id, "nome": m.nome, "modo": MODOS[m.modo]["nome"],
         "jogadores": len(m.jogadores_sentados()), "max": m.max_jogadores,
         "bb": m.bb,
         # "minha": eu ainda tenho assento nesta mesa (para 'Restaurar')
         "minha": any(a and a.jogador_id == u["apelido"] for a in m.assentos),
         # cash cheia -> oferece lista de espera em vez de "Entrar"
         "cash": not m.torneio,
         "cheia": len(m.jogadores_sentados()) >= m.max_jogadores,
         "fila": len(GM.filas_espera.get(m.id, []))}
        for m in GM.mesas.values()
    ]


@app.route("/mesas")
def pagina_mesas():
    u = requer_login()
    if not u:
        return redirect(url_for("pagina_login"))
    return render_template("mesas.html", usuario=u,
                           mesas=_mesas_publicas(u), modos=MODOS)


@app.route("/amigos")
def pagina_amigos():
    u = requer_login()
    if not u:
        return redirect(url_for("pagina_login"))
    return render_template("amigos.html", usuario=u)


@app.route("/avisos")
def pagina_avisos():
    u = requer_login()
    if not u:
        return redirect(url_for("pagina_login"))
    return render_template("avisos.html", usuario=u)


@app.route("/perfil")
def pagina_perfil():
    u = requer_login()
    if not u:
        return redirect(url_for("pagina_login"))
    return render_template("perfil.html", usuario=u,
                           saldo=wallet.formatar_reais(wallet.saldo(u["id"])))


@app.get("/api/perfil")
def api_perfil():
    u = usuario_atual()
    if not u:
        return jsonify({"ok": False}), 401
    return jsonify({"ok": True, "apelido": u["apelido"], "email": u["email"],
                    "stats": historia.stats_usuario(u["id"]),
                    "avisar_conexao": social.avisar_conexao_ligado(u["id"])})


# ==================== Configurações (central + páginas) ====================
# Conteúdo das páginas informativas (Ajuda, Privacidade, Termos, Segurança).
# Cada seção é um par (título, texto). Estrutura simples, fácil de ler no leitor de tela.
CONTEUDO_CONFIG = {
    "ajuda": ("Ajuda e suporte",
              "Perguntas frequentes, contato e orientação sobre o aplicativo.", [
        ("Como eu jogo pelo teclado?",
         "Na mesa, aperte F1 a qualquer momento para ouvir a lista completa de teclas. "
         "As principais: setas e Tab navegam; F desiste, C paga, R aumenta, P passa. A "
         "tecla X muda o quanto o jogo fala e a tecla Q abandona a partida."),
        ("O jogo não está falando as jogadas. O que faço?",
         "Verifique em Configurações, Acessibilidade se os anúncios e o volume estão "
         "ligados. No navegador, force a página nova com Ctrl e F5. Se usa NVDA, a mesa "
         "entra em 'modo aplicativo' sozinha para as teclas funcionarem."),
        ("Preciso de mais ajuda.",
         "Fale com o suporte pelo e-mail xandentro1@gmail.com. Descreva o que aconteceu "
         "e, se possível, qual navegador e leitor de tela você usa."),
    ]),
    "privacidade": ("Privacidade",
                    "Uso de dados pessoais, documentos, biometria e seus direitos.", [
        ("Quais dados guardamos",
         "Guardamos apenas o necessário para você jogar: apelido, e-mail e o histórico "
         "das suas mãos e fichas. As senhas ficam guardadas de forma cifrada (nunca em "
         "texto puro)."),
        ("Documentos e biometria",
         "Esta versão é um beta com fichas simuladas e NÃO coleta documentos nem "
         "biometria. Se um dia houver verificação de identidade, ela será opcional, "
         "explicada antes, e você poderá recusar."),
        ("Seus direitos",
         "Você pode pedir a qualquer momento para ver, corrigir ou apagar seus dados, "
         "escrevendo para xandentro1@gmail.com."),
    ]),
    "termos": ("Termos e contratos",
               "Termos de uso, regras das mesas, pagamentos e cancelamento.", [
        ("Uso do aplicativo",
         "Este é um beta fechado, para testes, com fichas SIMULADAS. Não há dinheiro "
         "real envolvido. Use com respeito aos outros jogadores."),
        ("Regras das mesas",
         "Vale o Texas Hold'em tradicional. Abandonar partidas no meio, usar linguagem "
         "abusiva ou tentar burlar o jogo pode levar a bloqueio da conta."),
        ("Pagamentos",
         "Depósitos e saques são simulados nesta fase. Nenhum valor real é cobrado ou "
         "pago."),
    ]),
    "seguranca": ("Segurança",
                  "Senha, sessões, dispositivos e autenticação em duas etapas.", [
        ("Sua senha",
         "Use uma senha forte (mínimo 8 caracteres, com letra maiúscula e número). "
         "Nunca compartilhe sua senha com ninguém — o suporte NUNCA vai pedir sua senha."),
        ("Sessões",
         "Sua sessão expira sozinha depois de um tempo sem uso, para proteger sua conta "
         "em computadores compartilhados. Você pode sair a qualquer momento pelo botão "
         "Sair, no topo do site."),
        ("Autenticação em duas etapas",
         "A verificação por código de e-mail já protege o primeiro acesso. A "
         "autenticação em duas etapas a cada login está planejada para uma próxima versão."),
    ]),
}


@app.route("/configuracoes")
def pagina_configuracoes():
    u = requer_login()
    if not u:
        return redirect(url_for("pagina_login"))
    return render_template("configuracoes.html", usuario=u)


@app.route("/configuracoes/acessibilidade")
def pagina_config_acessibilidade():
    u = requer_login()
    if not u:
        return redirect(url_for("pagina_login"))
    return render_template("config_acessibilidade.html", usuario=u)


@app.route("/configuracoes/jogo-responsavel")
def pagina_config_jogo_responsavel():
    u = requer_login()
    if not u:
        return redirect(url_for("pagina_login"))
    return render_template("config_jogo_responsavel.html", usuario=u)


@app.route("/configuracoes/<secao>")
def pagina_config_conteudo(secao):
    u = requer_login()
    if not u:
        return redirect(url_for("pagina_login"))
    dados = CONTEUDO_CONFIG.get(secao)
    if not dados:
        return redirect(url_for("pagina_configuracoes"))
    titulo, intro, secoes = dados
    return render_template("config_conteudo.html", usuario=u,
                           titulo=titulo, intro=intro, secoes=secoes)


# ---- API do Jogo Responsável ----
@app.get("/api/jogo-responsavel/estado")
def api_jr_estado():
    u = usuario_atual()
    if not u:
        return jsonify({"ok": False}), 401
    est = responsavel.estado(u["id"], session.get("login_ts"))
    return jsonify({"ok": True, **est})


@app.post("/api/jogo-responsavel/limite")
def api_jr_limite():
    u = usuario_atual()
    if not u:
        return jsonify({"ok": False}), 401
    d = request.get_json(force=True, silent=True) or {}
    m = responsavel.set_limite_min(u["id"], d.get("minutos", 0))
    return jsonify({"ok": True, "limite_min": m})


@app.post("/api/jogo-responsavel/pausa")
def api_jr_pausa():
    u = usuario_atual()
    if not u:
        return jsonify({"ok": False}), 401
    d = request.get_json(force=True, silent=True) or {}
    horas = d.get("horas", 0)
    responsavel.bloquear_por(u["id"], horas)
    return jsonify({"ok": True, "bloqueado": responsavel.bloqueado(u["id"]),
                    "quando_libera": responsavel.quando_libera(u["id"])})


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
    corpo = "<br>".join(linha or "&nbsp;" for linha in linhas)
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
    ip = _ip_cliente()
    if _login_bloqueado(ip):
        return jsonify({"ok": False, "erro": "Muitas tentativas de login. "
                        "Espere alguns minutos e tente de novo."}), 429
    d = request.get_json(force=True)
    try:
        u = auth.autenticar(d.get("identificador", ""), d.get("senha", ""))
        _login_falhas.pop(ip, None)   # sucesso: zera o contador
        session["token"] = auth.criar_sessao(u["id"])
        session["login_ts"] = int(time.time())   # p/ lembrete de tempo de jogo
        return jsonify({"ok": True, "usuario": u})
    except auth.ErroAuth as e:
        _registrar_falha_login(ip)    # senha errada / conta não verificada: conta a falha
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
    if responsavel.bloqueado(u["id"]):
        return jsonify({"ok": False, "erro": "Você ativou uma pausa no Jogo Responsável. "
                        "Poderá jogar de novo em " + responsavel.quando_libera(u["id"]) + "."}), 403
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
        if custo > 0:      # mesa grátis (buy-in 0) não cobra nem debita
            if wallet.saldo(u["id"]) < custo:
                return jsonify({"ok": False, "erro": "saldo insuficiente"}), 400
            wallet.debitar_buy_in(u["id"], custo, mesa_id)
        avatar = social.get_pref(u["id"], "avatar", "")
        mesa.sentar(u["apelido"], u["apelido"], fichas, eh_bot=False,
                    usuario_id=u["id"], avatar=avatar)
        GM.enviar_estado(mesa)   # avisa os outros da mesa (atualiza lista de PV, presença)
        # ao sentar, sai da fila de espera desta mesa (se estava esperando)
        fila = GM.filas_espera.get(mesa_id)
        if fila:
            GM.filas_espera[mesa_id] = [x for x in fila if x["apelido"] != u["apelido"]]
        return jsonify({"ok": True})
    except (wallet.ErroCarteira, ValueError) as e:
        return jsonify({"ok": False, "erro": str(e)}), 400


@app.post("/api/mesa/<mesa_id>/levantar")
def api_levantar(mesa_id):
    """Sai da mesa de verdade: libera o assento e, no cash, devolve as fichas à
    carteira. Se estava só na fila de espera, sai da fila."""
    u = usuario_atual()
    if not u:
        return jsonify({"ok": False, "erro": "não autenticado"}), 401
    mesa = GM.mesas.get(mesa_id)
    # tira da fila de espera (se estava esperando)
    fila = GM.filas_espera.get(mesa_id)
    if fila:
        GM.filas_espera[mesa_id] = [x for x in fila if x["apelido"] != u["apelido"]]
    if not mesa:
        return jsonify({"ok": True, "sentado": False})
    r = mesa.marcar_para_sair(u["apelido"])
    if not r.get("ok"):
        return jsonify({"ok": True, "sentado": False})   # não estava sentado, tudo bem
    GM.enviar_estado(mesa)
    return jsonify(r)


@app.post("/api/mesa/<mesa_id>/fila/entrar")
def api_fila_entrar(mesa_id):
    u = usuario_atual()
    if not u:
        return jsonify({"ok": False, "erro": "não autenticado"}), 401
    if responsavel.bloqueado(u["id"]):
        return jsonify({"ok": False, "erro": "Você ativou uma pausa no Jogo Responsável. "
                        "Poderá jogar de novo em " + responsavel.quando_libera(u["id"]) + "."}), 403
    mesa = GM.mesas.get(mesa_id)
    if not mesa:
        return jsonify({"ok": False, "erro": "mesa inexistente"}), 404
    if any(a and a.jogador_id == u["apelido"] for a in mesa.assentos):
        return jsonify({"ok": False, "erro": "você já está sentado nesta mesa"}), 400
    fila = GM.filas_espera.setdefault(mesa_id, [])
    if not any(x["apelido"] == u["apelido"] for x in fila):
        fila.append({"apelido": u["apelido"], "usuario_id": u["id"]})
    pos = next((i + 1 for i, x in enumerate(fila) if x["apelido"] == u["apelido"]), len(fila))
    return jsonify({"ok": True, "posicao": pos, "tamanho": len(fila)})


@app.post("/api/mesa/<mesa_id>/fila/sair")
def api_fila_sair(mesa_id):
    u = usuario_atual()
    if not u:
        return jsonify({"ok": False}), 401
    fila = GM.filas_espera.get(mesa_id) or []
    GM.filas_espera[mesa_id] = [x for x in fila if x["apelido"] != u["apelido"]]
    return jsonify({"ok": True})


@app.get("/api/mesa/<mesa_id>/fila")
def api_fila_ver(mesa_id):
    u = usuario_atual()
    if not u:
        return jsonify({"ok": False}), 401
    fila = GM.filas_espera.get(mesa_id) or []
    pos = next((i + 1 for i, x in enumerate(fila) if x["apelido"] == u["apelido"]), 0)
    mesa = GM.mesas.get(mesa_id)
    cheia = bool(mesa and len(mesa.jogadores_sentados()) >= mesa.max_jogadores)
    return jsonify({"ok": True, "tamanho": len(fila), "minha_posicao": pos, "cheia": cheia})


def _relatorio_args():
    """Lê escopo e alvos do corpo JSON da requisição de relatório."""
    d = request.get_json(force=True, silent=True) or {}
    escopo = d.get("escopo", "proprio")
    if escopo not in ("proprio", "selecionados", "todos"):
        escopo = "proprio"
    alvos = d.get("alvos") or []
    if not isinstance(alvos, list):
        alvos = []
    return escopo, [str(x) for x in alvos]


@app.post("/api/mesa/<mesa_id>/relatorio")
def api_relatorio(mesa_id):
    """Devolve o relatório rodada-a-rodada em texto (para copiar/mostrar)."""
    u = usuario_atual()
    if not u:
        return jsonify({"ok": False, "erro": "não autenticado"}), 401
    mesa = GM.mesas.get(mesa_id)
    if not mesa:
        return jsonify({"ok": False, "erro": "mesa inexistente"}), 404
    escopo, alvos = _relatorio_args()
    texto = mesa.relatorio(u["apelido"], escopo=escopo, alvos=alvos)
    # nomes de humanos disponíveis (para o usuário escolher 'selecionados')
    return jsonify({"ok": True, "texto": texto,
                    "jogadores": mesa._humanos_conhecidos()})


@app.post("/api/mesa/<mesa_id>/relatorio/email")
def api_relatorio_email(mesa_id):
    """Envia o relatório por e-mail para o próprio usuário logado."""
    u = usuario_atual()
    if not u:
        return jsonify({"ok": False, "erro": "não autenticado"}), 401
    mesa = GM.mesas.get(mesa_id)
    if not mesa:
        return jsonify({"ok": False, "erro": "mesa inexistente"}), 404
    escopo, alvos = _relatorio_args()
    texto = mesa.relatorio(u["apelido"], escopo=escopo, alvos=alvos)
    ok, detalhe = mailer.enviar_relatorio(u["email"], u["apelido"], texto)
    return jsonify({"ok": ok, "detalhe": detalhe, "destino": u["email"]})


# ==================== amigos, notificações e convites ====================
@app.get("/api/amigos")
def api_amigos():
    u = usuario_atual()
    if not u:
        return jsonify({"ok": False, "erro": "não autenticado"}), 401
    return jsonify({"ok": True, "amigos": social.listar_amigos(u["id"])})


@app.get("/api/online")
def api_online():
    """Pessoas online (menos você), amigos primeiro e depois em ordem alfabética.
    Serve para 'adicionar amigo' e para escolher destinatário no bate-papo."""
    u = usuario_atual()
    if not u:
        return jsonify({"ok": False, "online": []}), 401
    social.marcar_online(u["apelido"])   # eu também conto como online
    return jsonify({"ok": True, "online": social.online_para(u["id"], u["apelido"])})


@app.post("/api/amigos/adicionar_varios")
def api_amigos_adicionar_varios():
    """Adiciona vários amigos de uma vez (lista de apelidos)."""
    u = usuario_atual()
    if not u:
        return jsonify({"ok": False, "erro": "não autenticado"}), 401
    d = request.get_json(force=True, silent=True) or {}
    apelidos = d.get("apelidos") or []
    add, erros = [], []
    for ap in apelidos:
        r = social.adicionar_amigo(u["id"], ap)
        (add if r.get("ok") else erros).append(r.get("amigo") or ap)
    return jsonify({"ok": True, "adicionados": add, "erros": erros})


@app.post("/api/amigos/adicionar")
def api_amigos_adicionar():
    u = usuario_atual()
    if not u:
        return jsonify({"ok": False, "erro": "não autenticado"}), 401
    d = request.get_json(force=True, silent=True) or {}
    r = social.adicionar_amigo(u["id"], d.get("apelido", ""))
    return jsonify(r), (200 if r.get("ok") else 400)


@app.post("/api/amigos/remover")
def api_amigos_remover():
    u = usuario_atual()
    if not u:
        return jsonify({"ok": False, "erro": "não autenticado"}), 401
    d = request.get_json(force=True, silent=True) or {}
    r = social.remover_amigo(u["id"], d.get("apelido", ""))
    return jsonify(r), (200 if r.get("ok") else 400)


# ---- moderação: bloquear / denunciar ----
@app.get("/api/bloqueados")
def api_bloqueados():
    u = usuario_atual()
    if not u:
        return jsonify({"ok": False, "bloqueados": []}), 401
    return jsonify({"ok": True, "bloqueados": social.listar_bloqueados(u["id"])})


@app.post("/api/bloquear")
def api_bloquear():
    u = usuario_atual()
    if not u:
        return jsonify({"ok": False, "erro": "não autenticado"}), 401
    d = request.get_json(force=True, silent=True) or {}
    r = social.bloquear(u["id"], d.get("apelido", ""))
    return jsonify(r), (200 if r.get("ok") else 400)


@app.post("/api/desbloquear")
def api_desbloquear():
    u = usuario_atual()
    if not u:
        return jsonify({"ok": False, "erro": "não autenticado"}), 401
    d = request.get_json(force=True, silent=True) or {}
    r = social.desbloquear(u["id"], d.get("apelido", ""))
    return jsonify(r), (200 if r.get("ok") else 400)


@app.post("/api/denunciar")
def api_denunciar():
    u = usuario_atual()
    if not u:
        return jsonify({"ok": False, "erro": "não autenticado"}), 401
    d = request.get_json(force=True, silent=True) or {}
    r = social.denunciar(u["id"], u["apelido"], d.get("apelido", ""), d.get("motivo", ""))
    return jsonify(r), (200 if r.get("ok") else 400)


@app.get("/api/denuncias")
def api_denuncias():
    u = requer_admin()      # só admin vê as denúncias
    if not u:
        return jsonify({"ok": False, "erro": "acesso negado"}), 403
    return jsonify({"ok": True, "denuncias": social.listar_denuncias()})


@app.post("/api/denuncias/<int:denuncia_id>/resolver")
def api_denuncia_resolver(denuncia_id):
    u = requer_admin()
    if not u:
        return jsonify({"ok": False, "erro": "acesso negado"}), 403
    return jsonify(social.resolver_denuncia(denuncia_id))


@app.get("/api/notificacoes")
def api_notificacoes():
    """Busca (e limpa) as notificações pendentes do usuário logado. O navegador
    chama isto por polling em todas as páginas — também serve de 'batida de
    presença' (heartbeat) para o alerta de conexão."""
    u = usuario_atual()
    if not u:
        return jsonify({"ok": False, "notificacoes": []}), 401
    # heartbeat de presença: se ACABOU de conectar, avisa os outros e recebe os avisos
    if social.marcar_online(u["apelido"]):
        social.notificar_conexao(u["apelido"])
        for av in social.avisos_para(u["id"]):
            social.notificar(u["apelido"], "aviso", av["texto"],
                             {"aviso_id": av["id"], "de": av.get("criado_nome")})
    return jsonify({"ok": True, "notificacoes": social.pegar_notificacoes(u["apelido"])})


# ---- preferência: alerta de conexão liga/desliga ----
@app.get("/api/preferencias/avisar_conexao")
def api_pref_avisar_get():
    u = usuario_atual()
    if not u:
        return jsonify({"ok": False}), 401
    return jsonify({"ok": True, "ligado": social.avisar_conexao_ligado(u["id"])})


@app.post("/api/preferencias/avisar_conexao")
def api_pref_avisar_set():
    u = usuario_atual()
    if not u:
        return jsonify({"ok": False}), 401
    d = request.get_json(force=True, silent=True) or {}
    social.set_pref(u["id"], "avisar_conexao", "1" if d.get("ligado") else "0")
    return jsonify({"ok": True, "ligado": bool(d.get("ligado"))})


# ---- preferência: boneco (avatar) escolhido pelo jogador ----
AVATARES_VALIDOS = {"m1", "m2", "m3", "f1", "f2", "f3"}


@app.get("/api/preferencias/avatar")
def api_pref_avatar_get():
    u = usuario_atual()
    if not u:
        return jsonify({"ok": False}), 401
    return jsonify({"ok": True, "avatar": social.get_pref(u["id"], "avatar", "")})


@app.post("/api/preferencias/avatar")
def api_pref_avatar_set():
    u = usuario_atual()
    if not u:
        return jsonify({"ok": False}), 401
    d = request.get_json(force=True, silent=True) or {}
    avatar = str(d.get("avatar", "")).strip()
    if avatar not in AVATARES_VALIDOS:
        return jsonify({"ok": False, "erro": "boneco inválido"}), 400
    social.set_pref(u["id"], "avatar", avatar)
    return jsonify({"ok": True, "avatar": avatar})


# ---- quadro de avisos ----
@app.get("/api/avisos")
def api_avisos():
    u = usuario_atual()
    if not u:
        return jsonify({"ok": False, "avisos": []}), 401
    return jsonify({"ok": True, "avisos": social.avisos_para(u["id"]),
                    "sou_admin": bool(u.get("admin"))})


@app.post("/api/avisos/criar")
def api_avisos_criar():
    u = requer_admin()      # só admin publica avisos da plataforma
    if not u:
        return jsonify({"ok": False, "erro": "acesso negado"}), 403
    d = request.get_json(force=True, silent=True) or {}
    r = social.criar_aviso(u["id"], u["apelido"], d.get("texto", ""))
    return jsonify(r), (200 if r.get("ok") else 400)


@app.post("/api/avisos/<int:aviso_id>/baixar")
def api_avisos_baixar(aviso_id):
    u = usuario_atual()
    if not u:
        return jsonify({"ok": False, "erro": "não autenticado"}), 401
    r = social.baixar_aviso(u["id"], aviso_id, bool(u.get("admin")))
    return jsonify(r), (200 if r.get("ok") else 400)


@app.post("/api/avisos/<int:aviso_id>/dispensar")
def api_avisos_dispensar(aviso_id):
    u = usuario_atual()
    if not u:
        return jsonify({"ok": False, "erro": "não autenticado"}), 401
    social.dispensar_aviso(u["id"], aviso_id)
    return jsonify({"ok": True})


@app.post("/api/mesa/<mesa_id>/convidar")
def api_convidar(mesa_id):
    """Convida alguém (por apelido) para esta mesa. Só quem está na mesa convida."""
    u = usuario_atual()
    if not u:
        return jsonify({"ok": False, "erro": "não autenticado"}), 401
    mesa = GM.mesas.get(mesa_id)
    if not mesa:
        return jsonify({"ok": False, "erro": "mesa inexistente"}), 404
    d = request.get_json(force=True, silent=True) or {}
    r = social.convidar_para_mesa(u["apelido"], d.get("apelido", ""),
                                  mesa_id, mesa.nome)
    return jsonify(r), (200 if r.get("ok") else 400)


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
    if responsavel.bloqueado(u["id"]):
        return jsonify({"ok": False, "erro": "Você ativou uma pausa no Jogo Responsável. "
                        "Poderá jogar de novo em " + responsavel.quando_libera(u["id"]) + "."}), 403
    t = GM.torneios.get(tid)
    if not t:
        return jsonify({"ok": False, "erro": "torneio inexistente"}), 404
    try:
        if not any(i["jogador_id"] == u["apelido"] for i in t.inscritos):
            if t.buy_in > 0:      # torneio grátis (buy-in 0) não cobra nem debita
                if wallet.saldo(u["id"]) < t.buy_in:
                    return jsonify({"ok": False, "erro": "saldo insuficiente para o buy-in"}), 400
                wallet.debitar_buy_in(u["id"], t.buy_in, tid)
            t.inscrever(u["apelido"], u["apelido"], usuario_id=u["id"])
        return jsonify({"ok": True})
    except (ValueError, wallet.ErroCarteira) as e:
        return jsonify({"ok": False, "erro": str(e)}), 400


@app.post("/api/torneio/<tid>/convidar")
def api_convidar_torneio(tid):
    """Convida amigos (ou apelidos/e-mails escolhidos) para o torneio. Cada um
    recebe um e-mail com o link para aceitar, e um aviso na plataforma se online."""
    u = usuario_atual()
    if not u:
        return jsonify({"ok": False, "erro": "não autenticado"}), 401
    t = GM.torneios.get(tid)
    if not t:
        return jsonify({"ok": False, "erro": "torneio inexistente"}), 404
    d = request.get_json(force=True, silent=True) or {}
    alvos = d.get("apelidos") or []
    if not alvos:   # sem lista = convida todos os amigos
        alvos = [a["apelido"] for a in social.listar_amigos(u["id"])]
    link = request.host_url.rstrip("/") + "/torneio/" + tid
    enviados, falhas, sem_email = [], [], []
    for alvo in alvos:
        apel = social.resolver_apelido(alvo)
        if not apel or apel == u["apelido"]:
            falhas.append(alvo)
            continue
        # aviso na plataforma (abre janela se a pessoa estiver online)
        social.notificar(apel, "convite_torneio",
                         f"{u['apelido']} convidou você para o torneio {t.nome}.",
                         {"tid": tid, "torneio_nome": t.nome, "de": u["apelido"], "link": link})
        # e-mail com o link
        email = social.email_por_apelido(apel)
        if email and mailer.enviar_convite_torneio(email, apel, u["apelido"], t.nome, link):
            enviados.append(apel)
        else:
            sem_email.append(apel)
    return jsonify({"ok": True, "enviados": enviados, "sem_email": sem_email,
                    "falhas": falhas})


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
            elif cmd == "chat":
                para = (msg.get("para") or "").strip() or None
                ok, motivo = GM.enviar_chat(mesa_id, u["apelido"],
                                            msg.get("texto", ""), para=para)
                # confirma ao remetente (feedback) — inclui erro se houver
                ws.send(json.dumps({"tipo": "chat_ok", "ok": ok, "motivo": motivo,
                                    "privado": bool(para), "para": para}))
    finally:
        try:
            GM.assinantes[mesa_id].remove(ws)
        except (ValueError, KeyError):
            pass


def criar_app():
    # A preparação (banco + timer) roda em SEGUNDO PLANO para o app LIGAR na hora.
    # Assim o worker do gunicorn responde de imediato e o deploy do Render NUNCA dá
    # "Timed out" esperando um banco lento. As tabelas já existem, então as primeiras
    # requisições funcionam mesmo antes de a preparação terminar.
    def _preparar():
        try:
            db.inicializar()
        except Exception as e:  # noqa
            print(f"[app] erro ao inicializar o banco: {type(e).__name__}: {e}", flush=True)
        try:
            GM.iniciar_ticker()
        except Exception as e:  # noqa
            print(f"[app] erro ao iniciar o ticker: {type(e).__name__}: {e}", flush=True)
    threading.Thread(target=_preparar, daemon=True, name="preparar-app").start()
    return app


if __name__ == "__main__":
    db.inicializar()
    GM.iniciar_ticker()
    porta = int(os.environ.get("PORT", 5000))
    print(f"Poker Acessível rodando em http://localhost:{porta}")
    app.run(host="0.0.0.0", port=porta, debug=False, threaded=True)
