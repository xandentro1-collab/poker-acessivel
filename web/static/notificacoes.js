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

  // ---- diálogo de convite (criado na hora, funciona em qualquer tela) ----
  function abrirDialogoConvite(dados) {
    var existente = document.getElementById("dialog-convite-auto");
    if (existente) existente.remove();
    var d = document.createElement("div");
    d.id = "dialog-convite-auto";
    d.setAttribute("role", "alertdialog");
    d.setAttribute("aria-modal", "true");
    d.setAttribute("aria-labelledby", "conv-auto-txt");
    d.tabIndex = -1;
    d.style.cssText = "position:fixed;left:50%;top:20px;transform:translateX(-50%);z-index:9999;"
      + "max-width:520px;width:92%;background:var(--superficie,#131d34);color:var(--texto,#eef3ff);"
      + "border:2px solid var(--primaria,#ffcf33);border-radius:14px;padding:18px;box-shadow:0 12px 40px rgba(0,0,0,.6)";
    var de = dados.de || "Alguém";
    var mesaNome = dados.mesa_nome || "uma mesa";
    d.innerHTML = '<p id="conv-auto-txt" style="font-weight:800;margin:0 0 12px">'
      + de + ' convidou você para a mesa ' + mesaNome + '. Deseja entrar para jogar?</p>'
      + '<div style="display:flex;gap:10px;flex-wrap:wrap">'
      + '<button type="button" id="conv-auto-sim" class="btn sucesso">Aceitar e entrar</button>'
      + '<button type="button" id="conv-auto-nao" class="btn secundaria">Agora não</button>'
      + '</div>';
    document.body.appendChild(d);
    var sim = document.getElementById("conv-auto-sim");
    var nao = document.getElementById("conv-auto-nao");
    sim.addEventListener("click", function () { window.location.href = "/mesa/" + dados.mesa_id; });
    nao.addEventListener("click", function () { d.remove(); anunciar("Convite recusado.", "polite"); });
    d.addEventListener("keydown", function (ev) { if (ev.key === "Escape") { ev.preventDefault(); d.remove(); } });
    setTimeout(function () { d.focus(); }, 60);
  }

  function tratar(n) {
    if (n.tipo === "convite_mesa" && n.dados && n.dados.mesa_id) {
      ultimoConvite = n.dados;
      som("suaVez");
      anunciar(n.texto);
      abrirDialogoConvite(n.dados);   // abre a janela perguntando
      return;
    } else if (n.tipo === "chat_pv") {
      som("check");         // PV que chegou enquanto você está em outra tela
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
