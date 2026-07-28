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
    const t = evt.tipo || evt.msg;   // ações usam "tipo"; eventos da mesa usam "msg"
    const mapa = { fold: "fold", check: "check", call: "call", bet: "bet",
      raise: "raise", all_in: "allin", street: "deal", nova_mao: "deal" };
    if (mapa[t]) Sons.tocar(mapa[t]);
    if (t === "fim_mao") tratarFimMao(evt);
    if (t === "fim_torneio") tratarFimTorneio(evt);
    if (t === "eliminacao") tratarEliminacao(evt);
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
      case "m": alternarSom(); break;
      // --- ajustar aposta / iniciar mão ---
      case "arrowup": ajustarAposta((+range.step) || 1); break;
      case "arrowdown": ajustarAposta(-((+range.step) || 1)); break;
      case "+": case "=": ajustarAposta(estado && estado.mao ? estado.mao.bb : 50); break;
      case "-": ajustarAposta(-(estado && estado.mao ? estado.mao.bb : 50)); break;
      case "enter": if (minhaVez && "raise" in acoesValidas) acionar("raise");
                    else if (minhaVez && "bet" in acoesValidas) acionar("bet"); else tratou = false; break;
      case " ": if (!el("btn-iniciar").hidden) iniciarMao(); break;
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

  window.addEventListener("beforeunload", function () { fechadoDeProposito = true; });

  conectar();
})();
