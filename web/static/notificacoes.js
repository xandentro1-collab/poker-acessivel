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
  function abrirDialogoConvite(mensagem, url) {
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
    d.innerHTML = '<p id="conv-auto-txt" style="font-weight:800;margin:0 0 12px">' + mensagem + '</p>'
      + '<div style="display:flex;gap:10px;flex-wrap:wrap">'
      + '<button type="button" id="conv-auto-sim" class="btn sucesso">Aceitar e entrar</button>'
      + '<button type="button" id="conv-auto-nao" class="btn secundaria">Agora não</button>'
      + '</div>';
    document.body.appendChild(d);
    document.getElementById("conv-auto-sim").addEventListener("click", function () { window.location.href = url; });
    document.getElementById("conv-auto-nao").addEventListener("click", function () { d.remove(); anunciar("Convite recusado.", "polite"); });
    d.addEventListener("keydown", function (ev) { if (ev.key === "Escape") { ev.preventDefault(); d.remove(); } });
    setTimeout(function () { d.focus(); }, 60);
  }

  function tratar(n) {
    if (n.tipo === "convite_mesa" && n.dados && n.dados.mesa_id) {
      ultimoConvite = n.dados;
      som("convite");
      anunciar(n.texto);
      abrirDialogoConvite(n.dados.de + " convidou você para a mesa "
        + (n.dados.mesa_nome || "") + ". Deseja entrar para jogar?", "/mesa/" + n.dados.mesa_id);
      return;
    } else if (n.tipo === "convite_torneio" && n.dados && n.dados.tid) {
      som("convite");
      anunciar(n.texto);
      abrirDialogoConvite(n.dados.de + " convidou você para o torneio "
        + (n.dados.torneio_nome || "") + ". Deseja ver e se inscrever?", "/torneio/" + n.dados.tid);
      return;
    } else if (n.tipo === "vaga_mesa" && n.dados && n.dados.mesa_id) {
      som("convite");
      anunciar(n.texto);
      abrirDialogoConvite("Abriu uma vaga na mesa " + (n.dados.mesa_nome || "")
        + ". Deseja entrar para jogar?", "/mesa/" + n.dados.mesa_id);
      return;
    } else if (n.tipo === "chat_pv") {
      som("mensagemPrivada");   // PV que chegou enquanto você está em outra tela
    } else if (n.tipo === "conexao") {
      som("conexao");           // alguém entrou
    } else if (n.tipo === "aviso") {
      som("aviso");             // comunicado da plataforma
    } else if (n.tipo === "amigo_novo") {
      som("amigo");             // novo amigo
    } else {
      som("clique");
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

  // ---- Jogo Responsável: lembrete de tempo de jogo ----
  // Avisa quando o tempo jogando cruza o limite escolhido (e a cada novo intervalo).
  var proximoLembrete = 0;        // 0 = ainda não sei o limite
  function checarTempo() {
    fetch("/api/jogo-responsavel/estado", { headers: { "Accept": "application/json" } })
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (j) {
        if (!j || !j.ok || !j.limite_min) return;   // sem limite: nada a fazer
        if (proximoLembrete === 0) proximoLembrete = j.limite_min;
        if (j.minutos_jogando >= proximoLembrete) {
          anunciar("Lembrete: você está jogando há " + j.minutos_jogando
            + " minutos. Que tal fazer uma pausa?", "assertivo");
          som("aviso");
          // reprograma o próximo lembrete para daqui a mais um intervalo
          while (proximoLembrete <= j.minutos_jogando) proximoLembrete += j.limite_min;
        }
      })
      .catch(function () {});
  }
  setTimeout(checarTempo, 5000);
  setInterval(checarTempo, 60000);
})();
