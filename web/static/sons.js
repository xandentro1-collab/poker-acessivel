/* Sons característicos por ação.
   Por padrão são gerados proceduralmente (Web Audio API) — funcionam offline, sem
   nenhum arquivo. MAS você pode PERSONALIZAR: basta colocar um arquivo MP3 com o
   nome certo na pasta  web/static/sons/  (veja o catálogo em SONS.md). Se o arquivo
   existir, ele é usado no lugar do som gerado. Pode ligar/desligar (tecla M) e
   ajustar o volume (vírgula/ponto). */
(function () {
  "use strict";
  let ctx = null;
  let ligado = true;
  let volume = 0.8;   // multiplicador global de volume (0 a 1)
  // lembra as preferências de som entre as telas
  try {
    const lg = localStorage.getItem("poker_som_ligado");
    if (lg !== null) ligado = lg !== "0";
    const vl = parseFloat(localStorage.getItem("poker_volume"));
    if (!isNaN(vl)) volume = Math.max(0, Math.min(1, vl));
  } catch (e) {}
  function salvarPrefs() {
    try {
      localStorage.setItem("poker_som_ligado", ligado ? "1" : "0");
      localStorage.setItem("poker_volume", String(volume));
    } catch (e) {}
  }

  // Nome do arquivo MP3 (na pasta web/static/sons/) para cada som interno.
  // Troque o arquivo com esse nome para personalizar. Ex.: foldar.mp3
  const NOMES = {
    fold: "foldar", check: "passar", call: "pagar", bet: "aposta",
    raise: "aumentar", allin: "all-in", deal: "distribuir", inicioMao: "inicio-mao",
    cartaMesa: "carta-mesa", suaVez: "sua-vez", vitoria: "vitoria", derrota: "derrota",
    erro: "erro", clique: "clique", copiar: "copiar", emailEnviado: "email-enviado",
    deposito: "deposito", saque: "saque", rebuy: "rebuy", addon: "addon",
    vaia: "vaia", aplauso: "aplauso", terror: "aviso-tempo", novoNivel: "novo-nivel",
    mensagem: "mensagem", mensagemPrivada: "mensagem-privada", conexao: "conexao",
    aviso: "aviso", convite: "convite", amigo: "amigo",
  };
  const PASTA = "/static/sons/";
  const custom = {};   // nome interno -> URL do mp3 (quando existe)

  function garantirContexto() {
    if (!ctx) {
      const AC = window.AudioContext || window.webkitAudioContext;
      if (AC) ctx = new AC();
    }
    if (ctx && ctx.state === "suspended") ctx.resume();
    return ctx;
  }

  // Descobre quais MP3 personalizados existem (uma checagem leve por som, no load).
  function descobrirCustom() {
    Object.keys(NOMES).forEach(function (nome) {
      const url = PASTA + NOMES[nome] + ".mp3";
      fetch(url, { method: "HEAD" }).then(function (r) {
        if (r.ok) custom[nome] = url;
      }).catch(function () {});
    });
  }

  function tocarMp3(nome) {
    try {
      const a = new Audio(custom[nome]);
      a.volume = Math.max(0, Math.min(1, volume));
      a.play().catch(function () {});
      return true;
    } catch (e) { return false; }
  }

  // toca uma sequência de tons: [{freq, dur, tipo, vol, delay}]
  function tocar(notas) {
    if (!ligado) return;
    const c = garantirContexto();
    if (!c) return;
    let t = c.currentTime;
    notas.forEach(function (n) {
      const osc = c.createOscillator();
      const g = c.createGain();
      osc.type = n.tipo || "sine";
      osc.frequency.value = n.freq;
      const inicio = t + (n.delay || 0);
      const vol = Math.max(0.0002, (n.vol == null ? 0.18 : n.vol) * volume);
      g.gain.setValueAtTime(0.0001, inicio);
      g.gain.exponentialRampToValueAtTime(vol, inicio + 0.01);
      g.gain.exponentialRampToValueAtTime(0.0001, inicio + n.dur);
      osc.connect(g).connect(c.destination);
      osc.start(inicio);
      osc.stop(inicio + n.dur + 0.02);
      t = inicio;
    });
  }

  // ruído curto (para "cartas" e "fichas")
  function ruido(dur, vol) {
    if (!ligado) return;
    const c = garantirContexto();
    if (!c) return;
    const n = Math.floor(c.sampleRate * dur);
    const buf = c.createBuffer(1, n, c.sampleRate);
    const data = buf.getChannelData(0);
    for (let i = 0; i < n; i++) data[i] = (Math.random() * 2 - 1) * (1 - i / n);
    const src = c.createBufferSource();
    const g = c.createGain();
    g.gain.value = (vol == null ? 0.1 : vol) * volume;
    src.buffer = buf;
    src.connect(g).connect(c.destination);
    src.start();
  }

  const SONS = {
    // ---- ações do jogo ----
    fold:   () => tocar([{ freq: 180, dur: 0.18, tipo: "sawtooth", vol: 0.12 }]),
    check:  () => tocar([{ freq: 320, dur: 0.08 }, { freq: 320, dur: 0.08, delay: 0.1 }]),
    call:   () => { ruido(0.12, 0.08); tocar([{ freq: 440, dur: 0.1, delay: 0.02 }]); },
    bet:    () => { ruido(0.15, 0.1); tocar([{ freq: 520, dur: 0.1 }, { freq: 660, dur: 0.12, delay: 0.08 }]); },
    raise:  () => { ruido(0.18, 0.12); tocar([{ freq: 520, dur: 0.1 }, { freq: 700, dur: 0.1, delay: 0.08 }, { freq: 880, dur: 0.12, delay: 0.16 }]); },
    allin:  () => tocar([{ freq: 440, dur: 0.1, tipo: "square" }, { freq: 660, dur: 0.1, tipo: "square", delay: 0.1 }, { freq: 990, dur: 0.2, tipo: "square", delay: 0.2 }]),
    deal:   () => { ruido(0.08, 0.06); },
    // embaralhar + repartir (nova mão)
    inicioMao: () => { ruido(0.35, 0.05); setTimeout(function () { ruido(0.07, 0.06); }, 180); setTimeout(function () { ruido(0.07, 0.06); }, 300); },
    // carta comunitária virando (flop/turn/river)
    cartaMesa: () => { ruido(0.10, 0.07); tocar([{ freq: 600, dur: 0.06, tipo: "triangle", vol: 0.1, delay: 0.03 }]); },
    suaVez: () => tocar([{ freq: 880, dur: 0.12, tipo: "triangle" }, { freq: 1180, dur: 0.14, tipo: "triangle", delay: 0.12 }]),
    vitoria:() => tocar([{ freq: 523, dur: 0.14 }, { freq: 659, dur: 0.14, delay: 0.14 }, { freq: 784, dur: 0.14, delay: 0.28 }, { freq: 1046, dur: 0.3, delay: 0.42 }]),
    derrota:() => tocar([{ freq: 392, dur: 0.16, tipo: "sine" }, { freq: 294, dur: 0.3, tipo: "sine", delay: 0.16 }]),
    erro:   () => tocar([{ freq: 200, dur: 0.15, tipo: "square", vol: 0.14 }]),
    // clique curto (feedback genérico de botão)
    clique: () => tocar([{ freq: 660, dur: 0.05, tipo: "triangle", vol: 0.1 }]),
    // copiado (tique curto e agudo)
    copiar: () => tocar([{ freq: 1200, dur: 0.05, tipo: "triangle", vol: 0.12 }, { freq: 1600, dur: 0.05, tipo: "triangle", vol: 0.1, delay: 0.05 }]),
    // e-mail enviado (whoosh subindo)
    emailEnviado: () => { ruido(0.18, 0.05); tocar([{ freq: 500, dur: 0.1, tipo: "sine", vol: 0.12 }, { freq: 900, dur: 0.14, tipo: "sine", vol: 0.12, delay: 0.08 }]); },
    // ---- dinheiro ----
    deposito: () => {
      ruido(0.05, 0.05);
      tocar([{ freq: 784, dur: 0.12, tipo: "triangle", vol: 0.18, delay: 0.02 },
             { freq: 1046, dur: 0.20, tipo: "triangle", vol: 0.18, delay: 0.12 }]);
      setTimeout(function () { ruido(0.10, 0.045); }, 70);
    },
    saque: () => {
      ruido(0.14, 0.07);
      tocar([{ freq: 1046, dur: 0.12, tipo: "triangle", vol: 0.18, delay: 0.02 },
             { freq: 660, dur: 0.22, tipo: "triangle", vol: 0.18, delay: 0.13 }]);
    },
    // recompra (rebuy) — fichas caindo, curto
    rebuy: () => { ruido(0.10, 0.06); tocar([{ freq: 700, dur: 0.1, tipo: "triangle", vol: 0.14, delay: 0.02 }, { freq: 900, dur: 0.12, tipo: "triangle", vol: 0.14, delay: 0.1 }]); },
    // add-on — parecido, mais grave
    addon: () => { ruido(0.10, 0.06); tocar([{ freq: 500, dur: 0.1, tipo: "triangle", vol: 0.14, delay: 0.02 }, { freq: 640, dur: 0.14, tipo: "triangle", vol: 0.14, delay: 0.1 }]); },
    // ---- torneio / plateia ----
    vaia: () => {
      ruido(0.6, 0.05);
      tocar([{ freq: 233, dur: 0.6, tipo: "sawtooth", vol: 0.13 },
             { freq: 220, dur: 0.6, tipo: "sawtooth", vol: 0.11, delay: 0.02 },
             { freq: 165, dur: 0.7, tipo: "sawtooth", vol: 0.12, delay: 0.28 },
             { freq: 123, dur: 0.7, tipo: "sawtooth", vol: 0.11, delay: 0.5 }]);
    },
    aplauso: () => {
      for (let i = 0; i < 16; i++) {
        setTimeout(function () { ruido(0.035, 0.09); }, i * 65 + Math.random() * 45);
      }
    },
    terror: () => {
      ruido(0.06, 0.09);
      tocar([{ freq: 1200, dur: 0.20, tipo: "sawtooth", vol: 0.17 },
             { freq: 1272, dur: 0.20, tipo: "sawtooth", vol: 0.15 },
             { freq: 87, dur: 0.30, tipo: "square", vol: 0.15 }]);
    },
    // blinds subiram (level up ascendente)
    novoNivel: () => tocar([{ freq: 523, dur: 0.1, tipo: "triangle" }, { freq: 659, dur: 0.1, tipo: "triangle", delay: 0.1 }, { freq: 880, dur: 0.16, tipo: "triangle", delay: 0.2 }]),
    // ---- social / avisos ----
    // mensagem pública recebida (pop suave)
    mensagem: () => tocar([{ freq: 620, dur: 0.06, tipo: "sine", vol: 0.12 }, { freq: 780, dur: 0.07, tipo: "sine", vol: 0.12, delay: 0.06 }]),
    // mensagem privada (PV) — mais grave e "íntima"
    mensagemPrivada: () => tocar([{ freq: 440, dur: 0.08, tipo: "sine", vol: 0.13 }, { freq: 520, dur: 0.09, tipo: "sine", vol: 0.12, delay: 0.09 }]),
    // alguém conectou (blip curto subindo)
    conexao: () => tocar([{ freq: 660, dur: 0.07, tipo: "triangle", vol: 0.1 }, { freq: 990, dur: 0.08, tipo: "triangle", vol: 0.1, delay: 0.07 }]),
    // comunicado da plataforma (sino/ding duplo)
    aviso: () => tocar([{ freq: 1046, dur: 0.14, tipo: "sine", vol: 0.14 }, { freq: 1318, dur: 0.18, tipo: "sine", vol: 0.13, delay: 0.14 }]),
    // convite recebido (arpejo amigável subindo)
    convite: () => tocar([{ freq: 523, dur: 0.1, tipo: "triangle", vol: 0.14 }, { freq: 784, dur: 0.1, tipo: "triangle", vol: 0.14, delay: 0.1 }, { freq: 1046, dur: 0.16, tipo: "triangle", vol: 0.14, delay: 0.2 }]),
    // novo amigo (ta-da curtinho)
    amigo: () => tocar([{ freq: 659, dur: 0.1, tipo: "triangle", vol: 0.14 }, { freq: 988, dur: 0.16, tipo: "triangle", vol: 0.14, delay: 0.1 }]),
  };

  window.Sons = {
    tocar: function (nome) {
      if (!ligado) return;
      if (custom[nome]) { if (tocarMp3(nome)) return; }   // usa o MP3 personalizado, se houver
      try { (SONS[nome] || function () {})(); } catch (e) {}
    },
    alternar: function () { ligado = !ligado; salvarPrefs(); return ligado; },
    ligado: function () { return ligado; },
    ativarContexto: garantirContexto,
    nomes: function () { return Object.assign({}, NOMES); },   // catálogo nome->arquivo
    volume: function () { return Math.round(volume * 100); },
    ajustarVolume: function (delta) {
      volume = Math.max(0, Math.min(1, volume + delta / 100));
      salvarPrefs();
      try { garantirContexto(); if (!custom.clique) tocar([{ freq: 660, dur: 0.08 }]); else tocarMp3("clique"); } catch (e) {}
      return Math.round(volume * 100);
    },
    // define o volume direto (0 a 100) — usado pela tela de Configurações
    definirVolume: function (pct) {
      volume = Math.max(0, Math.min(1, (parseFloat(pct) || 0) / 100));
      salvarPrefs();
      return Math.round(volume * 100);
    },
  };

  descobrirCustom();
})();
