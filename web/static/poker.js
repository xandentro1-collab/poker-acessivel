/* Cliente da mesa: WebSocket (com reconexão), render acessível, atalhos,
   timer de ação com contagem regressiva e sons. */
(function () {
  "use strict";

  const dados = document.getElementById("dados-mesa");
  const MESA_ID = dados.dataset.mesaId;
  const EU = dados.dataset.eu;
  const TORNEIO_ID = dados.dataset.torneio || "";

  const NAIPE_SIMBOLO = { h: "♥", d: "♦", c: "♣", s: "♠" };
  const NAIPE_NOME = { h: "copas", d: "ouros", c: "paus", s: "espadas" };
  const NAIPE_COR = { h: "vermelho", d: "vermelho", c: "preto", s: "preto" };
  const RANK_NOME = {
    "2": "2", "3": "3", "4": "4", "5": "5", "6": "6", "7": "7", "8": "8",
    "9": "9", "10": "10", J: "Valete", Q: "Dama", K: "Rei", A: "Ás",
  };

  let ws = null;
  let estado = null;
  let acoesValidas = {};
  let minhaVez = false;
  let sentado = false;
  let ultimaVezAnunciada = null;
  let ultimasCartasAnunciadas = null;   // evita repetir as cartas a cada ação
  let deadlineMs = null;
  let tempoAcao = 0;
  let avisoDezSeg = false;
  let autoFold = false;
  let tentativasReconexao = 0;
  let fechadoDeProposito = false;

  const el = (id) => document.getElementById(id);
  const controles = el("controles");
  const range = el("range-aposta");

  // ---------- cartas ----------
  function parseCarta(codigo) {
    if (!codigo || codigo === "??") return null;
    return { rank: codigo.slice(0, -1), naipe: codigo.slice(-1) };
  }
  function cartaFalada(codigo) {
    const c = parseCarta(codigo);
    return c ? RANK_NOME[c.rank] + " de " + NAIPE_NOME[c.naipe] : "carta virada";
  }
  function elementoCarta(codigo) {
    const div = document.createElement("div");
    const c = parseCarta(codigo);
    if (!c) {
      div.className = "carta verso";
      div.setAttribute("aria-label", "carta virada");
      return div;
    }
    div.className = "carta " + NAIPE_COR[c.naipe];
    div.setAttribute("role", "img");
    div.setAttribute("aria-label", cartaFalada(codigo));
    div.innerHTML = '<span class="rank">' + c.rank + '</span>' +
      '<span class="naipe" aria-hidden="true">' + NAIPE_SIMBOLO[c.naipe] + "</span>";
    return div;
  }

  // ---------- WebSocket com reconexão ----------
  function conectar() {
    const proto = location.protocol === "https:" ? "wss" : "ws";
    ws = new WebSocket(proto + "://" + location.host + "/ws/mesa/" + MESA_ID);
    ws.onopen = function () {
      tentativasReconexao = 0;
      el("status-conexao").textContent = "🟢 Conectado";
      A11y.anunciar("Conectado à mesa.", "polite");
    };
    ws.onclose = function () {
      if (fechadoDeProposito) return;
      el("status-conexao").textContent = "🔴 Reconectando…";
      const espera = Math.min(1000 * Math.pow(2, tentativasReconexao), 10000);
      tentativasReconexao++;
      if (tentativasReconexao === 1) A11y.anunciar("Conexão perdida. Reconectando…", "assertivo");
      setTimeout(conectar, espera);
    };
    ws.onmessage = function (e) {
      const m = JSON.parse(e.data);
      if (m.tipo === "estado") aplicarEstado(m.dados);
      else if (m.tipo === "evento") tratarEvento(m.dados);
      else if (m.tipo === "equidade") {
        A11y.anunciar(m.pct == null ? "Não dá para calcular a chance agora."
                                    : m.pct + " por cento de chance de vencer.", "assertivo");
      }
      else if (m.tipo === "erro") {
        Sons.tocar("erro");
        A11y.anunciar("Ação inválida: " + m.mensagem, "assertivo");
      }
      else if (m.tipo === "chat") receberChat(m);
      else if (m.tipo === "chat_ok") {
        if (m.ok) chatFeedback(m.privado ? "Mensagem privada enviada para " + m.para + "." : "Mensagem enviada.");
        else { chatFeedback("Não enviou: " + (m.motivo || "erro") + "."); Sons.tocar("erro"); }
      }
    };
  }
  function enviar(obj) { if (ws && ws.readyState === 1) ws.send(JSON.stringify(obj)); }

  // ---------- eventos (sons) ----------
  let ultimaNarracaoLen = 0;
  function tratarEvento(evt) {
    const t = evt.tipo || evt.msg;   // ações usam "tipo"; eventos da mesa usam "msg"
    const mapa = { fold: "fold", check: "check", call: "call", bet: "bet",
      raise: "raise", all_in: "allin", street: "cartaMesa", nova_mao: "inicioMao" };
    if (mapa[t]) Sons.tocar(mapa[t]);
    if (t === "fim_mao") tratarFimMao(evt);
    if (t === "fim_torneio") tratarFimTorneio(evt);
    if (t === "eliminacao") tratarEliminacao(evt);
    if (t === "mudanca_mesa" && evt.jogador_id === EU) {
      A11y.anunciar("Você foi movido para outra mesa. Indo...", "assertivo");
      setTimeout(function () { window.location.href = "/mesa/" + evt.nova_mesa; }, 800);
    }
    if (t === "rebuy_oferta" && evt.jogador_id === EU) {
      const d = el("dialog-rebuy"); if (d) { d.hidden = false; setTimeout(() => d.focus(), 40); }
      Sons.tocar("erro");
      A11y.anunciar("Você zerou as fichas. Fazer rebuy? Botões: Fazer rebuy, ou Não.", "assertivo");
    }
    if (t === "addon_oferta") {
      const d = el("dialog-addon"); if (d) { d.hidden = false; setTimeout(() => d.focus(), 40); }
      A11y.anunciar("Intervalo! Comprar add-on de fichas extras? Botões: Comprar, ou Não.", "assertivo");
    }
    if (t === "relatorio_disponivel" && evt.jogador_id === EU) {
      A11y.anunciar("Você saiu do jogo. Um relatório das suas rodadas está disponível. "
        + "Aperte a tecla J a qualquer momento para abri-lo.", "assertivo");
      setTimeout(abrirRelatorio, 1200);   // abre sozinho após o anúncio
    }
    atualizarNarracao(evt.narracao);
  }
  function tratarEliminacao(evt) {
    // vaia para todos; aplauso só para quem eliminou
    Sons.tocar("vaia");
    if (evt.eliminador && evt.eliminador === EU) {
      setTimeout(function () { Sons.tocar("aplauso"); }, 500);
    }
    const txt = evt.eliminado + " perdeu todas as fichas" +
      (evt.eliminador_nome ? ", eliminado por " + evt.eliminador_nome : "") + ".";
    A11y.anunciar(txt, "assertivo");
  }
  function tratarFimMao(evt) {
    const ganhei = (evt.vencedores || []).some((v) => v.jogador === EU);
    setTimeout(() => Sons.tocar(ganhei ? "vitoria" : "derrota"), 250);
    const sd = evt.estado && evt.estado.showdown;
    let txt = "";
    if (sd && sd.length) {
      // showdown: combinação e cartas de cada envolvido
      txt = sd.map(function (s) {
        const cartas = (s.cartas || []).map(cartaFalada).join(" e ");
        return s.venceu ? (s.nome + " leva o pote com " + s.mao + " tendo " + cartas)
                        : (s.nome + " tinha " + s.mao + " com " + cartas);
      }).join(". ") + ".";
    } else if (evt.vencedores && evt.vencedores.length) {
      // ganhou sem showdown (os outros desistiram)
      txt = evt.vencedores.map(function (v) {
        return v.jogador + " levou o pote de " + v.valor + (v.mao ? " com " + v.mao : "");
      }).join("; ") + ".";
    }
    A11y.anunciar("Fim da mão. " + txt, "assertivo");
  }
  function tratarFimTorneio(evt) {
    Sons.tocar("vitoria");
    renderClassificacao(evt.classificacao);
    const campeao = (evt.classificacao || []).find((c) => c.colocacao === 1);
    if (campeao) A11y.anunciar("Torneio encerrado. Campeão: " + campeao.nome + ".", "assertivo");
  }

  // ---------- narração ----------
  function atualizarNarracao(linhas) {
    if (!linhas) return;
    const lista = el("narracao-lista");
    lista.innerHTML = "";
    linhas.forEach((linha) => {
      const li = document.createElement("li");
      li.textContent = linha;
      lista.appendChild(li);
    });
    if (linhas.length > ultimaNarracaoLen) {
      A11y.anunciar(linhas.slice(ultimaNarracaoLen).join(". "), "polite");
    }
    ultimaNarracaoLen = linhas.length;
    lista.scrollTop = 0;
  }

  // ---------- estado ----------
  function aplicarEstado(e) {
    estado = e;
    const mao = e.mao;
    sentado = (e.assentos || []).some((a) => a && a.jogador_id === EU);
    el("btn-sentar").hidden = sentado || (e.torneio && e.entrantes);

    el("pote").textContent = mao ? mao.pote_total : 0;
    el("street-nome").textContent = mao ? nomeStreet(mao.street) : "Aguardando início";

    const board = el("board");
    board.innerHTML = "";
    if (mao && mao.board) mao.board.forEach((c) => board.appendChild(elementoCarta(c)));

    renderInfoTorneio(e);
    renderAssentos(e, mao);
    renderMinhasCartas(mao);

    // timer
    deadlineMs = e.deadline_ms || null;
    tempoAcao = e.tempo_acao || 0;
    if (!deadlineMs) avisoDezSeg = false;

    acoesValidas = e.acoes_validas || {};
    const euAtuo = mao && mao.to_act === EU;
    atualizarControles(euAtuo, mao);

    // fold automático: se ligado, passa (check) quando de graça, senão desiste
    if (euAtuo && autoFold) {
      setTimeout(function () {
        if (!minhaVez) return;
        if ("check" in acoesValidas) acionar("check");
        else if ("fold" in acoesValidas) acionar("fold");
      }, 400);
      return;
    }

    const podeIniciar = !e.torneio_encerrado && (!mao || mao.encerrada || !e.mao_ativa);
    // no modo automático não mostra o botão (as mãos começam sozinhas)
    el("btn-iniciar").hidden = !(sentado && podeIniciar) || !!e.auto_iniciar;

    atualizarNarracao(e.narracao);
    if (e.classificacao && e.classificacao.length) renderClassificacao(e.classificacao);

    const assinatura = e.numero_mao + "-" + (mao ? (mao.board || []).length + "-" + mao.aposta_atual : "0");
    if (euAtuo && ultimaVezAnunciada !== assinatura) {
      ultimaVezAnunciada = assinatura;
      avisoDezSeg = false;
      anunciarMinhaVez(mao);
    }
  }

  function nomeStreet(s) {
    return { preflop: "Pré-flop", flop: "Flop", turn: "Turn", river: "River",
      showdown: "Showdown", encerrada: "Mão encerrada" }[s] || s;
  }

  function renderInfoTorneio(e) {
    const box = el("info-torneio");
    if (!e.torneio || !e.nivel) { box.hidden = true; return; }
    box.hidden = false;
    el("nivel-num").textContent = e.nivel.idx;
    el("nivel-blinds").textContent = e.nivel.sb + "/" + e.nivel.bb +
      (e.nivel.ante ? " (ante " + e.nivel.ante + ")" : "");
    el("nivel-prox").textContent = e.entrantes ? formataTempo(e.nivel.proximo_em) : "ao iniciar";
    const vivos = (e.assentos || []).filter(Boolean).length;
    el("tn-vivos").textContent = vivos + (e.entrantes ? "/" + e.entrantes : "");
  }
  function formataTempo(seg) {
    seg = Math.max(0, Math.round(seg));
    const m = Math.floor(seg / 60), s = seg % 60;
    return m + ":" + String(s).padStart(2, "0");
  }

  function renderAssentos(e, mao) {
    const cont = el("assentos");
    cont.innerHTML = "";
    (e.assentos || []).forEach((a) => {
      if (!a) return;
      const div = document.createElement("div");
      div.className = "assento";
      const jm = mao && (mao.jogadores || []).find((j) => j.id === a.jogador_id);
      const ehVez = mao && mao.to_act === a.jogador_id;
      if (ehVez) div.classList.add("vez");
      if (jm && jm.foldou) div.classList.add("foldou");
      if (a.jogador_id === EU) div.classList.add("eu");
      const ehBotao = mao && mao.button === a.jogador_id;

      let estadoTxt = "";
      if (jm) {
        if (jm.foldou) estadoTxt = "desistiu";
        else if (jm.all_in) estadoTxt = "all-in";
        else if (jm.aposta_rodada > 0) estadoTxt = "apostou " + jm.aposta_rodada;
      }
      const rotulo = a.nome + (a.eh_bot ? " (bot)" : "") + (ehBotao ? ", botão" : "") +
        ", " + a.stack + " fichas" + (estadoTxt ? ", " + estadoTxt : "") +
        (ehVez ? ", na vez" : "");
      div.setAttribute("role", "group");
      div.setAttribute("aria-label", rotulo);

      let html = (ehBotao ? '<span class="btn-dealer" aria-hidden="true">D</span>' : "") +
        '<div class="avatar" aria-hidden="true">' + a.nome.charAt(0).toUpperCase() + "</div>" +
        '<div class="nome">' + a.nome + "</div>" +
        '<div class="stack">' + a.stack + "</div>" +
        '<div class="estado-jog">' + estadoTxt + "</div>";
      // barra de timer para quem está na vez (com deadline humano)
      if (ehVez && e.deadline_ms && !a.eh_bot) {
        html += '<div class="timer-wrap"><div class="timer-barra">' +
          '<div class="timer-fill" id="timer-fill"></div></div>' +
          '<span class="timer-num" id="timer-num" aria-hidden="true"></span></div>';
      }
      div.innerHTML = html;
      cont.appendChild(div);
    });
  }

  function renderMinhasCartas(mao) {
    const cont = el("minhas-cartas");
    cont.innerHTML = "";
    const eu = mao && (mao.jogadores || []).find((j) => j.id === EU);
    if (eu && eu.cartas && eu.cartas.length && eu.cartas[0] !== "??") {
      eu.cartas.forEach((c) => cont.appendChild(elementoCarta(c)));
      // anuncia AS CARTAS só quando você as recebe (mudaram), não a cada ação
      const assinatura = eu.cartas.join(",");
      if (assinatura !== ultimasCartasAnunciadas) {
        ultimasCartasAnunciadas = assinatura;
        A11y.anunciar("Suas cartas: " + eu.cartas.map(cartaFalada).join(" e ") + ".", "polite");
      }
    } else {
      cont.textContent = mao ? "—" : "Aguardando distribuição.";
      ultimasCartasAnunciadas = null;   // sem cartas: zera para anunciar as próximas
    }
  }

  function renderClassificacao(cls) {
    if (!cls || !cls.length) return;
    el("painel-classificacao").hidden = false;
    const lista = el("classificacao-lista");
    lista.innerHTML = "";
    cls.forEach((r) => {
      const li = document.createElement("li");
      const medalha = r.colocacao === 1 ? "🥇" : r.colocacao === 2 ? "🥈" : r.colocacao === 3 ? "🥉" : r.colocacao + "º";
      li.innerHTML = '<span class="medalha">' + medalha + " " + r.nome + "</span>" +
        "<span>" + (r.premio > 0 ? "+" + r.premio : "—") + "</span>";
      li.setAttribute("aria-label", r.colocacao + "º lugar, " + r.nome +
        (r.premio > 0 ? ", prêmio " + r.premio : ""));
      lista.appendChild(li);
    });
  }

  // ---------- controles ----------
  function atualizarControles(euAtuo, mao) {
    minhaVez = euAtuo;
    controles.hidden = !euAtuo;
    if (!euAtuo) return;
    controles.querySelectorAll("[data-acao]").forEach((b) => {
      const a = b.dataset.acao;
      let vis = false;
      if (a === "fold") vis = "fold" in acoesValidas;
      else if (a === "check") vis = "check" in acoesValidas;
      else if (a === "call") { vis = "call" in acoesValidas; if (vis) b.firstChild.textContent = "Pagar " + acoesValidas.call + " "; }
      else if (a === "bet") vis = "bet" in acoesValidas;
      else if (a === "raise") vis = "raise" in acoesValidas;
      else if (a === "all_in") vis = "all_in" in acoesValidas;
      b.hidden = !vis;
    });
    const lim = acoesValidas.raise || acoesValidas.bet;
    const wrap = range.parentElement;
    const inp = el("aposta-input");
    if (lim) {
      wrap.hidden = false;
      range.min = lim.min; range.max = lim.max; range.value = lim.min;
      range.step = mao ? (mao.sb || 1) : 1;
      if (inp) { inp.min = lim.min; inp.max = lim.max; inp.value = lim.min; inp.step = range.step; }
      atualizarValorSlider();
    } else {
      wrap.hidden = true;
    }
  }
  function atualizarValorSlider() {
    el("valor-aposta").textContent = range.value;
    range.setAttribute("aria-valuetext", range.value + " fichas");
  }
  range.addEventListener("input", atualizarValorSlider);

  function acao(nome, valor) {
    if (!minhaVez) { Sons.tocar("erro"); A11y.anunciar("Não é a sua vez.", "assertivo"); return; }
    enviar({ cmd: "acao", acao: nome, valor: valor == null ? null : parseInt(valor, 10) });
  }
  function acionar(nome) {
    if (nome === "bet" || nome === "raise") {
      const inp = el("aposta-input");
      acao(nome, (inp && inp.value) ? inp.value : range.value);
    } else if (nome === "call") acao("call", estado.mao.aposta_atual);
    else acao(nome);
  }
  controles.querySelectorAll("[data-acao]").forEach((b) =>
    b.addEventListener("click", () => acionar(b.dataset.acao)));

  // ---------- anúncios ----------
  function anunciarMinhaVez(mao) {
    Sons.tocar("suaVez");
    const op = [];
    if ("fold" in acoesValidas) op.push("F desistir");
    if ("check" in acoesValidas) op.push("C passar");
    if ("call" in acoesValidas) op.push("C pagar " + acoesValidas.call);
    if ("bet" in acoesValidas) op.push("R apostar");
    if ("raise" in acoesValidas) op.push("R aumentar");
    if ("all_in" in acoesValidas) op.push("A all-in");
    let cartasTxt = "";
    const eu = (mao.jogadores || []).find((j) => j.id === EU);
    if (eu && eu.cartas && eu.cartas[0] !== "??") cartasTxt = " Suas cartas: " + eu.cartas.map(cartaFalada).join(" e ") + ".";
    A11y.anunciar("Sua vez. Pote " + mao.pote_total + "." + cartasTxt + " Opções: " + op.join(", ") + ".", "assertivo");
    const primeiro = controles.querySelector("[data-acao]:not([hidden])");
    if (primeiro) setTimeout(() => primeiro.focus(), 60);
  }
  // ----- helpers de "eu" -----
  function meuJog() { const m = estado && estado.mao; return m && (m.jogadores || []).find((j) => j.id === EU); }
  function meuAssento() { return estado && (estado.assentos || []).find((a) => a && a.jogador_id === EU); }

  // P — pote
  function dizerPote() {
    const m = estado && estado.mao;
    A11y.anunciar(m ? "O pote tem " + m.pote_total + " fichas." : "A mão ainda não começou.", "polite");
  }
  // V — quanto pagar para entrar na mão
  function dizerParaPagar() {
    const m = estado && estado.mao;
    if (!m) { A11y.anunciar("A mão ainda não começou.", "polite"); return; }
    const jog = meuJog();
    const falta = (m.aposta_atual || 0) - (jog ? jog.aposta_rodada : 0);
    A11y.anunciar(falta > 0 ? "Para pagar e entrar na mão: " + falta + " fichas."
                            : "Nada a pagar. Você pode passar (check).", "polite");
  }
  // L — tempo para aumentar os blinds (torneio)
  function dizerBlindTimer() {
    if (!estado || !estado.torneio || !estado.nivel) { A11y.anunciar("Esta mesa não é torneio.", "polite"); return; }
    if (!estado.entrantes) { A11y.anunciar("Os blinds sobem quando o torneio começar.", "polite"); return; }
    A11y.anunciar("Faltam " + formataTempo(estado.nivel.proximo_em) +
      " para aumentar os blinds. Nível atual: " + estado.nivel.sb + " e " + estado.nivel.bb + ".", "polite");
  }
  // H — jogadores na disputa (que não desistiram) + nomes
  function dizerJogadoresNaMao() {
    const m = estado && estado.mao;
    if (!m) { A11y.anunciar("A mão ainda não começou.", "polite"); return; }
    const ativos = (m.jogadores || []).filter((j) => !j.foldou);
    A11y.anunciar(ativos.length + " jogadores na disputa: " +
      ativos.map((j) => j.nome || j.id).join(", ") + ".", "polite");
  }
  // G — minha melhor combinação (ou "Nada")
  function dizerMinhaMao() {
    const m = estado && estado.mao;
    if (!m) { A11y.anunciar("A mão ainda não começou.", "polite"); return; }
    A11y.anunciar("Sua melhor combinação: " + (m.minha_mao || "Nada") + ".", "polite");
  }
  // S — meu stack
  function dizerMeuStack() {
    const jog = meuJog(); const a = meuAssento();
    const s = jog ? jog.stack : (a ? a.stack : null);
    A11y.anunciar(s == null ? "Você não está sentado na mesa." : "Seu stack: " + s + " fichas.", "polite");
  }
  // Shift+S — stacks de todos, do maior para o menor
  function dizerStacksOrdenados() {
    if (!estado) return;
    const arr = (estado.assentos || []).filter(Boolean).slice().sort((x, y) => y.stack - x.stack);
    A11y.anunciar("Do maior para o menor: " + arr.map((a) => a.nome + " " + a.stack + " fichas").join(", ") + ".", "polite");
  }
  // D — minhas duas cartas
  function dizerMinhasCartas() {
    const eu = meuJog();
    A11y.anunciar((eu && eu.cartas && eu.cartas[0] !== "??")
      ? "Suas cartas: " + eu.cartas.map(cartaFalada).join(" e ") + "."
      : "Você não tem cartas no momento.", "polite");
  }
  // E — flop / cartas na mesa
  function dizerFlop() {
    const m = estado && estado.mao;
    if (!m || !m.board || !m.board.length) { A11y.anunciar("Ainda não tem flop.", "polite"); return; }
    A11y.anunciar(nomeStreet(m.street) + ". Cartas na mesa: " + m.board.map(cartaFalada).join(", ") + ".", "polite");
  }
  // I — quanto investi nesta rodada
  function dizerInvestido() {
    const jog = meuJog();
    A11y.anunciar(jog ? "Você tem " + jog.aposta_rodada + " fichas investidas nesta rodada."
                      : "Você não está na mão.", "polite");
  }
  // W — nomes dos jogadores na mesa
  function dizerNomesMesa() {
    if (!estado) return;
    A11y.anunciar("Jogadores na mesa: " +
      (estado.assentos || []).filter(Boolean).map((a) => a.nome).join(", ") + ".", "polite");
  }
  // Shift+W — todos os participantes do torneio (na mesa + eliminados)
  function dizerNomesTorneio() {
    if (!estado) return;
    const naMesa = (estado.assentos || []).filter(Boolean).map((a) => a.nome);
    const elim = (estado.classificacao || []).map((c) => c.nome + " (eliminado, " + c.colocacao + "º)");
    A11y.anunciar((estado.torneio ? "Participantes do torneio: " : "Jogadores: ") +
      naMesa.concat(elim).join(", ") + ".", "polite");
  }
  // T — de quem é a vez
  function dizerVez() {
    const m = estado && estado.mao;
    A11y.anunciar(m && m.to_act ? "É a vez de " + m.to_act + "." : "Nenhuma ação pendente.", "polite");
  }

  // ---------- timer (contagem regressiva local) ----------
  setInterval(function () {
    const fill = el("timer-fill");
    if (!deadlineMs || !tempoAcao) return;
    const restMs = deadlineMs - Date.now();
    const rest = Math.max(0, restMs / 1000);
    const frac = Math.max(0, Math.min(1, rest / tempoAcao));
    if (fill) {
      fill.style.width = (frac * 100) + "%";
      fill.classList.toggle("baixo", rest <= 10);
      const num = el("timer-num");
      if (num) num.textContent = Math.ceil(rest) + "s";
    }
    // Aviso: aos 5 segundos; no timer curto de 7s, avisa aos 3 segundos.
    const limiteAviso = (tempoAcao === 7) ? 3 : 5;
    if (minhaVez && rest <= limiteAviso && rest > 0 && !avisoDezSeg) {
      avisoDezSeg = true;
      Sons.tocar("terror");
      A11y.anunciar("Atenção: " + limiteAviso + " segundos para agir.", "assertivo");
    }
  }, 250);

  // ---------- campo de aposta (tecla R) ----------
  const apostaInput = el("aposta-input");
  function ajustarAposta(delta) {
    if (!apostaInput || apostaInput.parentElement.hidden) return;
    const novo = Math.max(+apostaInput.min, Math.min(+apostaInput.max, (+apostaInput.value || 0) + delta));
    apostaInput.value = novo;
    if (range) { range.value = novo; atualizarValorSlider(); }
    A11y.anunciar(novo + " fichas", "polite");
  }
  function abrirAposta() {
    if (!minhaVez) { Sons.tocar("erro"); A11y.anunciar("Não é a sua vez.", "assertivo"); return; }
    const lim = acoesValidas.raise || acoesValidas.bet;
    if (!lim) { A11y.anunciar("Não dá para apostar ou aumentar agora.", "assertivo"); return; }
    apostaInput.min = lim.min; apostaInput.max = lim.max; apostaInput.value = lim.min;
    apostaInput.parentElement.hidden = false;
    setTimeout(function () { apostaInput.focus(); apostaInput.select(); }, 40);
    const nomeAcao = ("raise" in acoesValidas) ? "aumentar" : "apostar";
    A11y.anunciar("Valor da aposta. Mínimo " + lim.min + " fichas. Digite o valor e Enter para " + nomeAcao +
                  ". Escape para cancelar.", "assertivo");
  }
  if (apostaInput) {
    apostaInput.addEventListener("keydown", function (ev) {
      if (ev.key === "Enter") {
        ev.preventDefault();
        if ("raise" in acoesValidas) acionar("raise");
        else if ("bet" in acoesValidas) acionar("bet");
      } else if (ev.key === "Escape") {
        ev.preventDefault();
        A11y.anunciar("Aposta cancelada.", "polite");
        el("conteudo").focus();
      }
    });
    apostaInput.addEventListener("input", function () {
      if (range) { range.value = apostaInput.value; atualizarValorSlider(); }
    });
  }

  // ---------- diálogo "abandonar partida" (tecla Q) ----------
  function abrirDialogSair() {
    const d = el("dialog-sair");
    if (!d) return;
    d.hidden = false;
    setTimeout(function () { d.focus(); }, 40);
    A11y.anunciar("Deseja mesmo abandonar a partida? Botões: Sair da mesa, ou Continuar jogando.", "assertivo");
  }

  // ---------- teclado ----------
  document.addEventListener("keydown", function (ev) {
    const tag = (ev.target.tagName || "").toLowerCase();
    const digitando = (tag === "input" && ev.target.type !== "range") || tag === "select" || tag === "textarea";
    if (digitando) return;                       // deixa digitar no campo de aposta
    if (ev.ctrlKey || ev.altKey || ev.metaKey) return;

    if (ev.key === "F1") { ev.preventDefault(); alternarAjuda(); return; }  // F1 = ajuda

    // se um diálogo modal está aberto, não dispara atalhos de jogo (deixa o diálogo funcionar)
    if (dialogoModalAberto()) {
      if (ev.key === "Escape") { ev.preventDefault(); fecharDialogos(); }
      return;
    }

    const k = ev.key.toLowerCase();
    const shift = ev.shiftKey;
    let tratou = true;
    switch (k) {
      // --- ações ---
      case "f": if (minhaVez && "fold" in acoesValidas) acionar("fold"); break;
      case "c": if (minhaVez && "call" in acoesValidas) acionar("call");
                else if (minhaVez && "check" in acoesValidas) acionar("check"); break;
      case "a": if (minhaVez && "all_in" in acoesValidas) acionar("all_in"); break;
      case "r": abrirAposta(); break;
      case "q": abrirDialogSair(); break;
      // --- informações faladas ---
      case "p": dizerPote(); break;
      case "v": dizerParaPagar(); break;
      case "l": dizerBlindTimer(); break;
      case "h": dizerJogadoresNaMao(); break;
      case "g": dizerMinhaMao(); break;
      case "s": if (shift) dizerStacksOrdenados(); else dizerMeuStack(); break;
      case "d": dizerMinhasCartas(); break;
      case "e": dizerFlop(); break;
      case "i": dizerInvestido(); break;
      case "w": if (shift) dizerNomesTorneio(); else dizerNomesMesa(); break;
      case "t": dizerVez(); break;
      case "o": pedirEquidade(); break;             // O = chance de vencer (%)
      case "j": abrirRelatorio(); break;            // J = relatório de rodadas
      case "b": focarChat(); break;                 // B = bate-papo (escrever)
      case "n": abrirConvite(); break;              // N = convidar para a mesa
      case "z": if (window.ampliarTela) window.ampliarTela(); break;  // Z = zoom (baixa visão)
      case "k": alternarAutoFold(); break;          // K = fold automático liga/desliga
      case ",": mudarVolume(-10); break;            // vírgula = volume -
      case ".": mudarVolume(10); break;             // ponto = volume +
      case "m": alternarSom(); break;
      // --- ajustar aposta / iniciar mão ---
      case "arrowup": ajustarAposta((+range.step) || 1); break;
      case "arrowdown": ajustarAposta(-((+range.step) || 1)); break;
      case "+": case "=": ajustarAposta(estado && estado.mao ? estado.mao.bb : 50); break;
      case "-": ajustarAposta(-(estado && estado.mao ? estado.mao.bb : 50)); break;
      case "enter": if (minhaVez && "raise" in acoesValidas) acionar("raise");
                    else if (minhaVez && "bet" in acoesValidas) acionar("bet"); else tratou = false; break;
      case " ": if (!el("btn-iniciar").hidden) iniciarMao(); break;
      case "u": if (!el("btn-sentar").hidden) el("btn-sentar").click(); break;  // U = sentar/comprar
      default: tratou = false;
    }
    if (tratou) ev.preventDefault();
  });

  // ---------- botões ----------
  function iniciarMao() {
    enviar({ cmd: "iniciar" });
    el("btn-iniciar").hidden = true;
    A11y.anunciar("Nova mão iniciada.", "polite");
  }
  el("btn-iniciar").addEventListener("click", iniciarMao);

  function sentarComBuyIn(valorReais) {
    const body = (valorReais != null) ? { buy_in: valorReais } : {};
    fetch("/api/mesa/" + MESA_ID + "/sentar", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }).then(function (r) { return r.json(); }).then(function (j) {
      if (j.ok) {
        sentado = true;
        el("btn-sentar").hidden = true;
        el("dialog-buyin").hidden = true;
        const dica = (estado && estado.auto_iniciar)
          ? "As mãos começam automaticamente." : "Pressione Espaço para iniciar a mão.";
        A11y.anunciar("Você sentou na mesa. " + dica, "assertivo");
        enviar({ cmd: "estado" });
      } else {
        Sons.tocar("erro");
        A11y.anunciar("Não foi possível sentar: " + j.erro, "assertivo");
      }
    });
  }
  el("btn-sentar").addEventListener("click", function () {
    const ehCash = !estado || estado.modo === "cash";
    if (ehCash) {
      el("dialog-buyin").hidden = false;
      setTimeout(function () { el("buyin-valor").focus(); el("buyin-valor").select(); }, 40);
      A11y.anunciar("Escolha quanto trazer para a mesa. Digite o valor em reais e confirme.", "assertivo");
    } else {
      sentarComBuyIn(null);   // torneio: buy-in fixo
    }
  });
  el("buyin-ok").addEventListener("click", function () { sentarComBuyIn(el("buyin-valor").value); });
  el("buyin-cancelar").addEventListener("click", function () {
    el("dialog-buyin").hidden = true; el("btn-sentar").focus();
    A11y.anunciar("Cancelado.", "polite");
  });
  el("buyin-valor").addEventListener("keydown", function (ev) {
    if (ev.key === "Enter") { ev.preventDefault(); sentarComBuyIn(el("buyin-valor").value); }
    else if (ev.key === "Escape") { ev.preventDefault(); el("dialog-buyin").hidden = true; el("btn-sentar").focus(); }
  });

  function alternarAjuda() {
    const p = el("painel-ajuda");
    const abrir = p.hidden;
    p.hidden = !abrir;
    el("btn-ajuda").setAttribute("aria-expanded", abrir);
    if (abrir) {
      p.setAttribute("tabindex", "-1"); p.focus();
      A11y.anunciar("Ajuda aberta: função de cada botão e atalho de teclado. "
        + "Use as setas para ler a lista. Aperte F1 de novo para fechar.", "assertivo");
    } else {
      A11y.anunciar("Ajuda fechada.", "polite");
      el("conteudo") && el("conteudo").focus();
    }
  }
  el("btn-ajuda").addEventListener("click", alternarAjuda);

  function alternarSom() {
    const ligado = Sons.alternar();
    const b = el("btn-som");
    b.setAttribute("aria-pressed", ligado);
    b.textContent = (ligado ? "🔊" : "🔇") + " Som (M)";
    A11y.anunciar("Som " + (ligado ? "ligado" : "desligado"), "polite");
  }
  el("btn-som").addEventListener("click", alternarSom);

  // O = chance de vencer (equity). Pede ao servidor e o servidor responde "equidade".
  function pedirEquidade() {
    if (!estado || !estado.mao || estado.mao.encerrada) {
      A11y.anunciar("A chance só é calculada durante uma mão em andamento.", "assertivo");
      return;
    }
    A11y.anunciar("Calculando a chance de vencer...", "polite");
    enviar({ cmd: "equidade" });
  }
  var btnEquidade = el("btn-equidade");
  if (btnEquidade) btnEquidade.addEventListener("click", pedirEquidade);

  // K = fold automático (liga/desliga). Quando ligado, na sua vez passa se de graça,
  // ou desiste se houver aposta para pagar.
  function alternarAutoFold() {
    autoFold = !autoFold;
    var b = el("btn-autofold");
    if (b) {
      b.setAttribute("aria-pressed", autoFold);
      b.textContent = (autoFold ? "☑" : "☐") + " Fold automático (K)";
    }
    A11y.anunciar("Fold automático " + (autoFold ? "ligado. Na sua vez você passa ou desiste sozinho." : "desligado."), "assertivo");
  }
  var btnAutoFold = el("btn-autofold");
  if (btnAutoFold) btnAutoFold.addEventListener("click", alternarAutoFold);

  // vírgula / ponto = volume dos sons (- / +)
  function mudarVolume(delta) {
    var pct = Sons.ajustarVolume(delta);
    A11y.anunciar("Volume " + pct + " por cento.", "assertivo");
    var b = el("btn-volume");
    if (b) b.textContent = "🔉 Volume " + pct + "% (vírgula/ponto)";
  }
  var btnVolMenos = el("btn-volume-menos");
  var btnVolMais = el("btn-volume-mais");
  if (btnVolMenos) btnVolMenos.addEventListener("click", function () { mudarVolume(-10); });
  if (btnVolMais) btnVolMais.addEventListener("click", function () { mudarVolume(10); });

  // ---------- diálogos: helpers ----------
  var IDS_DIALOGOS = ["dialog-sair", "dialog-buyin", "dialog-rebuy", "dialog-addon", "dialog-relatorio", "dialog-convidar"];
  function dialogoModalAberto() {
    return IDS_DIALOGOS.some(function (id) { var d = el(id); return d && !d.hidden; });
  }
  function fecharDialogos() {
    IDS_DIALOGOS.forEach(function (id) { var d = el(id); if (d) d.hidden = true; });
    el("conteudo") && el("conteudo").focus();
  }

  // ---------- relatório de rodadas (tecla J) ----------
  function escopoSelecionado() {
    var r = document.querySelector('input[name="rel-escopo"]:checked');
    return r ? r.value : "proprio";
  }
  function alvosSelecionados() {
    return [].slice.call(document.querySelectorAll('#rel-lista-pessoas input[type="checkbox"]:checked'))
      .map(function (c) { return c.value; });
  }
  function relFeedback(txt) {
    var f = el("rel-feedback"); if (f) f.textContent = txt;
    if (txt) A11y.anunciar(txt, "assertivo");
  }
  function preencherPessoas(nomes) {
    var box = el("rel-lista-pessoas");
    if (!box) return;
    if (!nomes || !nomes.length) { box.textContent = "Ninguém disponível ainda."; return; }
    box.innerHTML = "";
    nomes.forEach(function (nome, i) {
      var lab = document.createElement("label");
      lab.style.display = "block";
      var cb = document.createElement("input");
      cb.type = "checkbox"; cb.value = nome; cb.id = "rel-p-" + i;
      lab.appendChild(cb);
      lab.appendChild(document.createTextNode(" " + nome));
      box.appendChild(lab);
    });
  }
  function gerarRelatorio(silencioso) {
    var escopo = escopoSelecionado();
    return fetch("/api/mesa/" + MESA_ID + "/relatorio", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ escopo: escopo, alvos: alvosSelecionados() }),
    }).then(function (r) { return r.json(); }).then(function (j) {
      if (j.ok) {
        el("rel-texto").value = j.texto || "";
        preencherPessoas(j.jogadores);
        if (!silencioso) relFeedback("Relatório gerado. Use Copiar ou Enviar por e-mail.");
      } else {
        relFeedback(j.erro || "Não foi possível gerar o relatório.");
      }
    }).catch(function () { relFeedback("Erro de conexão ao gerar o relatório."); });
  }
  function abrirRelatorio() {
    var d = el("dialog-relatorio");
    if (!d) return;
    d.hidden = false;
    gerarRelatorio(true).then(function () {
      setTimeout(function () { d.focus(); }, 40);
      A11y.anunciar("Relatório de rodadas aberto. Escolha de quem é o relatório e use os botões "
        + "Copiar ou Enviar por e-mail. Aperte Escape para fechar.", "assertivo");
    });
  }
  function copiarRelatorio() {
    var txt = el("rel-texto").value || "";
    if (!txt) { relFeedback("Não há relatório para copiar. Gere primeiro."); return; }
    function ok() { relFeedback("Copiado para a área de transferência!"); Sons.tocar("copiar"); }
    function falha() {
      // método antigo (funciona sem permissão de clipboard)
      var ta = el("rel-texto"); ta.removeAttribute("readonly"); ta.select();
      try { document.execCommand("copy"); ok(); } catch (e) { relFeedback("Não deu para copiar automaticamente. Selecione o texto e copie com Controle C."); }
      ta.setAttribute("readonly", "readonly");
    }
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(txt).then(ok, falha);
    } else { falha(); }
  }
  function emailRelatorio() {
    relFeedback("Enviando o e-mail...");
    var escopo = escopoSelecionado();
    fetch("/api/mesa/" + MESA_ID + "/relatorio/email", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ escopo: escopo, alvos: alvosSelecionados() }),
    }).then(function (r) { return r.json(); }).then(function (j) {
      if (j.ok) { relFeedback("E-mail enviado para " + (j.destino || "seu e-mail") + "."); Sons.tocar("emailEnviado"); }
      else { relFeedback(j.detalhe || "Não foi possível enviar o e-mail."); Sons.tocar("erro"); }
    }).catch(function () { relFeedback("Erro de conexão ao enviar o e-mail."); Sons.tocar("erro"); });
  }
  (function ligarRelatorio() {
    var b;
    if ((b = el("btn-relatorio"))) b.addEventListener("click", abrirRelatorio);
    if ((b = el("rel-gerar")))   b.addEventListener("click", function () { gerarRelatorio(false); });
    if ((b = el("rel-copiar")))  b.addEventListener("click", copiarRelatorio);
    if ((b = el("rel-email")))   b.addEventListener("click", emailRelatorio);
    if ((b = el("rel-fechar")))  b.addEventListener("click", fecharDialogos);
    // mostra/esconde a lista de pessoas conforme o escopo
    [].slice.call(document.querySelectorAll('input[name="rel-escopo"]')).forEach(function (r) {
      r.addEventListener("change", function () {
        var sel = el("rel-selecao");
        if (sel) sel.hidden = escopoSelecionado() !== "selecionados";
        gerarRelatorio(true);
      });
    });
  })();

  // ---------- bate-papo (tecla B) ----------
  function chatFeedback(txt) {
    var f = el("chat-feedback"); if (f) f.textContent = txt || "";
    if (txt) A11y.anunciar(txt, "assertivo");
  }
  function focarChat() {
    carregarDestinatariosOnline();
    var inp = el("chat-texto");
    if (inp) { inp.focus(); A11y.anunciar("Bate-papo. Escreva e aperte Enter para todos na mesa. "
      + "Para conversa privada, escolha a pessoa em 'Enviar para' ou digite um apelido ou e-mail. "
      + "Use a seta para cima aqui para ler o histórico.", "assertivo"); }
  }
  function enviarChat() {
    var inp = el("chat-texto");
    var sel = el("chat-para");
    var digitado = el("chat-para-apelido");
    if (!inp) return;
    var texto = (inp.value || "").trim();
    if (!texto) { chatFeedback("Escreva algo antes de enviar."); return; }
    // prioridade: apelido/e-mail digitado; senão, a escolha do menu
    var para = (digitado && digitado.value.trim()) || (sel ? sel.value : "") || "";
    enviar({ cmd: "chat", texto: texto, para: para });
    inp.value = "";
    inp.focus();
  }
  // lê o histórico: move o foco para a lista de mensagens
  function irParaHistorico() {
    var lista = el("chat-lista");
    if (lista) { lista.focus(); A11y.anunciar("Histórico de mensagens. Use as setas para ler cada uma.", "assertivo"); }
  }
  function receberChat(m) {
    var lista = el("chat-lista");
    var quem = m.de === EU ? "Você" : m.de;
    var prefixo;
    if (m.privado) {
      prefixo = (m.de === EU) ? ("Você, no privado para " + m.para) : (m.de + ", no privado");
    } else {
      prefixo = quem;
    }
    if (lista) {
      var li = document.createElement("li");
      li.style.margin = "0 0 6px";
      if (m.privado) li.style.fontStyle = "italic";
      li.textContent = prefixo + ": " + m.texto;
      lista.appendChild(li);
      lista.scrollTop = lista.scrollHeight;
      // mantém a lista enxuta
      while (lista.children.length > 60) lista.removeChild(lista.firstChild);
    }
    // verbaliza a mensagem ao chegar (as próprias já têm o feedback de envio)
    if (m.de !== EU) {
      var fala = m.privado ? (m.de + " te mandou no privado: " + m.texto)
                           : (m.de + " disse: " + m.texto);
      A11y.anunciar(fala, "assertivo");
      Sons.tocar(m.privado ? "mensagemPrivada" : "mensagem");
    }
  }
  // preenche "Enviar para" com quem está ONLINE (amigos primeiro, depois A-Z)
  function carregarDestinatariosOnline() {
    var sel = el("chat-para");
    if (!sel) return;
    var atual = sel.value;
    fetch("/api/online").then(function (r) { return r.json(); }).then(function (j) {
      sel.innerHTML = "";
      var optTodos = document.createElement("option");
      optTodos.value = ""; optTodos.textContent = "Todos na mesa (sala em andamento)";
      sel.appendChild(optTodos);
      (j.ok ? j.online : []).forEach(function (p) {
        var o = document.createElement("option");
        o.value = p.apelido;
        o.textContent = "Privado para " + p.apelido + (p.amigo ? " (amigo)" : "");
        sel.appendChild(o);
      });
      if (atual) sel.value = atual;
    }).catch(function () {});
  }
  (function ligarChat() {
    var b = el("chat-enviar");
    if (b) b.addEventListener("click", enviarChat);
    var inp = el("chat-texto");
    if (inp) inp.addEventListener("keydown", function (ev) {
      if (ev.key === "Enter") { ev.preventDefault(); enviarChat(); }
      else if (ev.key === "ArrowUp") { ev.preventDefault(); irParaHistorico(); }  // seta pra cima: ler histórico
      else if (ev.key === "Escape") { ev.preventDefault(); el("conteudo") && el("conteudo").focus(); }
    });
    // da lista de histórico, Escape ou seta pra baixo volta a escrever
    var lista = el("chat-lista");
    if (lista) lista.addEventListener("keydown", function (ev) {
      if (ev.key === "Escape") { ev.preventDefault(); inp && inp.focus(); }
    });
  })();

  // ---------- convidar para a mesa (tecla N) ----------
  function convFeedback(txt) {
    var f = el("conv-feedback"); if (f) f.textContent = txt || "";
    if (txt) A11y.anunciar(txt, "assertivo");
  }
  function carregarAmigosConvite() {
    var sel = el("conv-amigo");
    if (!sel) return;
    fetch("/api/amigos").then(function (r) { return r.json(); }).then(function (j) {
      sel.innerHTML = "";
      var vazio = document.createElement("option");
      vazio.value = "";
      vazio.textContent = (j.ok && j.amigos && j.amigos.length) ? "— escolha um amigo —" : "— você ainda não tem amigos —";
      sel.appendChild(vazio);
      (j.ok ? j.amigos : []).forEach(function (a) {
        var o = document.createElement("option");
        o.value = a.apelido; o.textContent = a.apelido;
        sel.appendChild(o);
      });
    }).catch(function () {});
  }
  function abrirConvite() {
    var d = el("dialog-convidar");
    if (!d) return;
    convFeedback("");
    carregarAmigosConvite();
    d.hidden = false;
    setTimeout(function () { d.focus(); }, 40);
    A11y.anunciar("Convidar para a mesa. Escolha um amigo na lista ou digite o apelido, "
      + "e aperte Convidar. Escape fecha.", "assertivo");
  }
  function enviarConvite() {
    var sel = el("conv-amigo");
    var inp = el("conv-apelido");
    var apelido = (inp && inp.value.trim()) || (sel && sel.value) || "";
    if (!apelido) { convFeedback("Escolha um amigo ou digite um apelido."); return; }
    fetch("/api/mesa/" + MESA_ID + "/convidar", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ apelido: apelido }),
    }).then(function (r) { return r.json(); }).then(function (j) {
      if (j.ok) { convFeedback("Convite enviado para " + j.convidado + "."); Sons.tocar("clique"); if (inp) inp.value = ""; }
      else { convFeedback(j.erro || "Não deu para convidar."); Sons.tocar("erro"); }
    }).catch(function () { convFeedback("Erro de conexão."); });
  }
  (function ligarConvite() {
    var b;
    if ((b = el("btn-convidar"))) b.addEventListener("click", abrirConvite);
    if ((b = el("conv-enviar"))) b.addEventListener("click", enviarConvite);
    if ((b = el("conv-fechar"))) b.addEventListener("click", fecharDialogos);
    var sel = el("conv-amigo");
    if (sel) sel.addEventListener("change", function () {
      var inp = el("conv-apelido"); if (inp && sel.value) inp.value = "";  // escolher amigo limpa o apelido digitado
    });
  })();

  // diálogo "abandonar partida" (tecla Q)
  const btnSairSim = el("sair-sim");
  const btnSairNao = el("sair-nao");
  if (btnSairSim) {
    btnSairSim.addEventListener("click", function () {
      fechadoDeProposito = true;
      A11y.anunciar("Saindo da mesa.", "assertivo");
      window.location.href = "/lobby";
    });
  }
  if (btnSairNao) {
    btnSairNao.addEventListener("click", function () {
      el("dialog-sair").hidden = true;
      A11y.anunciar("Continuando na partida.", "polite");
      el("conteudo").focus();
    });
  }

  // rebuy / add-on (torneio MTT)
  function acaoTorneio(caminho, sucesso) {
    if (!TORNEIO_ID) return;
    fetch("/api/torneio/" + TORNEIO_ID + "/" + caminho, { method: "POST" })
      .then(function (r) { return r.json(); }).then(function (j) {
        if (j.ok) { A11y.anunciar(sucesso, "assertivo"); Sons.tocar(caminho === "addon" ? "addon" : "rebuy"); }
        else { Sons.tocar("erro"); A11y.anunciar("Não deu: " + (j.erro || ""), "assertivo"); }
      });
  }
  if (el("rebuy-sim")) {
    el("rebuy-sim").addEventListener("click", function () {
      el("dialog-rebuy").hidden = true; acaoTorneio("rebuy", "Rebuy feito! Você voltou ao jogo.");
    });
    el("rebuy-nao").addEventListener("click", function () {
      el("dialog-rebuy").hidden = true; A11y.anunciar("Sem rebuy. Você será eliminado.", "polite");
    });
  }
  if (el("addon-sim")) {
    el("addon-sim").addEventListener("click", function () {
      el("dialog-addon").hidden = true; acaoTorneio("addon", "Add-on comprado! Fichas extras adicionadas.");
    });
    el("addon-nao").addEventListener("click", function () {
      el("dialog-addon").hidden = true; A11y.anunciar("Sem add-on.", "polite");
    });
  }

  window.addEventListener("beforeunload", function () { fechadoDeProposito = true; });

  conectar();
})();
