/* Utilitários de acessibilidade compartilhados: anúncios em regiões ao vivo,
   logout e ativação de áudio no primeiro gesto do usuário. */
(function () {
  "use strict";

  // FILA de fala (aria-live "polite"): quando muitas ações acontecem em sequência
  // rápida (vários jogadores seguidos), os anúncios se atropelam e o leitor de tela
  // PERDE alguns. A fila fala um de cada vez, dando tempo entre eles, para NENHUM
  // anúncio ser pulado. O tempo de cada fala é estimado pelo tamanho do texto.
  var _fila = [];
  var _processando = false;
  function _duracaoEstim(texto) {
    return Math.max(700, Math.min(8000, (texto ? texto.length : 0) * 60));
  }
  function _proximoDaFila() {
    if (!_fila.length) { _processando = false; return; }
    _processando = true;
    var texto = _fila.shift();
    var el = document.getElementById("live-polite");
    if (el) {
      el.textContent = "";
      window.setTimeout(function () { el.textContent = texto; }, 20);
    }
    window.setTimeout(_proximoDaFila, _duracaoEstim(texto));
  }

  window.A11y = {
    // Anuncia para leitor de tela. prioridade: "polite" (fila, não perde) |
    // "assertivo" (fala na hora, interrompe — para 'sua vez', erros, resultados).
    anunciar: function (texto, prioridade) {
      if (!texto) return;
      if (prioridade === "assertivo") {
        var el = document.getElementById("live-assertivo");
        if (!el) return;
        el.textContent = "";
        window.setTimeout(function () { el.textContent = texto; }, 20);
        return;
      }
      _fila.push(texto);
      if (_fila.length > 40) _fila.shift();   // não deixa a fila crescer sem limite
      if (!_processando) _proximoDaFila();
    },

    // Verbosidade da narração falada: "completa" (tudo), "media" (sem as ações de
    // cada jogador) ou "baixa" (só os resultados). Fica guardada no navegador.
    NIVEIS_VERBOSIDADE: ["completa", "media", "baixa"],
    verbosidade: function () {
      try {
        const v = localStorage.getItem("poker_verbosidade");
        return (v === "media" || v === "baixa") ? v : "completa";
      } catch (e) { return "completa"; }
    },
    setVerbosidade: function (v) {
      try { localStorage.setItem("poker_verbosidade", v); } catch (e) {}
      return v;
    },
    // Importância mínima que uma linha precisa ter para ser FALADA, dado o nível.
    _minImportancia: function () {
      return { completa: 1, media: 2, baixa: 3 }[this.verbosidade()] || 1;
    },
  };

  // ---------------------------------------------------------------------------
  // FOCUS TRAP: enquanto um diálogo (role dialog/alertdialog) está aberto, o Tab
  // e o Shift+Tab circulam SÓ dentro dele — o foco não escapa para a página atrás.
  // Funciona para qualquer modal visível, inclusive os criados na hora (convite).
  // ---------------------------------------------------------------------------
  function visivel(el) {
    return !!el && !el.hidden && el.getClientRects().length > 0 &&
      getComputedStyle(el).visibility !== "hidden";
  }
  function modalAberto() {
    const modais = document.querySelectorAll('[role="dialog"],[role="alertdialog"]');
    for (let i = modais.length - 1; i >= 0; i--) {   // o último visível é o de cima
      if (visivel(modais[i])) return modais[i];
    }
    return null;
  }
  function focaveis(cont) {
    const sel = 'a[href],button:not([disabled]),input:not([disabled]),' +
      'select:not([disabled]),textarea:not([disabled]),[tabindex]:not([tabindex="-1"])';
    return [].slice.call(cont.querySelectorAll(sel)).filter(visivel);
  }
  document.addEventListener("keydown", function (ev) {
    if (ev.key !== "Tab") return;
    const modal = modalAberto();
    if (!modal) return;
    const f = focaveis(modal);
    if (!f.length) { ev.preventDefault(); try { modal.focus(); } catch (e) {} return; }
    const primeiro = f[0], ultimo = f[f.length - 1], ativo = document.activeElement;
    if (!modal.contains(ativo)) { ev.preventDefault(); primeiro.focus(); return; }
    if (ev.shiftKey && ativo === primeiro) { ev.preventDefault(); ultimo.focus(); }
    else if (!ev.shiftKey && ativo === ultimo) { ev.preventDefault(); primeiro.focus(); }
  }, true);   // captura: age antes dos outros atalhos

  // Ativa o áudio no primeiro clique/tecla (política de autoplay dos navegadores)
  function ativarAudioUmaVez() {
    if (window.Sons) window.Sons.ativarContexto();
    document.removeEventListener("pointerdown", ativarAudioUmaVez);
    document.removeEventListener("keydown", ativarAudioUmaVez);
  }
  document.addEventListener("pointerdown", ativarAudioUmaVez);
  document.addEventListener("keydown", ativarAudioUmaVez);

  // Ao carregar/mudar de página: avisa "página carregada" e move o foco para o
  // primeiro componente da tela (o título principal), para o leitor de tela já
  // começar a ler do início, com contexto.
  function aoCarregarPagina() {
    const main = document.getElementById("conteudo");
    const h1 = document.querySelector("main h1") || main;

    // 1) Feedback de que a página foi carregada (genérico; o nome vem do foco a seguir)
    A11y.anunciar("Página carregada.", "assertivo");

    // 2) Foco no primeiro componente (título principal): o leitor lê o nome da tela
    const alvo = h1 || main;
    if (alvo) {
      alvo.setAttribute("tabindex", "-1");
      // pequeno atraso garante que o leitor de tela acompanhe o novo foco
      window.setTimeout(function () {
        try { alvo.focus({ preventScroll: false }); } catch (e) { alvo.focus(); }
      }, 120);
    }
  }

  // Botão sair (presente no cabeçalho quando logado)
  function aoIniciar() {
    const btnSair = document.getElementById("btn-sair");
    if (btnSair) {
      btnSair.addEventListener("click", function () {
        A11y.anunciar("Saindo...", "assertivo");
        fetch("/api/logout", { method: "POST" }).then(function () {
          window.location.href = "/entrar";
        });
      });
    }
    aoCarregarPagina();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", aoIniciar);
  } else {
    aoIniciar();
  }

  // Ao voltar/avançar no histórico do navegador (páginas restauradas do cache)
  window.addEventListener("pageshow", function (e) {
    if (e.persisted) aoCarregarPagina();
  });
})();
