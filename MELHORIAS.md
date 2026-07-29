# 🗺️ Roadmap — deixar o Poker Acessível profissional e inclusivo

**Princípio nº 1: acessibilidade primeiro.** Toda melhoria abaixo — inclusive as
visuais — precisa funcionar 100% com **leitor de tela + teclado**. O visual serve
para incluir quem enxerga **sem** criar barreira para quem não enxerga.

> Legenda de prioridade: **P0** = essencial / faça primeiro · **P1** = importante ·
> **P2** = quando der. Cada item traz **o caminho** a seguir.

## 📊 Onde estamos hoje (diagnóstico)
- **Testes automáticos:** 45 passando. **Cobertura 44%** — o *motor do jogo* está bem
  coberto (72–93%), mas a **camada web/servidor** (rotas, social, torneio MTT, e-mail)
  está **sem testes automáticos** (0%). Foi tudo testado à mão; falta automatizar.
- **Lint (ruff):** 44 apontamentos (a maioria pequenos: `except` genérico, imports
  fora de ordem). 8 corrigíveis automaticamente.
- **Acessibilidade:** boa base (foco no 1º elemento, regiões ao vivo, atalhos, sons,
  zoom, alto contraste, menos-animação). **Falta uma auditoria formal** (ferramentas
  abaixo) e testar com vários leitores de tela.

---

## 1) ♿ Acessibilidade (o coração do projeto)

- **P0 — Auditoria WCAG automática.** Rodar **axe** e **Lighthouse** em cada tela e
  corrigir. Caminho: instalar as ferramentas da seção "Ferramentas de validação".
- **P0 — Travar o foco dentro dos diálogos (focus trap).** Hoje os modais recebem
  foco, mas o Tab pode "escapar" para trás deles. Caminho: ao abrir um diálogo,
  prender o Tab entre o primeiro e o último elemento; Esc fecha (já fecha em vários).
- **P1 — Verbosidade configurável.** Deixar o jogador escolher o quanto o jogo fala
  (ex.: narrar toda ação de todos, ou só a própria vez). Caminho: preferência salva
  (já temos a tabela `preferencias`) + checar antes de cada `A11y.anunciar`.
- **P1 — Matriz de leitores de tela.** Testar com **NVDA** e **JAWS** (Windows),
  **VoiceOver** (Mac/iPhone) e **TalkBack** (Android). Caminho: checklist por tela.
- **P1 — Rótulos e ordem de tabulação.** Revisar `aria-label`/`aria-describedby` de
  todos os controles e a ordem lógica do Tab em cada página.
- **P2 — Idiomas (i18n).** Estrutura para traduzir a interface (começa em pt-BR).

## 2) 🎨 Layout, design e apresentação

- **P1 — Sistema de design consistente.** Padronizar cores, espaçamentos, botões e
  cartões num só lugar (já há variáveis CSS; falta documentar e uniformizar).
- **P1 — Estados de carregamento e vazio.** Mostrar "carregando…" e mensagens claras
  quando não há mesas/torneios/avisos (parte já existe).
- **P1 — Marca e identidade.** Logo próprio, favicon, e uma **tela de apresentação
  (landing)** curta antes do login explicando o que é a plataforma.
- **P2 — Alternador de tema claro/escuro** explícito (hoje segue o sistema).
- **P2 — Polimento mobile** (já responsivo; refinar toque e tamanhos).

## 3) 🏠 Tela inicial e novas seções

- **P0 — Página de Perfil.** Apelido, estatísticas (mãos jogadas, vitórias), e um
  **hub de Configurações** central: sons (ligar/volume), verbosidade, notificações,
  zoom. Caminho: nova rota `/perfil` + `/config`.
- **P1 — Painel inicial (dashboard) enxuto.** Resumo: saldo (link p/ carteira), mesas
  em andamento, convites pendentes, avisos. (Já começamos a enxugar a home.)
- **P1 — Central de notificações persistente.** Hoje os avisos são "de passagem";
  criar um histórico que a pessoa pode reabrir. Caminho: guardar notificações no banco.
- **P1 — Ranking / placar.** Lista de melhores jogadores (por fichas ganhas, vitórias).
- **P2 — Onboarding / tutorial** acessível para quem chega pela primeira vez.

## 4) ♠ Jogo e regras (nível de plataforma séria)

- **P0 — Histórico de mãos no banco.** Hoje o histórico/relatório é por mesa **na
  memória** (some ao reiniciar). Caminho: gravar cada mão numa tabela `maos`.
- **P1 — Banco de tempo (time bank).** Além do timer, um tempo extra que o jogador
  usa em decisões difíceis. Caminho: por jogador, consome quando o timer zera.
- **P1 — Proteção de desconexão.** Se cair no meio da mão, tratar como all-in/È
  "sentado fora" em vez de perder por tempo. Caminho: detectar WS fechado na vez.
- **P1 — Lista de espera** para mesas cheias, e **sentar fora** (sit-out) temporário.
- **P2 — Rake (comissão) configurável** por mesa/torneio (economia da plataforma).
- **P2 — Variantes**: Omaha, e opções como straddle/ante — sempre narradas.
- **P2 — Replay de mão** acessível (reouvir uma mão jogada, passo a passo).

## 5) 💬 Social e moderação

- **P0 — Bloquear / silenciar** um jogador (não receber PV/menções dele).
- **P0 — Denunciar abuso** + um painel de moderação para o admin.
- **P1 — Histórico de chat** persistente (hoje é só da sessão).
- **P1 — Lista de quem está online** como seção própria (já temos `/api/online`).

## 6) 🏆 Torneios

- **P1 — Agenda/calendário de torneios** com horário de início e inscrição antecipada.
- **P1 — Estrutura visível**: níveis de blind, premiação, nº de inscritos, tempo p/
  próximo nível — tudo falado.
- **P2 — Inscrição tardia (late reg)** e **satélites**.

## 7) 🔒 Segurança e infraestrutura

- **P0 — Proteção CSRF** nas ações que mudam estado (hoje contamos com SameSite;
  somar um token). **Rate limiting** no login e nas rotas sensíveis.
- **P1 — Registro de auditoria** (quem fez o quê) e **monitoramento de erros** (ex.:
  Sentry) para saber de falhas em produção.
- **P1 — Backups do banco** (PostgreSQL do Render) automatizados.
- **P2 (dinheiro real, fora do escopo atual):** licença de jogo, **gateway PIX**,
  **KYC** (verificação de identidade), e **RNG certificado** (aleatoriedade auditada).

## 8) ✅ Testes e qualidade (para não quebrar a cada mudança)

- **P0 — Testes automáticos da camada web.** Cobrir rotas (login, mesa, amigos,
  chat, avisos, torneio) e os módulos `social`/`mtt` (hoje 0%). Caminho: usar o
  cliente de teste do Flask (`app.test_client()`) — não precisa de navegador.
- **P0 — Testes de acessibilidade automatizados** (axe) rodando nas telas principais.
- **P1 — Testes ponta-a-ponta** com **Playwright** (inclui checagens de acessibilidade).
- **P1 — Integração contínua (CI).** GitHub Actions rodando testes + lint + axe a cada
  push, para nada quebrar sem a gente ver.
- **P1 — Lint/format no código.** `ruff` (já instalado) e `black` no Python; `ESLint`
  no JavaScript. Rodar `ruff check --fix` resolve 8 itens de imediato.

## 9) 🔊 Sons (feito agora + próximos)

- **Feito:** catálogo completo com **30 sons nomeados** e **sons distintos** para o
  que antes era genérico (mensagem, PV, conexão, aviso, convite, amigo, copiar,
  e-mail, rebuy, add-on, nova mão, carta na mesa...). Veja **SONS.md**. Já dá para
  **trocar por MP3 seu** colocando o arquivo em `web/static/sons/`.
- **P2 — Temas de som** (pacotes) e **volume por tipo** de evento.
- **P2 — Pistas espaciais** (esquerda/direita) para indicar de quem é a vez.

---

## 🧰 Ferramentas de validação (o que usar e como)

**Importante:** este computador **não tem Node.js instalado**, e várias ferramentas
de acessibilidade rodam em Node. Para usá-las, o primeiro passo é **instalar o Node**
(https://nodejs.org — versão LTS).

Sem instalar nada (dá para começar já):
- **Lighthouse** — já vem no **Google Chrome**: F12 → aba "Lighthouse" → marcar
  "Accessibility" → "Analyze". Dá nota e lista de problemas.
- **axe DevTools** — extensão gratuita do Chrome/Firefox: analisa a página e aponta
  falhas de acessibilidade com explicação.
- **NVDA** (grátis, Windows) — o teste que mais vale: navegar cada tela ouvindo.

Precisam de **Node.js** (instalar depois):
- **pa11y** / **pa11y-ci** — checagem de acessibilidade por linha de comando/CI.
- **@axe-core/cli** — axe automatizado em várias URLs.
- **Playwright** (`@playwright/test`) + **@axe-core/playwright** — testes ponta-a-ponta
  com verificação de acessibilidade embutida.
- **ESLint** — qualidade do JavaScript.

Já instalados no projeto (Python):
- **ruff** — lint do Python. Rodar: `venv\Scripts\python -m ruff check server engine`.
- **pytest-cov** — cobertura. Rodar:
  `venv\Scripts\python -m pytest --cov=server --cov=engine`.
- **pytest** — testes (45 passando).

## 🎯 Por onde eu sugiro começar (ordem)
1. **Auditoria de acessibilidade** (Lighthouse + axe no Chrome; NVDA em cada tela).
2. **Focus trap nos diálogos** e revisão de rótulos/ordem de Tab.
3. **Testes automáticos da camada web** (Flask test client) + **axe** nas telas.
4. **Histórico de mãos no banco** + **Perfil/Configurações**.
5. **Segurança**: CSRF + rate limiting; depois CI no GitHub.

> Este arquivo é um mapa vivo: à medida que cada item for feito, marco aqui e no
> `MUDANCAS.md`.
