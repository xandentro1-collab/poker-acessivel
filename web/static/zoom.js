/* Zoom / baixa visão: amplia a tela toda (texto, cartas, botões).
   3 níveis (Normal, Grande, Gigante). Guardado no navegador, vale em todas as telas.
   Botão no topo (🔍 Zoom) e, na mesa, a tecla Z. */
(function () {
  "use strict";
  var NIVEIS = ["Normal", "Grande", "Gigante"];
  var nivel = 0;
  try { nivel = parseInt(localStorage.getItem("poker_zoom") || "0", 10) || 0; } catch (e) {}
  if (nivel < 0 || nivel > 2) nivel = 0;

  function aplicar() {
    var h = document.documentElement;
    h.classList.remove("zoom-1", "zoom-2");
    if (nivel === 1) h.classList.add("zoom-1");
    else if (nivel === 2) h.classList.add("zoom-2");
    var b = document.getElementById("btn-zoom");
    if (b) b.textContent = "🔍 Zoom: " + NIVEIS[nivel];
  }

  // aplica cedo (antes de pintar) para não "pular"
  aplicar();
  document.addEventListener("DOMContentLoaded", aplicar);

  // gira Normal -> Grande -> Gigante -> Normal
  window.ampliarTela = function () {
    nivel = (nivel + 1) % 3;
    try { localStorage.setItem("poker_zoom", String(nivel)); } catch (e) {}
    aplicar();
    if (window.A11y) A11y.anunciar("Zoom " + NIVEIS[nivel] + ".", "assertivo");
  };

  document.addEventListener("DOMContentLoaded", function () {
    var b = document.getElementById("btn-zoom");
    if (b) b.addEventListener("click", window.ampliarTela);
  });
})();
