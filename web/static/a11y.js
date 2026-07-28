/* Utilitários de acessibilidade compartilhados: anúncios em regiões ao vivo,
   logout e ativação de áudio no primeiro gesto do usuário. */
(function () {
  "use strict";

  window.A11y = {
    // Anuncia para leitor de tela. prioridade: "polite" | "assertivo"
    anunciar: function (texto, prioridade) {
      const id = prioridade === "assertivo" ? "live-assertivo" : "live-polite";
      const el = document.getElementById(id);
      if (!el) return;
      // limpar e reescrever força o leitor a reanunciar mensagens repetidas
      el.textContent = "";
      window.setTimeout(function () { el.textContent = texto; }, 30);
    },
  };

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
