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

  // Botão sair (presente no cabeçalho quando logado)
  document.addEventListener("DOMContentLoaded", function () {
    const btnSair = document.getElementById("btn-sair");
    if (btnSair) {
      btnSair.addEventListener("click", function () {
        fetch("/api/logout", { method: "POST" }).then(function () {
          window.location.href = "/entrar";
        });
      });
    }
  });
})();
