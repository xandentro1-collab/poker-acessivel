/* Notificações por usuário, em todas as páginas (polling).
   Verbaliza convites de mesa, avisos e presença. F2 aceita o último convite. */
(function () {
  "use strict";
  var ultimoConvite = null;   // {mesa_id, mesa_nome, de}

  function anunciar(txt, tipo) {
    if (window.A11y && txt) A11y.anunciar(txt, tipo || "assertivo");
  }
  function som(nome) {
    try { if (window.Sons) Sons.tocar(nome); } catch (e) {}
  }

  function tratar(n) {
    if (n.tipo === "convite_mesa" && n.dados && n.dados.mesa_id) {
      ultimoConvite = n.dados;
      som("suaVez");
    } else if (n.tipo === "conexao") {
      som("deal");          // som curto e discreto: alguém entrou
    } else if (n.tipo === "aviso") {
      som("suaVez");        // aviso da plataforma: som um pouco mais destacado
    } else {
      som("check");
    }
    anunciar(n.texto);
  }

  function poll() {
    fetch("/api/notificacoes", { headers: { "Accept": "application/json" } })
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (j) {
        if (j && j.ok && j.notificacoes && j.notificacoes.length) {
          j.notificacoes.forEach(tratar);
        }
      })
      .catch(function () {});
  }

  // aceitar o último convite de mesa (também chamável por um botão)
  window.aceitarConvite = function () {
    if (ultimoConvite && ultimoConvite.mesa_id) {
      anunciar("Entrando na mesa " + (ultimoConvite.mesa_nome || "") + ".");
      window.location.href = "/mesa/" + ultimoConvite.mesa_id;
    } else {
      anunciar("Você não tem convite de mesa pendente.");
    }
  };

  document.addEventListener("keydown", function (ev) {
    if (ev.key === "F2") { ev.preventDefault(); window.aceitarConvite(); }
  });

  setTimeout(poll, 800);          // primeira checagem logo ao carregar
  setInterval(poll, 4000);        // depois a cada 4 segundos
})();
