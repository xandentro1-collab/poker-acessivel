/* Cliente da mesa: WebSocket (com reconexão), render acessível, atalhos,
   timer de ação com contagem regressiva e sons. */
(function () {
  "use strict";

  const dados = document.getElementById("dados-mesa");
  const MESA_ID = dados.dataset.mesaId;
  const EU = dados.dataset.eu;

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
  let deadlineMs = null;
  let tempoAcao = 0;
  let avisoDezSeg = false;
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
      else if (m.tipo === "erro") {
        Sons.tocar("erro");
        A11y.anunciar("Ação inválida: " + m.mensagem, "assertivo");
      }
    };
  }
  function enviar(obj) { if (ws && ws.readyState === 1) ws.send(JSON.stringify(obj)); }

  // ---------- eventos (sons) ----------
  let ultimaNarracaoLen = 0;
  function tratarEvento(evt) {
    const t = evt.tipo;
    const mapa = { fold: "fold", check: "check", call: "call", bet: "bet",
      raise: "raise", all_in: "allin", street: "deal", nova_mao: "deal" };
    if (mapa[t]) Sons.tocar(mapa[t]);
    if (t === "fim_mao") tratarFimMao(evt);
    if (t === "fim_torneio") tratarFimTorneio(evt);
    atualizarNarracao(evt.narracao);
  }
  function tratarFimMao(evt) {
    const ganhei = (evt.vencedores || []).some((v) => v.jogador === EU);
    setTimeout(() => Sons.tocar(ganhei ? "vitoria" : "derrota"), 250);
    if (evt.vencedores) {
      const txt = evt.vencedores.map((v) =>
        v.jogador + " venceu " + v.valor + (v.mao ? " com " + v.mao : "")).join("; ");
      A11y.anunciar("Fim da mão. " + txt, "assertivo");
    }
    if (sentado) el("btn-iniciar").hidden = false;
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

    const podeIniciar = !e.torneio_encerrado && (!mao || mao.encerrada || !e.mao_ativa);
    el("btn-iniciar").hidden = !(sentado && podeIniciar);

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
    } else {
      cont.textContent = mao ? "—" : "Aguardando distribuição.";
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
    if (lim) {
      range.parentElement.hidden = false;
      range.min = lim.min; range.max = lim.max; range.value = lim.min;
      range.step = mao ? (mao.sb || 1) : 1;
      atualizarValorSlider();
    } else {
      range.parentElement.hidden = true;
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
    if (nome === "bet" || nome === "raise") acao(nome, range.value);
    else if (nome === "call") acao("call", estado.mao.aposta_atual);
    else acao(nome);
  }
  controles.querySelectorAll("[data-acao]").forEach((b) =>
    b.addEventListener("click", () => acionar(b.dataset.acao)));

  // ---------- anúncios ----------
  function anunciarMinhaVez(mao) {
    Sons.tocar("suaVez");
    const op = [];
    if ("fold" in acoesValidas) op.push("F desistir");
    if ("check" in acoesValidas) op.push("C ou K passar");
    if ("call" in acoesValidas) op.push("C pagar " + acoesValidas.call);
    if ("bet" in acoesValidas) op.push("B apostar");
    if ("raise" in acoesValidas) op.push("R aumentar");
    if ("all_in" in acoesValidas) op.push("A all-in");
    let cartasTxt = "";
    const eu = (mao.jogadores || []).find((j) => j.id === EU);
    if (eu && eu.cartas && eu.cartas[0] !== "??") cartasTxt = " Suas cartas: " + eu.cartas.map(cartaFalada).join(" e ") + ".";
    A11y.anunciar("Sua vez. Pote " + mao.pote_total + "." + cartasTxt + " Opções: " + op.join(", ") + ".", "assertivo");
    const primeiro = controles.querySelector("[data-acao]:not([hidden])");
    if (primeiro) setTimeout(() => primeiro.focus(), 60);
  }
  function descreverMesa() {
    if (!estado || !estado.mao) { A11y.anunciar("A mão ainda não começou.", "polite"); return; }
    const m = estado.mao;
    const board = (m.board || []).map(cartaFalada).join(", ") || "sem cartas ainda";
    A11y.anunciar(nomeStreet(m.street) + ". Pote " + m.pote_total + ". Board: " + board + ". " +
      (m.to_act ? "Vez de " + m.to_act : "sem ação pendente") + ".", "polite");
  }
  function dizerMinhasCartas() {
    const m = estado && estado.mao;
    const eu = m && (m.jogadores || []).find((j) => j.id === EU);
    A11y.anunciar((eu && eu.cartas && eu.cartas[0] !== "??")
      ? "Suas cartas: " + eu.cartas.map(cartaFalada).join(" e ") + "."
      : "Você não tem cartas no momento.", "polite");
  }
  function dizerStacks() {
    if (!estado) return;
    A11y.anunciar((estado.assentos || []).filter(Boolean)
      .map((a) => a.nome + " " + a.stack + " fichas").join(". "), "polite");
  }
  function dizerVez() {
    const m = estado && estado.mao;
    A11y.anunciar(m && m.to_act ? "É a vez de " + m.to_act + "." : "Nenhuma ação pendente.", "polite");
  }
  function dizerTempo() {
    if (!deadlineMs) { A11y.anunciar("Sem tempo cronometrado agora.", "polite"); return; }
    const rest = Math.max(0, Math.round((deadlineMs - Date.now()) / 1000));
    A11y.anunciar(rest + " segundos restantes.", "polite");
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
    if (minhaVez && rest <= 10 && rest > 0 && !avisoDezSeg) {
      avisoDezSeg = true;
      Sons.tocar("erro");
      A11y.anunciar("Atenção: 10 segundos para agir.", "assertivo");
    }
  }, 250);

  // ---------- teclado ----------
  function ajustarSlider(delta) {
    if (range.parentElement.hidden) return;
    range.value = Math.max(+range.min, Math.min(+range.max, +range.value + delta));
    atualizarValorSlider();
    A11y.anunciar(range.value + " fichas", "polite");
  }
  document.addEventListener("keydown", function (ev) {
    const tag = (ev.target.tagName || "").toLowerCase();
    if (((tag === "input" && ev.target.type !== "range") || tag === "select" || tag === "textarea")) return;
    if (ev.ctrlKey || ev.altKey || ev.metaKey) return;
    const k = ev.key.toLowerCase();
    let tratou = true;
    switch (k) {
      case "f": if (minhaVez && "fold" in acoesValidas) acionar("fold"); break;
      case "c": if (minhaVez && "call" in acoesValidas) acionar("call");
                else if (minhaVez && "check" in acoesValidas) acionar("check"); break;
      case "k": if (minhaVez && "check" in acoesValidas) acionar("check"); break;
      case "b": if (minhaVez && "bet" in acoesValidas) acionar("bet"); break;
      case "r": if (minhaVez && "raise" in acoesValidas) acionar("raise"); break;
      case "a": if (minhaVez && "all_in" in acoesValidas) acionar("all_in"); break;
      case "arrowup": ajustarSlider(+range.step || 1); break;
      case "arrowdown": ajustarSlider(-(+range.step || 1)); break;
      case "+": case "=": ajustarSlider(estado && estado.mao ? estado.mao.bb : 50); break;
      case "-": ajustarSlider(-(estado && estado.mao ? estado.mao.bb : 50)); break;
      case "enter": if (minhaVez && "raise" in acoesValidas) acionar("raise");
                    else if (minhaVez && "bet" in acoesValidas) acionar("bet"); else tratou = false; break;
      case " ": if (!el("btn-iniciar").hidden) iniciarMao(); break;
      case "d": descreverMesa(); break;
      case "s": dizerMinhasCartas(); break;
      case "p": dizerStacks(); break;
      case "t": dizerTempo(); break;
      case "v": dizerVez(); break;
      case "h": alternarAjuda(); break;
      case "m": alternarSom(); break;
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

  el("btn-sentar").addEventListener("click", async function () {
    const r = await fetch("/api/mesa/" + MESA_ID + "/sentar", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ buy_in: 50 }),
    });
    const j = await r.json();
    if (j.ok) {
      sentado = true;
      el("btn-sentar").hidden = true;
      A11y.anunciar("Você sentou na mesa. Pressione Espaço para iniciar a mão.", "assertivo");
      enviar({ cmd: "estado" });
    } else {
      Sons.tocar("erro");
      A11y.anunciar("Não foi possível sentar: " + j.erro, "assertivo");
    }
  });

  function alternarAjuda() {
    const p = el("painel-ajuda");
    const abrir = p.hidden;
    p.hidden = !abrir;
    el("btn-ajuda").setAttribute("aria-expanded", abrir);
    if (abrir) { p.setAttribute("tabindex", "-1"); p.focus(); }
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

  window.addEventListener("beforeunload", function () { fechadoDeProposito = true; });

  conectar();
})();
