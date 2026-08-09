/* Bonecos (avatares) dos jogadores. Um GERADOR monta 20 homens + 20 mulheres,
   variando pele, cabelo, cor, acessórios e camisa — cada um com uma DESCRIÇÃO
   automática para o leitor de tela. O jogador escolhe o seu no Perfil; na mesa,
   o assento mostra o boneco escolhido. Usado por poker.js e perfil.html. */
(function () {
  "use strict";

  var PELE = [
    { nome: "pele clara", cor: "#efc6a1" },
    { nome: "pele morena clara", cor: "#d29a6f" },
    { nome: "pele morena", cor: "#b87c4f" },
    { nome: "pele escura", cor: "#8a5a34" },
  ];
  var CABELO = [
    { nome: "castanho", cor: "#4a3421" },
    { nome: "preto", cor: "#241810" },
    { nome: "loiro", cor: "#caa62a" },
    { nome: "ruivo", cor: "#a6522a" },
    { nome: "grisalho", cor: "#c9c4bd" },
  ];
  var CAMISA = [
    { nome: "azul", cor: "#2f6fb0" }, { nome: "verde", cor: "#2f8f5b" },
    { nome: "vermelha", cor: "#c0392b" }, { nome: "roxa", cor: "#7d4a9e" },
    { nome: "vinho", cor: "#8c3b4a" }, { nome: "verde-água", cor: "#1f9e8f" },
    { nome: "laranja", cor: "#d1731f" }, { nome: "cinza", cor: "#5b6673" },
    { nome: "amarela", cor: "#c9a227" }, { nome: "azul-marinho", cor: "#2a3f66" },
  ];

  function escurecer(hex, f) {
    var n = parseInt(hex.slice(1), 16);
    return "rgb(" + Math.round(((n >> 16) & 255) * f) + ","
      + Math.round(((n >> 8) & 255) * f) + "," + Math.round((n & 255) * f) + ")";
  }

  function cartas() {
    return '<g stroke="#b98f22" stroke-width="0.8">'
      + '<rect x="16.5" y="31" width="8.5" height="12" rx="1.4" fill="#fffdf6" transform="rotate(-11 20.7 37)"/>'
      + '<rect x="23" y="31" width="8.5" height="12" rx="1.4" fill="#fffdf6" transform="rotate(11 27.2 37)"/>'
      + '</g>';
  }

  // Monta o SVG a partir das características (f: bg, shirt, skin, estilo, hairColor,
  // beard, glasses, earrings, cap).
  function construir(f) {
    var hc = f.hairColor, s = '<svg viewBox="0 0 48 48" aria-hidden="true" focusable="false">';
    s += '<circle cx="24" cy="24" r="24" fill="' + f.bg + '"/>';
    s += '<path d="M9 43 Q9 29 24 29 Q39 29 39 43 Z" fill="' + f.shirt + '"/>';
    s += '<rect x="21.5" y="23.5" width="5" height="6" fill="' + f.skin + '"/>';
    // cabelo/estilo ATRÁS da cabeça
    if (f.estilo === "comprido") {
      s += '<path d="M14 19 Q13 31 17.5 34 L17.5 20 Q17.5 12 24 12 Q30.5 12 30.5 20 L30.5 34 Q35 31 34 19 Q34 9 24 9 Q14 9 14 19 Z" fill="' + hc + '"/>';
    } else if (f.estilo === "trancas") {
      s += '<rect x="13.8" y="18" width="3.2" height="16" rx="1.6" fill="' + hc + '"/>';
      s += '<rect x="31" y="18" width="3.2" height="16" rx="1.6" fill="' + hc + '"/>';
    } else if (f.estilo === "rabo") {
      s += '<path d="M30 13.5 Q37.5 16 36.5 24.5 Q34.5 31 30 31 Q34.5 24 31 17.5 Z" fill="' + hc + '"/>';
    } else if (f.estilo === "coque") {
      s += '<circle cx="24" cy="9" r="3.5" fill="' + hc + '"/>';
    }
    s += '<circle cx="24" cy="18.5" r="7.8" fill="' + f.skin + '"/>';   // cabeça
    // cabelo no topo
    if (f.estilo === "careca") {
      s += '<path d="M16.4 20 Q15.4 16 17.6 14.6 Q17.2 18 18.6 20 Z" fill="' + hc + '"/>';
      s += '<path d="M31.6 20 Q32.6 16 30.4 14.6 Q30.8 18 29.4 20 Z" fill="' + hc + '"/>';
    } else if (f.estilo !== "bone") {
      s += '<path d="M16.2 16 Q17 9.3 24 9.3 Q31 9.3 31.8 16 Q27 12.6 24 12.6 Q21 12.6 16.2 16 Z" fill="' + hc + '"/>';
    }
    if (f.estilo === "bone") {
      s += '<path d="M15.5 15.2 Q16 9 24 9 Q32 9 32.5 15.2 Z" fill="' + f.cap + '"/>';
      s += '<path d="M15.8 15.2 L10.5 16.4 Q13.5 14.4 16 15 Z" fill="' + f.cap + '"/>';
    }
    if (f.beard) {
      s += '<path d="M16.6 19.5 Q17 27.5 24 27.5 Q31 27.5 31.4 19.5 Q31 24.5 24 24.5 Q17 24.5 16.6 19.5 Z" fill="' + hc + '"/>';
    }
    s += '<circle cx="21" cy="18.6" r="1" fill="#2a2018"/><circle cx="27" cy="18.6" r="1" fill="#2a2018"/>';
    s += '<path d="M21.5 21.8 Q24 23.4 26.5 21.8" fill="none" stroke="#8a5a3a" stroke-width="0.9" stroke-linecap="round"/>';
    if (f.glasses) {
      s += '<g fill="none" stroke="#2a2018" stroke-width="1"><circle cx="21" cy="18.6" r="2.5"/><circle cx="27" cy="18.6" r="2.5"/><line x1="23.5" y1="18.6" x2="24.5" y2="18.6"/></g>';
    }
    if (f.earrings) {
      s += '<circle cx="16.4" cy="21.2" r="1.1" fill="#ffd54a"/><circle cx="31.6" cy="21.2" r="1.1" fill="#ffd54a"/>';
    }
    return s + cartas() + '</svg>';
  }

  function homem(i, pele, cor, camisa, estilo, barba, oculos) {
    var f = { bg: escurecer(camisa.cor, 0.62), shirt: camisa.cor, skin: pele.cor,
      estilo: estilo, hairColor: cor.cor, beard: barba, glasses: oculos,
      cap: escurecer(camisa.cor, 0.82) };
    var est = estilo === "careca" ? "careca"
      : estilo === "bone" ? "de boné"
      : "cabelo curto " + cor.nome;
    var desc = "Homem de " + pele.nome + ", " + est
      + (barba ? ", com barba" : "") + (oculos ? ", de óculos" : "")
      + ", camisa " + camisa.nome + ".";
    return { id: "m" + (i + 1), genero: "homem", rotulo: "Homem " + (i + 1), desc: desc, f: f };
  }

  function mulher(j, pele, cor, camisa, estilo, brincos, oculos) {
    var f = { bg: escurecer(camisa.cor, 0.62), shirt: camisa.cor, skin: pele.cor,
      estilo: estilo, hairColor: cor.cor, beard: false, glasses: oculos, earrings: brincos };
    var est = estilo === "comprido" ? "cabelo comprido " + cor.nome
      : estilo === "curto" ? "cabelo curto " + cor.nome
      : estilo === "trancas" ? "tranças " + cor.nome
      : estilo === "coque" ? "cabelo " + cor.nome + " preso em coque"
      : "rabo de cavalo " + cor.nome;
    var desc = "Mulher de " + pele.nome + ", " + est
      + (brincos ? ", com brincos" : "") + (oculos ? ", de óculos" : "")
      + ", blusa " + camisa.nome + ".";
    return { id: "f" + (j + 1), genero: "mulher", rotulo: "Mulher " + (j + 1), desc: desc, f: f };
  }

  function gerar() {
    var lista = [], i;
    var estH = ["curto", "careca", "bone", "curto"];
    var estM = ["comprido", "curto", "trancas", "coque", "rabo"];
    for (i = 0; i < 20; i++) {
      lista.push(homem(i, PELE[i % 4], CABELO[(i * 3) % 5], CAMISA[i % 10],
        estH[i % estH.length], (i % 3 === 0), (i % 4 === 2)));
    }
    for (i = 0; i < 20; i++) {
      lista.push(mulher(i, PELE[(i + 1) % 4], CABELO[(i * 2 + 1) % 5], CAMISA[(i + 3) % 10],
        estM[i % estM.length], (i % 2 === 0), (i % 5 === 3)));
    }
    return lista;
  }

  var LISTA = gerar(), MAPA = {};
  LISTA.forEach(function (a) { a.svg = construir(a.f); MAPA[a.id] = a; });

  // Fallback determinístico pelo nome (bots e quem ainda não escolheu).
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
