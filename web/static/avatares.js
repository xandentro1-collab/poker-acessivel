/* Bonecos (avatares) dos jogadores: um conjunto fixo de opções, homens e mulheres
   em igual quantidade. Cada um tem uma DESCRIÇÃO para o leitor de tela. O jogador
   escolhe o seu no Perfil; na mesa, o assento mostra o boneco escolhido.
   Usado tanto na mesa (poker.js) quanto na tela de escolha (perfil.html). */
(function () {
  "use strict";

  var PELE = { clara: "#efc6a1", media: "#d29a6f", escura: "#a9744e" };

  function cartas() {
    return '<g stroke="#b98f22" stroke-width="0.8">'
      + '<rect x="16.5" y="31" width="8.5" height="12" rx="1.4" fill="#fffdf6" transform="rotate(-11 20.7 37)"/>'
      + '<rect x="23" y="31" width="8.5" height="12" rx="1.4" fill="#fffdf6" transform="rotate(11 27.2 37)"/>'
      + '</g>';
  }

  // Monta o SVG a partir das características (f).
  function construir(f) {
    var s = '<svg viewBox="0 0 48 48" aria-hidden="true" focusable="false">';
    s += '<circle cx="24" cy="24" r="24" fill="' + f.bg + '"/>';
    s += '<path d="M9 43 Q9 29 24 29 Q39 29 39 43 Z" fill="' + f.shirt + '"/>';    // ombros/camisa
    s += '<rect x="21.5" y="23.5" width="5" height="6" fill="' + f.skin + '"/>';   // pescoço
    // cabelo comprido (atrás da cabeça, desenhado antes)
    if (f.hair === "comprido") {
      s += '<path d="M14 19 Q13 31 17.5 34 L17.5 20 Q17.5 12 24 12 Q30.5 12 30.5 20 L30.5 34 Q35 31 34 19 Q34 9 24 9 Q14 9 14 19 Z" fill="' + f.hairColor + '"/>';
    }
    if (f.hair === "trancas") {
      s += '<rect x="13.8" y="18" width="3.2" height="16" rx="1.6" fill="' + f.hairColor + '"/>';
      s += '<rect x="31" y="18" width="3.2" height="16" rx="1.6" fill="' + f.hairColor + '"/>';
    }
    s += '<circle cx="24" cy="18.5" r="7.8" fill="' + f.skin + '"/>';              // cabeça
    // cabelo no topo (curto/grisalho/comprido/tranças)
    if (["curto", "grisalho", "comprido", "trancas"].indexOf(f.hair) >= 0) {
      s += '<path d="M16.2 16 Q17 9.3 24 9.3 Q31 9.3 31.8 16 Q27 12.6 24 12.6 Q21 12.6 16.2 16 Z" fill="' + f.hairColor + '"/>';
    }
    if (f.hair === "coque") {
      s += '<circle cx="24" cy="9.2" r="3.2" fill="' + f.hairColor + '"/>';
      s += '<path d="M16.2 16 Q17 10 24 10 Q31 10 31.8 16 Q27 13 24 13 Q21 13 16.2 16 Z" fill="' + f.hairColor + '"/>';
    }
    if (f.cap) {   // boné
      s += '<path d="M15.5 15.2 Q16 9 24 9 Q32 9 32.5 15.2 Z" fill="' + f.cap + '"/>';
      s += '<path d="M15.8 15.2 L10.5 16.4 Q13.5 14.4 16 15 Z" fill="' + f.cap + '"/>';
    }
    if (f.beard) {  // barba
      s += '<path d="M16.6 19.5 Q17 27.5 24 27.5 Q31 27.5 31.4 19.5 Q31 24.5 24 24.5 Q17 24.5 16.6 19.5 Z" fill="' + f.hairColor + '"/>';
    }
    // olhos + sorriso
    s += '<circle cx="21" cy="18.6" r="1" fill="#2a2018"/><circle cx="27" cy="18.6" r="1" fill="#2a2018"/>';
    s += '<path d="M21.5 21.8 Q24 23.4 26.5 21.8" fill="none" stroke="#8a5a3a" stroke-width="0.9" stroke-linecap="round"/>';
    if (f.glasses) {   // óculos
      s += '<g fill="none" stroke="#2a2018" stroke-width="1">'
        + '<circle cx="21" cy="18.6" r="2.5"/><circle cx="27" cy="18.6" r="2.5"/>'
        + '<line x1="23.5" y1="18.6" x2="24.5" y2="18.6"/></g>';
    }
    if (f.earrings) {  // brincos
      s += '<circle cx="16.4" cy="21.2" r="1.1" fill="#ffd54a"/><circle cx="31.6" cy="21.2" r="1.1" fill="#ffd54a"/>';
    }
    s += cartas();
    s += '</svg>';
    return s;
  }

  // Conjunto: 3 homens + 3 mulheres. Descrições pensadas para o leitor de tela.
  var LISTA = [
    { id: "m1", genero: "homem", rotulo: "Rapaz de cabelo curto",
      desc: "Homem jovem, pele morena, cabelo curto castanho, camisa azul.",
      f: { bg: "#255c86", shirt: "#2f6fb0", skin: PELE.media, hair: "curto", hairColor: "#4a3421" } },
    { id: "m2", genero: "homem", rotulo: "Homem de barba e boné",
      desc: "Homem de pele escura, com barba, boné e camisa verde.",
      f: { bg: "#25764a", shirt: "#2f8f5b", skin: PELE.escura, hair: "curto", hairColor: "#241810", beard: true, cap: "#1c5f3c" } },
    { id: "m3", genero: "homem", rotulo: "Senhor grisalho de óculos",
      desc: "Senhor de pele clara, cabelo grisalho, óculos e camisa vinho.",
      f: { bg: "#7a2f3c", shirt: "#8c3b4a", skin: PELE.clara, hair: "grisalho", hairColor: "#c9c4bd", glasses: true } },
    { id: "f1", genero: "mulher", rotulo: "Moça de cabelo comprido",
      desc: "Mulher jovem, pele morena, cabelo comprido castanho, brincos e blusa vermelha.",
      f: { bg: "#a5322a", shirt: "#c0392b", skin: PELE.media, hair: "comprido", hairColor: "#5a3a20", earrings: true } },
    { id: "f2", genero: "mulher", rotulo: "Mulher de cabelo curto",
      desc: "Mulher de pele escura, cabelo curto, brincos e blusa roxa.",
      f: { bg: "#6a3e88", shirt: "#7d4a9e", skin: PELE.escura, hair: "curto", hairColor: "#241810", earrings: true } },
    { id: "f3", genero: "mulher", rotulo: "Moça de tranças e óculos",
      desc: "Mulher de pele clara, tranças, óculos e blusa verde-água.",
      f: { bg: "#1a8a7d", shirt: "#1f9e8f", skin: PELE.clara, hair: "trancas", hairColor: "#3a2414", glasses: true } },
  ];

  var MAPA = {};
  LISTA.forEach(function (a) { a.svg = construir(a.f); MAPA[a.id] = a; });

  // Fallback determinístico pelo nome (para bots e para quem ainda não escolheu).
  function porNome(nome) {
    var h = 0, s = String(nome || "?");
    for (var i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) % LISTA.length;
    return LISTA[h];
  }

  window.Avatares = {
    lista: LISTA,
    ids: LISTA.map(function (a) { return a.id; }),
    svg: function (id, nome) { return (MAPA[id] || porNome(nome)).svg; },
    desc: function (id, nome) { return (MAPA[id] || porNome(nome)).desc; },
  };
})();
