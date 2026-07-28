/* Sons característicos por ação, gerados proceduralmente com Web Audio API.
   Nenhum arquivo externo — funciona offline. Pode ser desligado (tecla M). */
(function () {
  "use strict";
  let ctx = null;
  let ligado = true;

  function garantirContexto() {
    if (!ctx) {
      const AC = window.AudioContext || window.webkitAudioContext;
      if (AC) ctx = new AC();
    }
    if (ctx && ctx.state === "suspended") ctx.resume();
    return ctx;
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
      const vol = n.vol == null ? 0.18 : n.vol;
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
    g.gain.value = vol == null ? 0.1 : vol;
    src.buffer = buf;
    src.connect(g).connect(c.destination);
    src.start();
  }

  const SONS = {
    fold:   () => tocar([{ freq: 180, dur: 0.18, tipo: "sawtooth", vol: 0.12 }]),
    check:  () => tocar([{ freq: 320, dur: 0.08 }, { freq: 320, dur: 0.08, delay: 0.1 }]),
    call:   () => { ruido(0.12, 0.08); tocar([{ freq: 440, dur: 0.1, delay: 0.02 }]); },
    bet:    () => { ruido(0.15, 0.1); tocar([{ freq: 520, dur: 0.1 }, { freq: 660, dur: 0.12, delay: 0.08 }]); },
    raise:  () => { ruido(0.18, 0.12); tocar([{ freq: 520, dur: 0.1 }, { freq: 700, dur: 0.1, delay: 0.08 }, { freq: 880, dur: 0.12, delay: 0.16 }]); },
    allin:  () => tocar([{ freq: 440, dur: 0.1, tipo: "square" }, { freq: 660, dur: 0.1, tipo: "square", delay: 0.1 }, { freq: 990, dur: 0.2, tipo: "square", delay: 0.2 }]),
    deal:   () => { ruido(0.08, 0.06); },
    suaVez: () => tocar([{ freq: 880, dur: 0.12, tipo: "triangle" }, { freq: 1180, dur: 0.14, tipo: "triangle", delay: 0.12 }]),
    vitoria:() => tocar([{ freq: 523, dur: 0.14 }, { freq: 659, dur: 0.14, delay: 0.14 }, { freq: 784, dur: 0.14, delay: 0.28 }, { freq: 1046, dur: 0.3, delay: 0.42 }]),
    derrota:() => tocar([{ freq: 392, dur: 0.16, tipo: "sine" }, { freq: 294, dur: 0.3, tipo: "sine", delay: 0.16 }]),
    erro:   () => tocar([{ freq: 200, dur: 0.15, tipo: "square", vol: 0.14 }]),
    // Caixa registradora — DEPÓSITO (dinheiro entrando): "cha-ching" ascendente.
    deposito: () => {
      ruido(0.05, 0.05); // clique da gaveta
      tocar([
        { freq: 784,  dur: 0.12, tipo: "triangle", vol: 0.18, delay: 0.02 },  // sol
        { freq: 1046, dur: 0.20, tipo: "triangle", vol: 0.18, delay: 0.12 },  // dó agudo (sobe)
      ]);
      setTimeout(function () { ruido(0.10, 0.045); }, 70); // moedas caindo
    },
    // Caixa registradora — SAQUE (dinheiro saindo): gaveta abrindo + tom descendente.
    saque: () => {
      ruido(0.14, 0.07); // gaveta abrindo (mais longa)
      tocar([
        { freq: 1046, dur: 0.12, tipo: "triangle", vol: 0.18, delay: 0.02 }, // dó agudo
        { freq: 660,  dur: 0.22, tipo: "triangle", vol: 0.18, delay: 0.13 }, // mi (desce)
      ]);
    },
    // Vaia da plateia (jogador perdeu todas as fichas): graves dissonantes descendentes.
    vaia: () => {
      ruido(0.6, 0.05);
      tocar([
        { freq: 233, dur: 0.6, tipo: "sawtooth", vol: 0.13 },
        { freq: 220, dur: 0.6, tipo: "sawtooth", vol: 0.11, delay: 0.02 },  // batimento (dissonância)
        { freq: 165, dur: 0.7, tipo: "sawtooth", vol: 0.12, delay: 0.28 },  // desce (buuu)
        { freq: 123, dur: 0.7, tipo: "sawtooth", vol: 0.11, delay: 0.5 },
      ]);
    },
    // Aplausos (você eliminou alguém): vários estalos de ruído, como palmas.
    aplauso: () => {
      for (let i = 0; i < 16; i++) {
        setTimeout(function () { ruido(0.035, 0.09); }, i * 65 + Math.random() * 45);
      }
    },
  };

  window.Sons = {
    tocar: function (nome) { try { (SONS[nome] || function () {})(); } catch (e) {} },
    alternar: function () { ligado = !ligado; return ligado; },
    ligado: function () { return ligado; },
    ativarContexto: garantirContexto,
  };
})();
