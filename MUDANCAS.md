# 📋 Registro de Mudanças (para leigos)

Este arquivo explica, em linguagem simples, **tudo o que foi feito** no projeto e o
que muda a cada alteração. As mudanças mais **recentes ficam no topo**. Cada item
diz **o que mudou** e **para que serve**, sem termos técnicos.

> Como ler: pense em cada bloco como "uma novidade que entrou no jogo".

---

## 02/08/2026 — v0.33.1 · 🩹 Correção do deploy "Timed out" (conexão do banco com limite de tempo)

**O que mudou (em palavras simples):**

Os deploys no Render estavam falhando com **"Timed out"** (esgotou o tempo). O motivo:
quando o app subia, ele tentava conectar no banco de dados **sem limite de tempo** — se
o banco estivesse lento ou fora do ar, a conexão **travava por até 2 minutos**, e o
Render desistia da publicação.

- ⏱️ **Agora a conexão com o banco tem limite de 10 segundos.** Se o banco estiver lento,
  o app **sobe assim mesmo** (rápido) em vez de travar — e o deploy conclui. Também
  liguei um "keepalive" para não perder conexões ociosas.

Isso não muda nada visível no jogo; só faz a **publicação funcionar de forma confiável**.

---

## 02/08/2026 — v0.33.0 · 🎩 Nova identidade visual "Mesa de Veludo" (cassino de luxo)

**O que mudou (em palavras simples):**

Você escolheu a direção **"Mesa de Veludo"** (cassino elegante à noite). Apliquei essa
"cara" em **todas as telas de uma vez** (elas usam a mesma folha de estilo). Como você
é cego, aqui vai a descrição do que quem enxerga vê agora:

- 🟢 **Fundo verde-veludo bem escuro**, quase preto, com um leve brilho verde no topo —
  a sensação de feltro de mesa de poker num salão à meia-noite.
- 🟡 **Ouro nos detalhes:** o nome do site no topo, os títulos de destaque e o **botão
  principal** de cada tela ficam dourados (a cor da vitória e das fichas de alto valor).
- 📜 **Texto em creme/marfim** (não branco puro), suave como cartas de qualidade.
- ✒️ **Títulos com letra serifada elegante** (estilo placa de cassino / carta clássica);
  o texto comum continua numa letra limpa e larga, fácil de ler.
- 🃏 **A mesa de poker** ficou com o feltro verde mais rico, um **trilho de madeira
  escura com um fio de ouro** na borda, e o **verso das cartas** em verde com moldura
  de madeira (antes era azul).
- 🍷 **Botão de sair/perigo em vinho** (bordô) — sério, sem gritar. Botões de confirmar
  em verde.
- ☀️ **Modo claro** (para baixa visão) também no estilo: fundo **pergaminho creme**,
  verde e **ouro escuro** (para ler bem no claro).

Nada de funcionalidade mudou — é só a aparência. O **alto contraste** (preto e amarelo)
continua disponível em Configurações para quem precisar. **74 testes** seguem passando.

---

## 02/08/2026 — v0.32.0 · 🧹 Tela inicial enxuta (menu) com telas dedicadas

**O que mudou (em palavras simples):**

A tela inicial estava cheia de coisas ao mesmo tempo. Agora ela é um **menu limpo**, e
cada assunto tem a **sua própria tela** — mais fácil de percorrer no leitor de tela:

- 💼 **Tirei o bloco repetido de Carteira** do começo da tela inicial (a Carteira já
  fica no menu do topo).
- 🃏 **"Mesas" virou uma tela própria.** No início você clica em **Mesas** e cai numa
  página onde estão **Criar mesa** (com as configurações detalhadas só aqui), **Entrar
  em mesas em andamento** e **Restaurar** uma mesa em que você já está.
- 📣 **"Avisos" virou uma tela própria.** O quadro de avisos e a preferência de
  **"receber aviso quando alguém conecta"** saíram da tela inicial e agora ficam em
  **Avisos**.
- 👥 **"Amigos" virou uma tela própria** também (adicionar, ver quem está online e sua
  lista), para a tela inicial não ficar comprida.
- ⚙️ **Configurações** já está no menu do topo (desde a v0.30), com **som, volume e
  acessibilidade**.

Resumindo, a tela inicial agora mostra só os itens principais: **Mesas, Torneios,
Amigos e Avisos** (e Administração, se você for admin). Tudo o mais fica a um clique.

**Testado:** 74 testes automáticos passando (1 novo, conferindo o menu e as telas
dedicadas /mesas, /amigos e /avisos); revisão de código limpa.

---

## 02/08/2026 — v0.31.0 · 🎟️ Lista de espera no Cash Game + "Torneio da casa" com fila

**O que mudou (em palavras simples):**

Mais duas ideias do áudio-demo (o "Roadhouse Poker"), como você pediu:

- 🪑 **Sair da mesa de verdade (cash) + lista de espera.** Antes, "Abandonar" só te
  levava ao lobby, mas o **assento continuava ocupado**. Agora:
  - Ao sair de uma mesa de dinheiro, o assento é **liberado** e as **fichas voltam para
    a sua carteira**. Se você sair no meio de uma mão, a saída acontece **quando a mão
    termina** (o jogo avisa: "você sairá quando esta mão terminar").
  - Se uma mesa estiver **cheia**, no lobby aparece **"Entrar na lista de espera"**.
    Quando abrir uma vaga, quem está na fila **recebe um aviso** (texto e som) com um
    botão para entrar direto — "você será chamado quando houver vaga", como no demo.
- 🏆 **"Torneios da casa" com resumo e fila.** A lista de torneios agora mostra
  **entrada** (buy-in), **stack inicial**, **jogadores por mesa** e quantos já se
  inscreveram. E, ao entrar, o botão virou **"Entrar na fila do torneio"** — que
  primeiro mostra um **resumo para você confirmar** (entrada, fichas, jogadores e
  premiação) **antes** de descontar qualquer valor, exatamente como no demo.

**Testado:** 72 testes automáticos passando (4 novos, cobrindo sair-devolve-fichas,
a fila avisar quando abre vaga, sair da fila ao sentar, e o resumo do torneio); revisão
de código limpa.

---

## 01/08/2026 — v0.30.0 · ⚙️ Configurações organizadas, Acessibilidade e Jogo Responsável

**O que mudou (em palavras simples):**

Ouvi a sua demonstração (o áudio do "Roadhouse Poker") e trouxe **três ideias** dele
para o seu jogo — as que você escolheu:

- 🧭 **Central de Configurações organizada.** Agora existe uma página **Configurações**
  (link no topo do site) que agrupa tudo em 6 áreas claras, fáceis de percorrer no
  leitor de tela: **Acessibilidade**, **Jogo responsável**, **Ajuda e suporte**,
  **Privacidade**, **Termos e contratos** e **Segurança**. Cada área tem título,
  explicação e abre a sua própria página.
- ♿ **Central de Acessibilidade num lugar só.** Reuni o que estava espalhado —
  **anúncios das jogadas** (verbosidade), **sons e volume**, **zoom** e **aviso de
  conexão** — e acrescentei o **Alto contraste** (fundo preto com texto e links
  amarelos), que fica ligado em todas as telas até você desligar.
- 🧘 **Jogo Responsável (novo e funcional).** Ferramentas para jogar com equilíbrio:
  - **Lembrete de tempo de jogo:** você define depois de quantos minutos quer ser
    avisado; o jogo então fala "você está jogando há X minutos, que tal uma pausa?".
  - **Pausa temporária** (1 hora, 24 horas ou 7 dias) e **Autoexclusão** (30 ou 90
    dias): enquanto ativas, **bloqueiam entrar em mesas e torneios** (você continua
    entrando no site normalmente). Por segurança, uma pausa **só pode ser estendida,
    nunca encurtada** — e o **login nunca é bloqueado**, para você jamais ficar preso
    para fora. Há também um lembrete do **CVV 188** para quem precisar conversar.

**Sobre a verificação de identidade (selfie + RG) do demo:** ela lá é "um protótipo que
não salva imagens". Como capturar documentos/biometria de verdade é sensível, **não**
implementei essa parte — deixei registrado na página de Privacidade que esta fase não
coleta esses dados.

**Testado:** 69 testes automáticos passando (3 novos) + revisão de código limpa; abri as
páginas no navegador e confirmei que tudo funciona (o alto contraste aplica de verdade e
a pausa bloqueia a entrada em mesas). Guardei o resumo do áudio em `IDEIAS_DEMO_ROADHOUSE.md`.

---

## 01/08/2026 — v0.29.0 · 🗣️ Narração fala TODOS os jogadores e no modelo que você pediu

**O que mudou (em palavras simples):**

Na partida que você jogou, o jogo falava a sua ação e a de um adversário, mas **pulava
a de outro** (a da Carla). E você pediu que a narração fosse apresentada num **modelo**
bem específico. As duas coisas foram feitas:

- 🔊 **Agora fala a ação de TODO MUNDO da rodada — sem pular ninguém.** O motivo de
  algumas ações sumirem era técnico: quando vários jogadores agiam **em sequência bem
  rápida**, os avisos falados se **atropelavam** e o leitor de tela perdia alguns.
  Criei uma **fila de fala**: cada aviso entra na fila e é falado **um de cada vez**,
  com um tempinho entre eles. Assim **nenhuma ação é perdida**, não importa quantos
  jogadores ajam seguido.
- 📢 **A narração agora segue o modelo que você mandou.** Exemplos do que você ouve:
  - "**Rodada 282. Hapolo baralha as cartas e as distribui.**"
  - "**Hapolo paga a big blind (10 000).**" (quem pagou e quanto, com o número por extenso)
  - "**Rei de espadas e Ás de ouros em sua mão.**"
  - "**É a sua vez.**" / "**Vez de Hapolo.**"
  - "**Call (10 000).**" · "**Raise: 10 000.**" · "**All-in! (480 468)!**" · "Passou." · "Desistiu."
  - "**Flop: Ás de paus, 2 de copas e 6 de espadas.**" · "**Turn: 9 de paus.**" · "**River: 7 de copas.**"
  - No fim (quando há confronto): "**Você: par de Ases. com um rei de espadas e um ás
    de ouros**", "**Hapolo: …**", "**Você ganha o pote! (782 500)!**", "**Hapolo perdeu!**".
- 🔢 **Números grandes ficam fáceis de ouvir.** Valores como 480468 agora são falados
  como "**480 468**" (separados de mil em mil), em vez de um número corrido.
- 🙋 **Na sua vez e nas suas ações, fala "Você".** Quando é você quem ganha, ouve
  "Você ganha o pote"; e nas suas próprias jogadas o jogo **não repete o seu nome**.
- 🧰 **Ferramentas de teste organizadas (para desenvolvimento).** Criei um arquivo
  `requirements-dev.txt` que junta tudo o que é preciso para **rodar os testes e a
  revisão de código no PC** (pytest e ruff). Não muda nada no site — é só para
  facilitar conferir que nada quebrou antes de publicar. Confirmado: **66 testes
  passam** e a revisão de código está **limpa**.



**O que mudou (em palavras simples):**

Depois de publicar a atualização, alguns navegadores ficaram usando **arquivos
antigos guardados em cache** misturados com a página nova — e essa mistura **quebrava
o jogo** (cartas não faladas, atalhos sem efeito, botões novos parados). Corrigido:

- 🔄 **O navegador sempre pega a versão nova (cache-busting).** Agora cada arquivo do
  site leva uma "etiqueta de versão" que **muda a cada atualização**. Assim, ao
  recarregar, o navegador **baixa a versão nova** e para de misturar com a antiga.
  (Foi o que causou os problemas que você viu; agora não acontece mais.)
- 🚪 **Botão "Abandonar partida".** Faltava um botão visível para sair — agora tem, na
  barra da mesa (continua valendo a tecla **Q** também).
- 🗣️ **A "sua vez" não soletra mais as teclas.** Antes, ao chegar sua vez, o jogo lia
  "F desistir, C pagar, R aumentar…". Agora fala só as **ações e valores** ("você pode:
  desistir, pagar 79, aumentar, all-in") — as **letras das teclas** ficam no **F1**,
  como você pediu.

**Importante:** confirmei que o código já estava certo (cartas são faladas ao iniciar,
atalhos funcionam, o showdown diz o que cada um tinha) — o que atrapalhava era só o
**cache** do navegador. Depois desta atualização, um **Ctrl+F5** resolve de vez.

**Como foi garantido que não tem bug:** os **66 testes** passam e o **lint** está
limpo. No navegador, testei sentar → iniciar → jogar até o showdown: cartas faladas,
atalhos ativos, o novo aviso da vez sem as letras, o showdown dizendo as mãos, e o
botão Abandonar funcionando.

**Arquivos alterados:** `server/app.py` (versão dos estáticos), `web/templates/base.html`
e `web/templates/mesa.html` (etiqueta de versão + botão Abandonar), `web/static/poker.js`
(aviso da vez sem teclas + botão Abandonar).

---

## 29/07/2026 — v0.27.0 · 🛡️ Moderação: bloquear/silenciar e denunciar jogadores

**O que mudou (em palavras simples):**

- 🔇 **Bloquear (silenciar) alguém.** Na página **Perfil**, seção **Moderação**, você
  digita o apelido e bloqueia. A partir daí, essa pessoa **não consegue mais te mandar
  mensagens** — nem no bate-papo da mesa, nem no privado. **Ela não é avisada** de que
  foi bloqueada. Dá para **desbloquear** quando quiser (a lista fica ali).
- 🚨 **Denunciar um jogador.** Ainda no Perfil, você informa o **apelido** e o
  **motivo**. A denúncia vai para os **administradores** (e você fica **anônimo** para
  o denunciado). Os admins recebem um aviso de que chegou uma denúncia.
- 🧑‍⚖️ **Painel de denúncias (admin).** Na tela de **Administração** há uma lista das
  denúncias, com quem denunciou, quem foi denunciado, o motivo e a data — e um botão
  **"Marcar como resolvida"**.

**Como foi garantido que não tem bug:** os **66 testes** passam e o **lint** está
limpo (2 testes novos: um confere que a mensagem de quem foi bloqueado **não chega**
a quem bloqueou, mas chega aos outros; outro confere a denúncia + o admin vendo e
resolvendo). No navegador testei bloquear (aparece na lista com "Desbloquear"),
denunciar (o admin vê a denúncia e **marca como resolvida**) — **sem erros**.

**Arquivos alterados:** `server/db.py` (tabelas `bloqueios` e `denuncias`),
`server/social.py` (bloquear/denunciar/listar), `server/app.py` (entrega do chat
respeita bloqueio + novas rotas), `web/templates/perfil.html` (seção Moderação),
`web/templates/admin.html` (painel de denúncias), `tests/test_web.py`.

---

## 29/07/2026 — v0.26.0 · 🗣️ Verbosidade: você escolhe o quanto o jogo fala

**O que mudou (em palavras simples):**

Nem todo mundo quer ouvir **cada** açãozinha de cada jogador. Agora **você escolhe o
quanto o jogo fala**, em três níveis:

- **Completa** (padrão) — fala **tudo**, inclusive cada ação de cada jogador
  (passou, pagou, apostou…).
- **Média** — fala o **board** (flop/turn/river) e os **resultados**, mas **não** fica
  narrando cada ação dos outros. Menos "tagarelice", sem perder o importante.
- **Baixa** — fala **só os resultados** das mãos (e as suas cartas quando são
  distribuídas). O resto você pega nas teclas de sempre (D cartas, E flop, etc.).

Onde mudar: na mesa, a tecla **X** (ou o botão **"🗣️ Quanto fala"**) alterna na hora;
e na página **Perfil** há um seletor. A escolha fica **guardada**. Importante: a
**lista de narração na tela mostra tudo** — só a **fala** é que respeita o nível.

**Como foi garantido que não tem bug:** os **64 testes** passam e o **lint** está
limpo. No navegador, joguei mãos em cada nível: em **Média**, as ações dos jogadores
**não** foram faladas, mas board e resultado **sim**; em **Baixa**, só o resultado. A
tecla **X** alterna certinho e o seletor do Perfil **salva** a escolha — sem erros.

**Correção junto:** o script da página Perfil passou a rodar **depois** das
bibliotecas, senão alguns controles não ligavam (o seletor de verbosidade não salvava).

**Arquivos alterados:** `web/static/a11y.js` (controle de verbosidade guardado),
`web/static/poker.js` (fala filtrada + tecla X), `web/templates/mesa.html` (botão + F1),
`web/templates/perfil.html` (seletor + ordem do script).

---

## 29/07/2026 — v0.25.0 · 🤖 Integração Contínua (CI) + faxina no código (lint)

**O que mudou (em palavras simples):**

- 🤖 **Testes automáticos a cada envio (CI).** Configurei o **GitHub Actions**: toda
  vez que o código é enviado, o GitHub **roda sozinho os 64 testes e o lint**. Se algo
  quebrar, aparece um **X** e você é avisado — assim nada quebrado passa despercebido.
  (Vale para envios na `main` e para Pull Requests.)
- 🧹 **Faxina no código (lint).** Organizei a ordem dos `import`, tirei variáveis que
  não eram usadas e um nome de variável ambíguo. Criei uma **regra de lint** enxuta
  (`ruff.toml`) que aponta só o que importa (erros de verdade), sem barulho. Agora o
  lint passa **100% limpo**.

**Como foi garantido que não tem bug:** os **64 testes automáticos** continuam
passando e o **lint passa sem nenhum apontamento**. Rodei exatamente como a CI vai
rodar (`ruff check .` e `pytest -q`).

**O que você vai ver:** no GitHub, na aba **Actions**, um ✔️ verde quando tudo passa
(ou um ✖️ vermelho se algo falhar), a cada envio.

**Arquivos novos/alterados:** `.github/workflows/ci.yml` (novo — a automação),
`ruff.toml` (novo — regras de lint), e pequenas limpezas em `server/app.py`,
`server/social.py`, `server/mesa.py`, `engine/game.py`, `engine/evaluator.py` e testes.

---

## 29/07/2026 — v0.24.0 · 🔐 Segurança: anti-CSRF e trava contra força-bruta no login

**O que mudou (em palavras simples):**

- 🛡️ **Proteção contra CSRF.** CSRF é um golpe onde **outro site** tenta fazer uma
  ação em seu nome sem você saber (ex.: sacar da carteira). Agora **toda ação que
  muda algo** (entrar, sair, apostar, sacar, convidar…) só é aceita se vier **do
  próprio site**. Se vier de outro endereço, é **recusada**. Isso não muda nada para
  você — só bloqueia o golpe.
- 🔒 **Trava contra força-bruta no login.** Se alguém errar a senha **muitas vezes
  seguidas** (8 vezes em 5 minutos), o sistema **bloqueia novas tentativas por alguns
  minutos** e avisa "Muitas tentativas de login". Isso dificulta quem fica "chutando"
  senha. Ao acertar, o contador zera.

**Como foi garantido que não tem bug:** os **64 testes automáticos** passam (2 novos:
um confere que um pedido vindo de **outro site é barrado (erro de segurança)** e que o
do próprio site passa; outro confere que **depois de 8 erros o login trava**). Também
testei no site de verdade: as ações normais **continuam funcionando**, e no servidor
a 9ª tentativa de senha errada voltou **"bloqueado"** — como esperado.

**Ajuste fino (variáveis de ambiente):** `POKER_LOGIN_MAX` (padrão 8 tentativas) e
`POKER_LOGIN_JANELA` (padrão 300 segundos).

**Arquivos alterados:** `server/app.py` (checagem de origem em toda ação que muda
estado + limite de tentativas no login), `tests/test_web.py`.

---

## 29/07/2026 — v0.23.0 · 📚 Histórico de mãos no banco + Perfil e Configurações

**O que mudou (em palavras simples):**

- 📚 **Histórico de mãos guardado no banco.** Antes, o histórico das mãos (usado no
  relatório) ficava só **na memória** e **sumia se o servidor reiniciasse**. Agora
  **cada mão é gravada no banco de dados** (com as cartas, quem ganhou/perdeu e
  quanto). Isso não muda nada no seu jogo — é a base para as **estatísticas**.
- 👤 **Nova página "Perfil"** (link no topo do site). Mostra as suas **estatísticas
  de verdade**: **mãos jogadas**, **mãos ganhas**, **aproveitamento (%)**, saldo de
  fichas somado e o **maior pote** que você já ganhou.
- ⚙️ **Configurações num lugar só** (dentro do Perfil): **ligar/desligar os sons**,
  ajustar o **volume**, mudar o **zoom**, e ligar/desligar o **aviso de conexão**. E
  o melhor: as escolhas de **som e volume agora ficam guardadas** — quando você volta,
  continuam como você deixou.

**Como foi garantido que não tem bug:** os **62 testes automáticos** passam (2 novos:
um confere que a mão é **gravada no banco** e que as **estatísticas batem**; outro
abre a página de Perfil). No navegador, joguei uma mão e o Perfil mostrou os números
certos (1 mão jogada, 1 ganha, 100%, maior pote 100), e os controles de som/volume
**funcionam e ficam salvos** — **sem erros na tela**. O motor do jogo **não fala com
o banco** direto (usa um "recado"), então os testes do jogo seguem leves.

**Arquivos novos/alterados:** `server/historia.py` (novo — grava a mão e calcula as
estatísticas), `server/db.py` (tabelas `maos` e `mao_jogadores`), `server/mesa.py`
(manda o "recado" ao gravar a mão), `server/app.py` (liga o recado + rota
`/perfil`), `web/templates/perfil.html` (nova página), `web/templates/base.html`
(link Perfil), `web/static/sons.js` (som e volume guardados), `tests/test_web.py`.

---

## 29/07/2026 — v0.22.0 · ✅ Testes automáticos da camada web + correção (grátis)

**O que mudou (em palavras simples):**

- ✅ **Muito mais testes automáticos.** Antes, o "miolo" do jogo era bem testado,
  mas as **telas e ações da parte web** (login, criar/entrar em mesa, amigos, chat,
  avisos, convites, torneio) **não tinham teste automático**. Agora têm: **15 novos
  testes** que conferem essas rotas sem precisar abrir o navegador. Isso protege
  contra "consertar uma coisa e quebrar outra".
- 📈 **Cobertura de testes subiu de 44% para 66%.** (Os testes agora somam **60**.)
- 🐞 **Bug corrigido (achado pelos próprios testes):** uma **mesa ou torneio grátis
  (sem buy-in)** não deixava a pessoa entrar — o sistema tentava "cobrar zero" e dava
  erro. Agora, quando é grátis, ele **não cobra** e deixa entrar normalmente.

**Como foi garantido que não tem bug:** os **60 testes automáticos** passam. Os novos
usam o "cliente de teste" do Flask (roda tudo em memória, rápido). A correção do
buy-in grátis está coberta por teste (inscrever em torneio grátis agora funciona).

**Ferramentas:** medi a cobertura com `pytest-cov`. Áreas ainda com pouca cobertura
(anotadas no `MELHORIAS.md`): o motor do torneio multi-mesa e o envio de e-mail.

**Arquivos alterados/novos:** `tests/test_web.py` (novo — 15 testes de rota),
`server/app.py` (não cobra quando é grátis, na mesa e no torneio).

---

## 29/07/2026 — v0.21.0 · ♿ Foco preso nos diálogos (roadmap: acessibilidade)

**O que mudou (em palavras simples):**

Começando o roadmap pela **acessibilidade**: agora, quando uma **janela (diálogo)**
abre — relatório, convite, buy-in, rebuy, add-on, "sair" — o **teclado fica preso
dentro dela**. Antes, apertando **Tab** o foco podia "escapar" para a página atrás da
janela (o leitor de tela começava a ler coisas de trás), o que confundia. Agora:

- 🔒 **Tab** e **Shift+Tab** circulam **só entre os botões e campos da janela aberta**.
- 🔁 Ao chegar no último e apertar Tab, volta para o primeiro (e vice-versa).
- ↩️ Se por algum motivo o foco estava fora, o Tab **traz de volta** para dentro da
  janela.
- Vale para **todas** as janelas, inclusive a de convite que aparece sozinha.

**Como foi garantido que não tem bug:** os **45 testes automáticos** seguem passando.
No navegador testei com a janela de relatório (8 campos/botões): **Tab no último volta
ao primeiro**, **Shift+Tab no primeiro vai ao último**, e **foco de fora entra na
janela** — e, **sem** janela aberta, o Tab continua **normal**. Sem erros na tela.

**Arquivos alterados:** `web/static/a11y.js` (o "focus trap" — vale para todas as
telas, já que esse arquivo é carregado em todas).

---

## 29/07/2026 — v0.20.0 · 🔊 Sons completos e personalizáveis + roadmap profissional

**O que mudou (em palavras simples):**

- 🔊 **Sons distintos para cada coisa.** Antes, várias ações usavam o mesmo som (o
  bate-papo, a conexão, o convite, o "copiado"…). Agora **cada uma tem o seu**:
  mensagem pública, **mensagem privada**, alguém **conectou**, **aviso** da
  plataforma, **convite**, **novo amigo**, **copiado**, **e-mail enviado**, **nova
  mão** (embaralhar), **carta virando na mesa**, **rebuy**, **add-on** e mais. No
  total são **30 sons**.
- 🎚️ **Você pode trocar por sons seus.** É só colocar um arquivo **MP3** na pasta
  `web/static/sons/` com o nome certo (ex.: `foldar.mp3`). O jogo passa a usar o seu.
  Se tirar o arquivo, volta ao som automático. A **lista completa** de nomes e o que
  cada um faz está no novo arquivo **SONS.md** (e um resumo em `web/static/sons/
  LEIA-ME.txt`).
- 🗺️ **Mapa de melhorias (roadmap).** Criei o **MELHORIAS.md**: um checklist do que
  falta para a plataforma ficar profissional e inclusiva — acessibilidade, layout,
  tela inicial, seções novas, regras de jogo, social, torneios, segurança e testes —
  com **o caminho de cada um** e as **ferramentas para validar** (e quais dependem de
  instalar o Node.js).

**Como foi garantido que não tem bug:** os **45 testes automáticos** seguem passando.
No navegador confirmei que os **30 sons** carregam, tocam **sem erro**, e que a busca
por MP3 personalizado (quando não existe arquivo) **não gera erro** na tela. Também
rodei um diagnóstico de qualidade: **cobertura de testes 44%** e **44 apontamentos de
lint** — tudo anotado no roadmap com o que fazer.

**Ferramentas instaladas para validação (Python):** `ruff` (lint) e `pytest-cov`
(cobertura de testes).

**Arquivos alterados/novos:** `web/static/sons.js` (30 sons + troca por MP3),
`web/static/poker.js` e `web/static/notificacoes.js` (usam os novos sons),
`web/static/sons/LEIA-ME.txt` (novo), `SONS.md` (novo — catálogo), `MELHORIAS.md`
(novo — roadmap).

---

## 29/07/2026 — v0.19.0 · 🏆 Convite de torneio por e-mail e início mais limpo

**O que mudou (em palavras simples):**

- 🏆 **Convidar amigos para o torneio.** Na página de um torneio há **"Convidar
  amigos"**: um botão **convida todos os seus amigos de uma vez**, ou você **digita um
  apelido ou e-mail**. Cada convidado recebe um **e-mail com o link** para aceitar e
  se inscrever, e — se estiver online — uma **janela** abre na tela dele perguntando
  se quer participar.
- 🧹 **Início (home) mais limpo.** As seções **Ajuda**, **Criar mesa** e **Amigos**
  agora ficam **recolhidas**: aparecem como títulos e só **abrem quando você clica**.
  Assim a tela inicial fica enxuta, com as opções aparecendo só dentro de cada uma.

**Como foi garantido que não tem bug:** os **45 testes automáticos** seguem passando.
Testei o convite de torneio **com duas contas**: convidar por apelido e **convidar
todos os amigos** funcionaram; o convidado **recebeu o aviso com o link do torneio**
(e, com e-mail ligado no servidor, receberia por e-mail). E confirmei no navegador
que a home ficou com as seções **recolhidas** e que tudo continua funcionando, **sem
erros na tela**.

**Arquivos alterados:** `server/app.py` (rota de convite de torneio),
`server/mailer.py` (e-mail de convite com link), `server/social.py` (e-mail por
apelido), `web/static/notificacoes.js` (janela também para convite de torneio),
`web/templates/torneio.html` (seção Convidar amigos), `web/templates/lobby.html`
(seções recolhidas).

---

## 29/07/2026 — v0.18.0 · ♿ Ajustes de acessibilidade, amigos online e chat melhorado

**O que mudou (em palavras simples):**

- 🃏 **As cartas não são mais repetidas a cada jogada.** Antes, ao passar (check) ou
  pagar (call), o jogo repetia suas cartas. Agora suas cartas são faladas **só quando
  você as recebe** e quando você aperta **D** para ouvi-las.
- 🗣️ **Ajuda (F1) mais clara.** Cada linha agora tem a **tecla**, depois **dois
  pontos**, e então **o que ela faz** (ex.: *"F: Desistir"*). E a lista virou **uma
  coluna, um item por linha**, para ler direitinho com as setas do leitor de tela.
- 📨 **Convite abre uma janela perguntando.** Quando alguém te convida para uma mesa,
  agora **abre automaticamente uma janela** com **"Aceitar e entrar"** ou **"Agora
  não"** — em qualquer tela. (Antes só avisava por som/texto e podia passar batido.)
- 👥 **Adicionar amigos ficou fácil.** Na seção Amigos há **"Mostrar todos online"**:
  aparece a lista de quem está online (**amigos primeiro**, depois em ordem
  alfabética) com **caixinhas** para você **marcar várias pessoas e adicionar todas de
  uma vez**. Continua dando para adicionar pelo apelido também.
- 💬 **Bate-papo melhor.** No "Enviar para" você escolhe **Todos na mesa (sala em
  andamento)** ou uma **pessoa específica** — a lista mostra **só quem está online**,
  **amigos primeiro**. Também dá para **digitar um apelido ou e-mail** e mandar
  **privado para qualquer pessoa online**, mesmo que ela esteja em outra tela (ela
  recebe o aviso). E dá para **navegar pelo histórico** de mensagens: no campo de
  mensagem, aperte **seta para cima** para ler o que foi enviado e recebido.

**Como foi garantido que não tem bug:** os **45 testes automáticos** seguem passando.
Testei **com três contas**: a lista de online veio com **amigos primeiro**; a adição
**de várias pessoas de uma vez** funcionou; o **PV por e-mail** para alguém em outra
tela chegou como aviso; o **convite abriu a janela sozinho**; e as **cartas não se
repetem** ao passar/pagar (mas voltam a ser faladas em nova mão e no botão D) — tudo
**sem erros na tela**.

**Arquivos alterados:** `server/app.py` (online, adicionar vários, PV para quem está
online), `server/social.py` (lista de online amigos-primeiro, resolver por apelido/
e-mail), `web/static/notificacoes.js` (janela de convite + PV recebido), `web/static/
poker.js` (cartas sem repetir, chat com online e histórico), `web/templates/mesa.html`
(F1 com dois-pontos, chat), `web/templates/lobby.html` (amigos online),
`web/static/app.css` (ajuda em uma coluna, item por linha).

---

## 29/07/2026 — v0.17.0 · 🔒 Segurança: sessão expira e sai ao fechar o navegador

**O que mudou (em palavras simples):**

Antes, o login **ficava valendo para sempre** — mesmo fechando o navegador a pessoa
continuava logada. Isso é ruim para a segurança. Agora:

- 🚪 **Fechou o navegador, saiu.** O cookie de login virou um **cookie de sessão**:
  o navegador o **apaga ao ser fechado**, então a pessoa precisa entrar de novo.
- ⏲️ **Expira por inatividade.** No servidor, a sessão vale por um tempo de
  **inatividade (2 horas por padrão)**. Enquanto você usa o site, ela se **renova
  sozinha**; depois de ficar todo esse tempo sem uso, ela **expira** e pede login —
  mesmo que o navegador tente lembrar o cookie.
- 🛡️ **Cookie mais protegido.** Marcado como **HttpOnly** (o JavaScript da página não
  lê o cookie — protege contra roubo por scripts), **SameSite=Lax** (não vaza para
  outros sites) e **Secure** em produção (só trafega por HTTPS).

**Como foi garantido que não tem bug:** os **45 testes automáticos** seguem
passando. Testei direto no servidor: uma sessão nova **funciona**; uma sessão
**vencida é recusada e apagada** do banco; e uma sessão **antiga (de antes desta
mudança) também é recusada**, pedindo login de novo. O banco ganha a coluna de
expiração automaticamente, sem perder nada.

**Ajuste fino:** dá para mudar o tempo com a variável `POKER_SESSAO_HORAS` (ex.: 1,
2, 4). O padrão é 2 horas.

**Arquivos alterados:** `server/app.py` (flags de segurança do cookie),
`server/auth.py` (criar/validar sessão com expiração e renovação),
`server/db.py` (coluna `expira_em` em `sessoes`, com migração para bancos já
existentes).

---

## 29/07/2026 — v0.16.0 · 🏠 Home enxuta, seção de mesas e F1 por botão — Fase 6

**O que mudou (em palavras simples):**

- 🏠 **Início mais enxuto.** A tela inicial ficou limpa. O **saldo, depósito e saque
  saíram da home** e ficam só na **Carteira** (link no topo), como você pediu.
- 🎲 **Seção "Mesas" organizada em três opções:**
  - **➕ Criar mesa** — as configurações detalhadas ficam **escondidas** e só
    aparecem quando você **abre** "Criar mesa" (fica mais simples de navegar).
  - **🔄 Restaurar mesa** — lista as mesas em que **você já está sentado**, para
    **voltar** com um clique.
  - **▶️ Entrar em mesas em andamento** — as outras mesas abertas.
- ❓ **Ajuda na home.** Um bloco "Ajuda: o que dá para fazer aqui" explica cada parte.
- ⌨️ **Atalho em todos os botões.** O único que faltava — **Sentar e comprar fichas**
  — ganhou a tecla **U**.
- 🗣️ **F1 fala a função de cada botão.** Na mesa, o **F1** agora tem uma seção **"O
  que faz cada botão da barra do topo"**, descrevendo botão por botão (e ao abrir, o
  jogo avisa que é o guia de botões e atalhos).

**Como foi garantido que não tem bug:** os **45 testes automáticos** seguem
passando. No navegador confirmei: a home sem o saldo (isolado na carteira), o "Criar
mesa" **recolhido** por padrão (e o formulário ainda cria a mesa normalmente), a
seção **Restaurar** mostrando a minha mesa e **Entrar em andamento** mostrando as
outras, o **F1** com a descrição de cada botão, e a tecla **U** abrindo o "sentar" —
tudo **sem erros na tela**.

**Arquivos alterados:** `server/app.py` (marca "minha" em cada mesa),
`web/templates/lobby.html` (home + seção de mesas), `web/templates/mesa.html` (F1 por
botão + dica no Sentar), `web/static/poker.js` (tecla U e aviso ao abrir a ajuda).

Com esta fase, **todo o plano de melhorias combinado foi concluído** (Fases 1 a 6).

---

## 29/07/2026 — v0.15.0 · 🔍 Zoom para baixa visão e celular — Fase 5

**O que mudou (em palavras simples):**

- 🔍 **Zoom (baixa visão).** Um botão **"🔍 Zoom"** no topo (em todas as telas) que
  gira entre **Normal → Grande → Gigante**, ampliando **tudo**: textos, **cartas** e
  **botões**. Na mesa, dá para usar a tecla **Z**. A escolha fica **guardada** no
  navegador — quando você volta, continua no tamanho que preferiu.
- 📱 **Celular.** O jogo agora se **ajusta ao tamanho do telefone**: nada de barra de
  rolagem para os lados, botões grandes e fáceis de tocar, cartas e mesa no tamanho
  certo. E os **atalhos continuam funcionando** — no celular, cada atalho também é um
  **botão na tela**, então dá para jogar dos dois jeitos.
- 🤝 **Mesmo visual para todos.** A tela é a mesma para quem enxerga e para quem usa
  leitor de tela — é só o jogo, sem "cara" de limitação.

**Como foi garantido que não tem bug:** os **45 testes automáticos** seguem
passando. No navegador testei o zoom (gira os três tamanhos, aplica de verdade —
inclusive nas cartas e botões — e **continua guardado depois de recarregar**), a
tecla **Z** na mesa, e o **modo celular** (largura de telefone) confirmando que
**não há rolagem horizontal** e que as cartas e controles se ajustam — **sem erros na
tela**.

**Arquivos alterados:** `web/static/app.css` (zoom + regras de celular),
`web/static/zoom.js` (novo — controle de zoom guardado), `web/templates/base.html`
(botão de zoom no topo), `web/static/poker.js` (tecla Z), `web/templates/mesa.html`
(ajuda F1).

---

## 28/07/2026 — v0.14.0 · 📣 Aviso de conexão e quadro de avisos — Fase 4

**O que mudou (em palavras simples):**

- 🟢 **Aviso quando alguém conecta.** Quando um jogador entra na plataforma, quem
  está online **ouve e vê** um aviso (ex.: *"Bruno entrou na plataforma."*). Dá para
  **ligar ou desligar** isso na sua preferência (no lobby, em "Preferências de
  aviso") — e a escolha fica **guardada**.
- 📌 **Quadro de avisos.** Uma seção no lobby mostra os **comunicados da plataforma**
  (ex.: *"Hoje 20h tem torneio do Fulano"*). Toda vez que você conecta, os avisos
  ativos são **falados** para você.
- 🙅 **Não receber mais.** Cada aviso tem o botão **"Não receber mais este aviso"** —
  ele some só para você (se já está esperando o torneio, por exemplo).
- 🛠️ **Publicar e dar baixa.** O **administrador** publica um aviso pelo lobby; quem
  criou (ou um admin) pode **"Dar baixa"** para removê-lo **para todos** (por exemplo,
  quando o torneio começa).

**Como foi garantido que não tem bug:** os **45 testes automáticos** seguem
passando; testei **com duas contas** que quem está online **recebe o aviso de
conexão** de quem acabou de entrar; que o **liga/desliga** é respeitado e guardado;
e o quadro de avisos completo — admin **publica**, o outro **vê e dispensa só para
si**, e a **baixa** remove para todos. No navegador confirmei o formulário do admin,
a lista com os botões certos e o **aviso de conexão sendo falado**, **sem erros na
tela**.

**Arquivos alterados:** `server/db.py` (tabelas `preferencias` e `avisos`),
`server/social.py` (presença por heartbeat, preferências, avisos), `server/app.py`
(rotas de avisos/preferência + heartbeat no polling), `server/auth.py` (sessão passa
a incluir se é admin), `web/static/notificacoes.js` (sons de conexão/aviso),
`web/templates/lobby.html` (quadro de avisos + preferência).

---

## 28/07/2026 — v0.13.0 · 👥 Amigos e convites para a mesa — Fase 3

**O que mudou (em palavras simples):**

Agora dá para ter uma **lista de amigos** e **convidar** gente para cair direto na
sua mesa.

- 🧑‍🤝‍🧑 **Amigos (no lobby).** Uma seção "Amigos": você digita o **apelido** da pessoa
  e clica **Adicionar amigo**; a amizade vale para os dois lados. Cada amigo aparece
  na sua lista com um botão **Remover**. Tudo com aviso falado.
- 🔔 **Avisos que chegam em qualquer tela.** O sistema passou a ter **notificações**:
  de tempos em tempos o jogo verifica se há algo novo para você e **fala** (por
  exemplo, quando alguém te adiciona como amigo, ou te convida para uma mesa).
- ➕ **Convidar para a mesa (tecla N).** Estando em uma mesa, aperte **N** (ou o botão
  **"➕ Convidar para a mesa"**). Escolha um **amigo** na lista ou **digite o apelido**
  e clique **Convidar** — com aviso de que o convite foi enviado.
- 🎟️ **Aceitar convite (tecla F2).** Quem é convidado **ouve o convite em qualquer
  tela** e aperta **F2** para **entrar direto** na mesa de quem convidou. Simples
  assim.

**Como foi garantido que não tem bug:** os **45 testes automáticos** seguem
passando; testei os amigos (adicionar vira mútuo; apelido inexistente e "você mesmo"
são recusados; remover apaga dos dois lados; a pessoa recebe o aviso "novo amigo") e
o convite **com duas contas**: uma convidou pela mesa e a outra **recebeu o aviso
falado em outra tela e entrou com F2 na mesa certa** — tudo **sem erros na tela**.

**Arquivos novos/alterados:** `server/social.py` (novo — amigos, convites,
notificações), `server/db.py` (tabela `amizades`), `server/app.py` (rotas de amigos,
notificações e convite), `web/static/notificacoes.js` (novo — avisos em todas as
telas + F2), `web/templates/base.html` (carrega os avisos), `web/templates/lobby.html`
(seção Amigos), `web/templates/mesa.html` (botão e diálogo de convite),
`web/static/poker.js` (tecla N e envio do convite).

---

## 28/07/2026 — v0.12.0 · 💬 Bate-papo acessível com conversa privada — Fase 2

**O que mudou (em palavras simples):**

Agora dá para **conversar na mesa**, e o jogo **fala as mensagens** conforme elas
chegam.

- 🗣️ **Bate-papo na mesa.** Um painel com o histórico das mensagens, um campo para
  escrever e o botão **Enviar**. Aperte **Enter** para mandar.
- ⌨️ **Tecla B** leva você direto para o campo de mensagem (de "bate-papo"). Ao abrir,
  o jogo explica como usar.
- 🔊 **As mensagens são verbalizadas ao chegar.** Quando alguém escreve, você ouve
  *"Fulano disse: ..."*. Um somzinho curto avisa que chegou mensagem.
- 🤫 **Conversa privada (PV).** No campo **"Enviar para"** você escolhe **Todos na
  mesa** ou **uma pessoa específica**. A mensagem privada só chega para você e para
  ela, e é anunciada como *"Fulano te mandou no privado: ..."*. (Robôs não aparecem
  como opção.)
- ✅ **Feedback ao enviar:** o jogo confirma **"Mensagem enviada"** (ou **"Mensagem
  privada enviada para Fulano"**), e avisa se não deu certo.
- 👀 A lista de pessoas para PV **se atualiza** quando alguém novo senta na mesa.

**Como foi garantido que não tem bug:** os **45 testes automáticos** seguem
passando; a lógica de entrega foi testada (mensagem pública chega a todos; a
privada só ao remetente e ao destinatário; robô/ausente é recusado). E foi testado
**com duas pessoas de verdade ao mesmo tempo**: uma no navegador e outra por uma
conexão separada — a pública e a privada chegaram certinhas dos dois lados, com o
foco pela tecla B, o Enter e o feedback funcionando, **sem erros na tela**.

**Arquivos alterados:** `server/app.py` (entrega do chat + PV, avisa a mesa quando
alguém senta), `web/templates/mesa.html` (painel de bate-papo), `web/static/poker.js`
(tecla B, envio, recebimento falado, lista de PV, feedback).

---

## 28/07/2026 — v0.11.0 · 📄 Relatório de rodadas (com as cartas) — Fase 1

**O que mudou (em palavras simples):**

Agora o jogo **guarda um histórico de cada mão** (com as cartas de cada jogador, as
cartas da mesa e quem ganhou/perdeu) e monta um **relatório rodada‑a‑rodada** para
você.

- 🏁 **Aparece sozinho quando você perde o jogo.** Ao ficar sem fichas, o jogo avisa
  e abre o relatório. Você também pode abrir a qualquer momento com a tecla **J** ou
  o botão **"📄 Relatório de rodadas"**.
- 🧾 **O que o relatório mostra:** quantas rodadas você jogou, **quais você ganhou**
  (com quanto ganhou, **com quais cartas** e qual foi a mão) e **quais você perdeu**
  (com as cartas), e em **qual rodada você perdeu o jogo**. Exemplo de linha:
  *"Rodada 1: ganhou 122 fichas com 7 de copas e 4 de copas. Mão: Trinca de 4."*
- 👤 **De quem é o relatório:** você escolhe **só o seu**, **de pessoas que você
  selecionar**, ou **de todos que jogaram**. (Os robôs não entram.)
- 📋 **Botão Copiar** — copia tudo para a área de transferência, com aviso falado
  **"Copiado!"**.
- ✉️ **Botão Enviar por e‑mail** — manda o relatório para o seu e‑mail, com aviso
  falado se **deu certo** ou não.
- ⎋ **Escape** fecha o relatório; enquanto ele está aberto, as teclas de jogo ficam
  desativadas para não atrapalhar.

**Como foi garantido que não tem bug:** os **45 testes automáticos** seguem
passando; o relatório foi gerado em teste (mostrando corretamente as rodadas
ganhas/perdidas com as cartas e o valor **líquido** de cada rodada) e o fluxo foi
aberto no navegador — abrir com J, trocar "de quem é o relatório", **Copiar**
(confirmou "Copiado!"), **Enviar por e‑mail** (deu o aviso certo) e **Escape** para
fechar — **sem erros na tela**.

**Arquivos alterados:** `server/mesa.py` (histórico + relatório), `server/app.py`
(novas rotas), `server/mailer.py` (envio do relatório), `web/templates/mesa.html`
(diálogo do relatório), `web/static/poker.js` (tecla J, botões e feedback).

---

## 28/07/2026 — v0.10.0 · 🎯 Chance de vencer, volume, fold automático e big blind ante

**O que mudou (em palavras simples):**

- 🎯 **"Chance de vencer" (tecla O).** A qualquer momento da mão você aperta **O** e
  o jogo fala, por exemplo, **"13 por cento de chance de vencer"**. Ele usa o
  cálculo oficial de força das mãos do pôquer e considera **quantas pessoas ainda
  estão na disputa** e as cartas que já estão na mesa (pré-flop, flop, turn e
  river). Também há um botão **"📊 Chance de vencer"** na barra da mesa.
- 🔉 **Controle de volume dos sons.** Aperte **vírgula** para diminuir e **ponto**
  para aumentar; o jogo fala o novo volume em porcentagem e toca um bipe de teste.
  Também há os botões **"Volume −"** e **"Volume +"**.
- 🤖 **Fold automático (tecla K).** Se você não quer atrapalhar o ritmo da mesa,
  liga o fold automático: na sua vez o jogo **passa sozinho** quando é de graça, ou
  **desiste** quando há aposta para pagar. Aperte **K** de novo para desligar.
  Também há o botão **"☐ Fold automático"**.
- 🃏 **Big blind ante (liga/desliga na criação da mesa).** Um formato moderno de
  torneio: em vez de cada jogador pagar um ante separado, **só o jogador do big
  blind paga um ante** (do tamanho do big blind) pela mesa toda. Isso engorda o pote
  e deixa o jogo mais agressivo, sem atrasar as rodadas. Escolhe-se ao **criar a
  mesa**, no campo "Big blind ante".
- ⌨️ **Enter para entrar.** Na tela de login, ao digitar a senha e apertar **Enter**,
  o botão **"Entrar"** é acionado automaticamente (já funcionava, agora confirmado).
- ❓ **Ajuda (F1) atualizada** com as novas teclas: **O** (chance), **K** (fold
  automático), **vírgula/ponto** (volume), além de uma seção "Preferências".

**Como foi garantido que não tem bug:** os **45 testes automáticos** continuam
passando. Além disso, foi testado que o big blind ante **não faz ficha sumir nem
aparecer** (o dinheiro na mesa se conserva) e que o ante **não altera o valor que
você precisa pagar** para continuar na mão. A "chance de vencer" foi conferida com
mãos conhecidas (mão fraca dá porcentagem baixa; mão forte, alta). Tudo isso também
foi aberto no navegador para confirmar os botões, o painel de ajuda e que **não há
erros na tela**.

**Arquivos alterados:** `engine/game.py` (big blind ante), `engine/evaluator.py`
(cálculo de chance), `server/mesa.py`, `server/app.py`, `web/static/poker.js`,
`web/static/sons.js`, `web/templates/mesa.html`, `web/templates/lobby.html`.

---

## 28/07/2026 — v0.9.0 · 🏆 Torneio multi-mesa (MTT) de verdade

**O que mudou (em palavras simples):**

Um sistema completo de **torneio com várias mesas**, como nos jogos oficiais:
- 👥 **Número de participantes configurável.** As pessoas reais que entrarem ocupam
  vagas e o **resto é preenchido com bots** até o número escolhido (para o torneio
  rodar mesmo com poucos testadores).
- 🎲 Ao iniciar, os jogadores são **distribuídos aleatoriamente** em mesas de **9**.
- 🎚️ **Stack inicial** (fichas por jogador) e **buy-in** configuráveis.
- 🔁 **Rebuy (recompra):** quem zera as fichas nos primeiros níveis pode recomprar
  (bots recompram sozinhos; humanos recebem uma pergunta na tela).
- ➕ **Add-on:** no fim do período de rebuy há um **intervalo** com fichas extras
  por um valor (bots fazem sozinhos; humanos recebem a oferta).
- 🔀 **Reposicionamento (balanceamento):** conforme os jogadores são eliminados, as
  mesas são **equilibradas e quebradas**, juntando os jogadores até a **mesa final**
  — igual a torneios oficiais. Quem é movido é avisado e levado à nova mesa.
- 🥇 **Premiação** paga o **top ~15%**, com estrutura decrescente.
- 🕒 **Blinds sincronizados** entre todas as mesas.

**Como usar:** no lobby, o link **🏆 Torneios**. O admin cria o torneio, as pessoas
se inscrevem, o admin aperta "Iniciar", e cada um é levado à sua mesa.

**Testado:** simulações completas (18 jogadores → 2 mesas → 1 mesa final, 18
colocações, prêmios; rebuy e add-on funcionando) e o fluxo no navegador (criar,
inscrever, iniciar, jogar) sem erros.

**Arquivos novos/alterados:** `server/mtt.py` (novo), `engine/torneio.py`,
`server/mesa.py`, `server/app.py`, `web/templates/torneios.html` (novo),
`web/templates/torneio.html` (novo), `web/templates/mesa.html`,
`web/templates/lobby.html`, `web/static/poker.js`.

---

## 28/07/2026 — v0.8.0 · Configurações de mesa + narração de board e showdown

**O que mudou (em palavras simples):**

Na **criação da mesa** agora dá para configurar:
- **Small blind** e **Big blind** (deixar vazio usa o padrão do modo).
- **Velocidade de aumento dos blinds** no torneio (Turbo/Rápido/Médio/Lento).
- **Próximas rodadas:** automáticas (começam sozinhas) ou manuais (barra de espaço).
- **Ao terminar o torneio:** fechar a mesa (não fica aberta) ou reiniciar. E mesas
  abandonadas (sem ninguém) são removidas sozinhas, para não acumular.

No **cash game**, ao sentar, o jogador **escolhe quanto trazer** para a mesa (buy-in).

**Acessibilidade da mão:**
- 🔊 O **flop, o turn e o river são falados automaticamente** quando aparecem (o turn
  e o river dizem só a carta nova). A tecla **E** continua funcionando para repetir.
- 🏆 No **fim da rodada**, o leitor fala a **combinação e as cartas de cada envolvido**,
  ex.: *"Ana leva o pote com dois pares, Rei e 6, tendo 9 de paus e 6 de espadas.
  ConfigTest tinha par de Rei com 7 de paus e 2 de espadas."*

**Testado no navegador:** auto-início, diálogo de buy-in, blinds customizados,
board automático e showdown — tudo funcionando, sem erros.

**Arquivos:** `server/mesa.py`, `server/app.py`, `engine/game.py`,
`web/templates/lobby.html`, `web/templates/mesa.html`, `web/static/poker.js`.

---

## 28/07/2026 — v0.7.2 · Aviso de tempo: aos 5s (e aos 3s no timer de 7s)

**O que mudou (em palavras simples):**

- O aviso de "tempo acabando" agora toca **aos 5 segundos** restantes (antes era aos
  10). No timer **curto de 7 segundos**, o aviso vem aos **3 segundos**.
- O som do aviso agora é **curto e tenso** ("aterrorizante") em vez do bipe de erro.

**Testado:** com o timer de 7s, o aviso "Atenção: 3 segundos para agir" disparou no
momento certo, com o som novo.

**Arquivos:** `web/static/poker.js`, `web/static/sons.js`.

---

## 28/07/2026 — v0.7.1 · Sons de eliminação + mais opções de tempo

**O que mudou (em palavras simples):**

- 📢 **Vaia** quando um jogador **perde todas as fichas** — todos na mesa ouvem.
- 👏 **Aplauso** para o jogador que **eliminou** o outro (só ele ouve o aplauso).
  Junto, o leitor de tela anuncia "Fulano perdeu todas as fichas, eliminado por Ciclano".
- ⏱️ Novas opções de **tempo por ação** na criação da mesa: **7, 10, 15 e 20
  segundos** (além de 30, 45, 60 e sem timer).
- 🔧 Correção: os sons/avisos de **fim de mão** e **fim de torneio** (vitória,
  derrota) agora disparam de forma confiável (um campo de evento estava
  inconsistente).

**Arquivos:** `web/static/sons.js`, `web/static/poker.js`, `server/mesa.py`,
`web/templates/lobby.html`.

---

## 28/07/2026 — v0.7.0 · Mapa completo de atalhos na mesa + admin excluir usuário

**O que mudou (em palavras simples):**

Conjunto completo de **atalhos de teclado** na mesa, para jogar de ouvido:

*Ações:* `F` desistir · `C` pagar/passar · `R` apostar/aumentar (abre o campo já
com o valor mínimo; ao digitar, limpa e fica só o que você digitou) · `A` all-in ·
`Enter` confirma a aposta · `Espaço` inicia a mão · `Q` abandonar (pergunta antes).

*Informações faladas:* `D` minhas cartas · `G` minha melhor combinação (ou "Nada")
· `E` o flop · `P` fichas no pote · `V` quanto pagar para entrar · `I` quanto
investi na rodada · `S` meu stack · `Shift+S` stacks de todos (do maior ao menor) ·
`H` quantos/quais jogadores na disputa · `W` nomes na mesa · `Shift+W` participantes
do torneio · `T` de quem é a vez · `L` tempo para subir os blinds · `M` sons.

- 🆘 **`F1` abre a ajuda** listando todos os atalhos e o que cada um faz.
- 🗑️ **Painel de admin:** botão **"Excluir"** em cada usuário (com confirmação),
  para remover contas de teste e moderar testadores. Não dá para excluir a si mesmo.

**Arquivos:** `web/static/poker.js`, `web/templates/mesa.html`, `engine/evaluator.py`
(descrever_melhor), `engine/game.py`, `server/auth.py`, `server/app.py`,
`web/templates/admin.html`.

---

## 27/07/2026 — v0.6.3 · Carteira: confirmação, aviso falado e sons de caixa

**O que mudou (em palavras simples):**

- 💰 **Tela de confirmação** no depósito e no saque: antes de executar, aparece
  "Você está prestes a depositar/sacar R$ X. Confirmar?", o foco vai para lá e o
  leitor de tela fala a pergunta. Só executa se você confirmar (segurança na área
  financeira).
- 🔊 **Mensagem de sucesso falada**, no formato pedido:
  "Você sacou o total de R$ 1.500,00. Seu saldo atual é de R$ 400,00." (idem para
  depósito).
- 🛎️ **Sons de caixa registradora distintos:** um som para **depósito** (dinheiro
  entrando, tom que sobe) e outro para **saque** (dinheiro saindo, gaveta + tom que
  desce). Assim dá para diferenciar de ouvido.
- O extrato passa a mostrar a nova transação **na hora**, sem recarregar a página.

**Sobre os títulos das telas (Insert+T):** já estavam prontos — cada tela tem seu
título (Carteira, Lobby, Mesa, etc.), então o NVDA já fala o nome com Insert+T.

**Arquivos alterados:** `web/templates/carteira.html`, `web/static/sons.js`,
`server/app.py`.

---

## 27/07/2026 — v0.6.2 · Acessibilidade: foco e aviso ao carregar cada tela

**O que mudou (em palavras simples):**

- 🔊 **Aviso "Página carregada"** toda vez que você abre ou muda de tela — o leitor
  de tela avisa que a nova página foi carregada.
- 🎯 **Foco automático no primeiro componente** (o título principal) ao abrir cada
  tela — assim o leitor de tela já começa a ler do início, com contexto, sem você
  precisar procurar onde está.
- Vale para todas as páginas (entrar, lobby, mesa, carteira, verificar, admin).

**Arquivo alterado:** `web/static/a11y.js`.

---

## 27/07/2026 — v0.6.1 · ✅ E-mail de verificação FUNCIONANDO (plano pago)

**O que mudou (em palavras simples):**

- 🎉 **O e-mail de verificação anti-bot está funcionando de verdade!** Os testadores
  agora recebem o código por e-mail e precisam confirmá-lo para ativar a conta.
- **O que faltava:** o plano **gratuito** do Render **bloqueia envio de e-mail**
  (regra deles contra spam). A solução foi migrar o site para o plano **pago
  Starter (~US$7/mês)**, no qual o envio de e-mail é liberado — e de quebra o site
  **não hiberna mais** (fica sempre rápido para os testadores).
- **Correções técnicas no caminho:** o sistema passou a **remover espaços** da senha
  de app do Gmail automaticamente, e a **forçar IPv4** no envio (evita o erro
  "Network is unreachable"). Também foi criada a página **`/admin/testar-email`**
  para diagnosticar o envio (mostra o erro real e o tamanho da senha, sem revelá-la).

**Estado atual:** plataforma no ar em `poker-acessivel.onrender.com`, plano Starter,
banco PostgreSQL permanente, beta fechado por convite + verificação por e-mail.

**Pendência pequena:** existem algumas contas de teste no banco (criadas durante a
configuração). Dá para removê-las adicionando um botão de "excluir usuário" no
painel de admin (a combinar).

---

## 27/07/2026 — v0.6.0 · Verificação de conta por código (anti-bot)

**O que mudou (em palavras simples):**

- 🛡️ **Nova barreira anti-bot.** Quando um convidado se cadastra (e-mail + senha +
  código de convite), a conta fica **"pendente"** e ele recebe um **e-mail com um
  código de 6 dígitos**. Só depois de digitar esse código a conta é **validada** e
  ele consegue entrar. Enquanto não verificar, o login fica bloqueado.
- 📄 **O código chega sozinho numa linha** no e-mail, sem mais nada escrito nela —
  para o leitor de tela ler com clareza.
- **Duas barreiras contra bots:** o **código de convite** (que só você distribui) e
  a **verificação por e-mail** (precisa de uma caixa de entrada real). Bot não passa.
- **O dono e admins não precisam verificar** (só os testadores comuns). Contas
  antigas (que já existiam) foram marcadas como já verificadas, para ninguém travar.
- Há botão de **"Reenviar código"** e o código **expira em 15 minutos**.

**Importante:** a verificação só **envia e-mail de verdade** se o serviço de e-mail
(SMTP) estiver configurado. Sem ele, o cadastro continua funcionando, mas sem a
etapa de código. Ou seja: para ligar a proteção anti-bot, é preciso configurar o
e-mail (passo guiado no `DEPLOY.md`).

**Arquivos novos/alterados:** `server/auth.py`, `server/mailer.py`, `server/db.py`,
`server/app.py`, `web/templates/verificar.html` (novo), `web/templates/login.html`,
`tests/test_verificacao.py` (novo).

---

## 27/07/2026 — v0.5.1 · E-mail de admin entra sem convite (recuperar acesso de dono)

**O que mudou (em palavras simples):**

- Agora um **e-mail designado como administrador** (na variável
  `POKER_ADMIN_EMAILS`) pode **criar a conta sem precisar de código de convite** e
  já entra como **dono/admin** — mesmo no beta fechado e mesmo que já exista outra
  conta no banco.
- Motivo: após ativar o banco permanente, ficou uma conta "fantasma" no banco (de
  algum teste durante a configuração) que bloqueava o dono de se cadastrar. Em vez
  de apagar o banco, o e-mail `xandentro1@gmail.com` foi definido como admin fixo,
  garantindo o acesso do dono.

**Arquivos alterados:** `server/auth.py`, `render.yaml`, `tests/test_admin.py`.

---

## 27/07/2026 — v0.5.0 · Dados permanentes (banco PostgreSQL)

**O que mudou (em palavras simples):**

- 🗄️ **As contas e saldos agora ficam guardados de forma PERMANENTE.** Antes, no
  plano gratuito, os dados sumiam quando o site hibernava ou era reconstruído.
  Agora usamos um banco de dados **PostgreSQL** (permanente e grátis no Render),
  então **contas, saldos e convites não se perdem mais**.
- O código funciona nos **dois** bancos: PostgreSQL quando está publicado (no
  Render) e SQLite no seu computador (para testes) — sem precisar mudar nada.
- Todos os 37 testes continuam passando.

**Para ativar:** é preciso reconstruir o site uma vez no Render ("Manual Sync"),
que vai **criar o banco PostgreSQL** automaticamente (está tudo no `render.yaml`).

**Arquivos alterados:** `server/db.py`, `server/auth.py`, `server/wallet.py`,
`requirements.txt`, `render.yaml`.

---

## 27/07/2026 — v0.4.2 · E-mail de boas-vindas no cadastro

**O que mudou (em palavras simples):**

- **Campos de e-mail e senha no cadastro:** já existiam desde o começo — cada
  testador cria a conta com o próprio apelido, e-mail e senha. (Confirmação.)
- **Novo: e-mail de boas-vindas.** Ao se cadastrar, o usuário recebe um e-mail no
  endereço que informou, com os **dados do cadastro** (apelido, e-mail, saldo
  inicial) e o link da plataforma.
- **Segurança:** o e-mail **não** inclui a senha (enviar senha por e-mail é
  perigoso). Envia só os dados seguros.
- É **opcional**: só funciona se você configurar um serviço de envio de e-mail
  (variáveis `SMTP_*`). Sem isso, o cadastro continua normal, apenas sem enviar
  o e-mail. Passo a passo no `DEPLOY.md`.

**Arquivos novos/alterados:** `server/mailer.py` (novo), `server/app.py`.

---

## 27/07/2026 — v0.4.1 · Correção: primeiro usuário não precisa de convite

**O que mudou (em palavras simples):**

- **Bug corrigido:** no beta fechado, a tela de cadastro estava pedindo código de
  convite **até para o primeiro usuário** (o dono), que deveria ser isento. Por
  dentro o sistema já isentava, mas o formulário travava. Agora o campo de convite
  **só aparece depois que já existe pelo menos um usuário**.
- **Enquanto o site não é reimplantado**, dá para contornar digitando qualquer
  palavra no campo de convite (o primeiro cadastro ignora o código e vira admin).

**Arquivos alterados:** `server/app.py`, `server/auth.py`.

---

## 27/07/2026 — v0.4.0 · 🎉 NO AR! Plataforma publicada 24h

**O que mudou (em palavras simples):**

- 🚀 **A plataforma está PUBLICADA e funcionando na internet**, 24 horas por dia, no
  endereço: **https://poker-acessivel.onrender.com**
- Foi publicada no **Render** (plano gratuito) a partir do repositório do GitHub,
  usando a opção de **repositório público** (que evitou a tela de autorização do
  GitHub que não era acessível pelo leitor de tela).
- **Beta fechado ativo:** para se cadastrar é preciso de um código de convite. O
  **primeiro cadastro vira administrador** e gera os códigos em `/admin`.

**Lembretes do plano gratuito:**
- O serviço **hiberna** após ~15 min sem uso; o primeiro acesso depois demora
  ~30–50 segundos para "acordar". Normal.
- As contas/saldos podem **reiniciar** quando ele hiberna ou a cada novo deploy
  (dados temporários). Para tornar permanente: plano pago com disco, ou PostgreSQL.

---

## 27/07/2026 — v0.3.4 · Publicado no GitHub + correção do deploy gratuito

**O que mudou (em palavras simples):**

- 🎉 O projeto foi **publicado no GitHub**: `github.com/xandentro1-collab/poker-acessivel`
  (público, com todos os arquivos). Esse é o passo que permite colocar no ar.
- **Correção importante no deploy:** o arquivo de configuração do Render pedia um
  "disco permanente" que o **plano gratuito não permite** — isso teria feito a
  publicação falhar. Ajustei para funcionar no plano free.
- **Consequência (plano gratuito):** as contas/saldos são **temporários** e podem
  reiniciar quando o serviço hiberna. Ótimo para testes. Dá para tornar permanente
  depois (plano pago com disco, ou banco PostgreSQL — anotado no `render.yaml`).
- Liguei o **beta fechado por convite** no Render (variável `POKER_EXIGIR_CONVITE`).

**Arquivo alterado:** `render.yaml`.

---

## 24/07/2026 — v0.3.3 · Conexão com o GitHub acessível (sem ler código)

**O que mudou (em palavras simples):**

- Os métodos anteriores de login mostravam um **código na tela do terminal**, que
  o **leitor de tela não lê** — uma barreira de acessibilidade real. Também
  descobrimos que a **janela preta do CMD não é lida** pelo leitor de tela.
- Solução final: o atalho **`conectar_github.vbs`** mostra **uma única caixa de
  diálogo** (tipo caixa de pergunta do Windows, bem lida pelo leitor de tela) onde
  você **cola o token e clica OK**. No fim, aparece uma **caixa de aviso** dizendo
  se conectou. **Nada depende da tela preta do CMD nem de salvar arquivo.** Você
  gera a "senha especial" (token) no site do GitHub (acessível), cola na caixa, e
  o computador fica conectado.
- (O `conectar_github.bat` anterior usava a tela preta do CMD, que o leitor de tela
  não lê, e o Bloco de Notas, com passos demais — por isso trocamos pela caixa de
  diálogo do `.vbs`.)
- **Correção (v2 do `.vbs`):** o script tinha um bug nas aspas do caminho
  "Program Files" que impedia o programa do GitHub de rodar (dava "Não consegui
  conectar" mesmo com o token certo). Reescrito para chamar o programa direto e,
  se falhar, **mostrar o motivo técnico exato** na caixa de aviso.
- **Limpeza:** apagado o `conectar_github.bat` antigo. Havia dois arquivos de nome
  quase igual (`.bat` e `.vbs`), que soam idênticos no leitor de tela e causavam
  clicar no errado. Agora existe **só um**: `conectar_github.vbs`.
- A partir dessa conexão, eu consigo criar o repositório e enviar o código sozinho.

**Por que isso importa:** garante que **o próprio dono da plataforma**, que usa
leitor de tela, consiga publicá-la sem depender de enxergar um código na tela.

**Arquivo novo:** `conectar_github.bat`.

---

## 23/07/2026 — v0.3.2 · Criar o repositório no GitHub quase sozinho

**O que mudou (em palavras simples):**

- Criei o atalho **`criar_repo_github.bat`**. Ele instala o programa do GitHub,
  pede o seu login **uma única vez** (abre o navegador) e, a partir daí,
  **cria o repositório `poker-acessivel` e envia o código automaticamente**.
- Diferença para o `enviar_para_github.bat`: aquele exige que você crie o
  repositório vazio no site primeiro; este **cria o repositório para você**.

**Por que a parte do login é sua:** por segurança, eu nunca entro na sua conta
nem uso a sua senha. O único passo manual é você aprovar o login na janela que
abre — todo o resto é automático.

**Como usar:** dê dois cliques em `criar_repo_github.bat`. Se ele instalar o
GitHub CLI, feche e abra o arquivo de novo (o Windows precisa reconhecer o
programa novo). Faça o login quando pedir. Fim.

**Arquivo novo:** `criar_repo_github.bat`.

---

## 23/07/2026 — v0.3.1 · Envio ao GitHub com dois cliques

**O que mudou (em palavras simples):**

- Criei o atalho **`enviar_para_github.bat`**. Você dá dois cliques, digita o seu
  nome de usuário do GitHub e ele **envia todo o projeto para a internet sozinho**
  (salva as mudanças pendentes, conecta no seu repositório e faz o "push").
- Se aparecer uma janela pedindo para entrar no GitHub, é normal — é só a primeira
  vez, para autorizar o envio.

**Por que isso importa:** era preciso digitar comandos no terminal para publicar o
código. Agora é só um clique, sem decorar nada.

**Como usar:** primeiro crie um repositório vazio em `github.com/new` chamado
`poker-acessivel` (público). Depois dê dois cliques no `enviar_para_github.bat`.

**Arquivo novo:** `enviar_para_github.bat`.

---

## 23/07/2026 — v0.3 · Beta fechado, administração e ficar 24h online

**O que mudou (em palavras simples):**

1. **Convite para entrar (beta fechado).** Agora dá para exigir um "código de
   convite" para criar conta. Assim, só quem você convida consegue entrar e ganhar
   as fichas de treino. Serve para controlar quem testa a plataforma.
   - Cada código serve para **uma** pessoa. Depois de usado, ninguém mais usa.

2. **Painel de Administração (a página `/admin`).** Uma área só sua (do dono) onde
   você:
   - **Gera os códigos de convite** e copia para mandar aos testadores;
   - Vê a **lista de quem já se cadastrou** (com o saldo de cada um);
   - Vê **quais convites** já foram usados e quais ainda estão livres.

3. **Você vira "dono" automaticamente.** A **primeira pessoa** que se cadastrar
   vira administrador. Também dá para fixar o seu e-mail como administrador.

4. **Ficar ligado 24 horas — duas formas prontas:**
   - **Na nuvem (recomendado):** deixei tudo configurado para publicar de graça no
     site *Render*, com um **link fixo** que funciona mesmo com seu computador
     desligado. Você só precisa clicar em um botão e entrar na sua conta.
   - **No seu computador:** criei atalhos (`online_24h.bat`) que ligam o jogo e o
     **reiniciam sozinhos** se travar, e um instalador (`instalar_tarefa_24h.bat`)
     que faz ele **subir sozinho toda vez que o Windows liga**.

5. **Repositório de código (Git).** Organizei o projeto num "pacote versionado",
   pronto para enviar ao GitHub e publicar na nuvem em poucos cliques.

**Por que isso importa:** antes qualquer um com o link poderia criar conta. Agora
você controla os convites, acompanha os testadores por um painel, e tem caminhos
prontos para deixar tudo no ar 24 horas.

**Arquivos novos:** `web/templates/admin.html`, `wsgi.py`, `Procfile`,
`render.yaml`, `online_24h.bat`, `instalar_tarefa_24h.bat`,
`remover_tarefa_24h.bat`, `testar_com_amigos.bat`, `DEPLOY.md`, `.gitignore`,
`tests/test_admin.py`, este `MUDANCAS.md`.

---

## 23/07/2026 — v0.2 · Torneios, cronômetro, visual profissional

**O que mudou (em palavras simples):**

1. **Torneios "Sit & Go" (como no PokerStars).** Além do jogo normal (cash game),
   agora tem torneio: todo mundo paga uma entrada, começa com as mesmas fichas, as
   apostas mínimas (blinds) **vão aumentando com o tempo**, os perdedores são
   **eliminados** e os melhores **ganham prêmios** que caem na carteira.

2. **Cronômetro por jogada.** Cada jogador tem um tempo para agir (30, 45 ou 60
   segundos, ou desligado). Aparece uma barra que diminui, avisa quando faltam 10
   segundos e, se o tempo acabar, o sistema **passa a vez ou desiste** por você.
   Isso evita que uma pessoa trave a mesa.

3. **Reconexão automática.** Se a internet cair no meio do jogo, o sistema
   **reconecta sozinho** e avisa o leitor de tela.

4. **Visual profissional.** A mesa ganhou cara de pôquer de verdade: mesa oval com
   feltro verde, cartas bonitas, fichas, avatares dos jogadores, painel de
   classificação do torneio e tema claro/escuro. Tudo continua 100% acessível.

**Por que isso importa:** o jogo deixou de ser só "uma mesa simples" e passou a ter
**modos de disputa** e aparência de plataforma profissional, sem perder a
acessibilidade.

**Arquivos novos:** `engine/torneio.py`, `tests/test_torneio.py`.

---

## 23/07/2026 — v0.1 · Primeira versão jogável (a base de tudo)

**O que mudou (em palavras simples):**

1. **O jogo de pôquer funciona do início ao fim.** Distribuição de cartas,
   apostas, virada das cartas na mesa (flop, turn, river) e decisão de quem ganha —
   tudo com as regras corretas do Texas Hold'em, inclusive divisão de prêmio quando
   há empate ou aposta parcial (side pots).

2. **Acessibilidade de verdade (o coração do projeto):**
   - **Atalho de teclado para cada ação** (desistir, pagar, passar, apostar,
     aumentar, all-in) e para "descrever a mesa", "dizer minhas cartas", etc.
   - **Leitor de tela** narra tudo em voz ("Ana pagou 100", "Flop: Rei de copas...").
   - **Sons característicos** para cada ação (gerados pelo próprio navegador).
   - Foco visível forte, respeita preferências do sistema (menos animação, alto
     contraste, tema claro/escuro).

3. **Login e carteira.** Criar conta, entrar, ver saldo, depositar, sacar e
   extrato — com contabilidade correta (tudo em modo **simulado**, sem dinheiro
   real).

4. **Jogar contra robôs (bots).** Para você treinar sozinho e testar a
   acessibilidade a qualquer hora.

5. **Vários jogadores ao mesmo tempo.** A mesa funciona em tempo real (tecnologia
   de "WebSocket"), então várias pessoas podem jogar juntas.

**Por que isso importa:** é a fundação. Um pôquer acessível, jogável, com login e
carteira, testado para não ter bugs.

**Como foi garantido que não tem bug:** foram criados **testes automáticos** que
conferem as regras, inclusive um teste que joga dezenas de mãos sozinho e verifica
que **nenhuma ficha some ou aparece do nada**.

**Arquivos principais:** `engine/` (regras do jogo), `server/` (login, carteira,
mesa, servidor), `web/` (as telas), `tests/` (os testes).

---

### Legenda de versões
- **v0.1** — base jogável e acessível.
- **v0.2** — torneios, cronômetro e visual profissional.
- **v0.3** — beta fechado por convite, painel de admin e publicação 24h.
- **v0.9** — torneio multi-mesa (MTT) completo.
- **v0.10** — chance de vencer (tecla O), volume, fold automático e big blind ante.
- **v0.11** — relatório de rodadas com as cartas (Fase 1 do plano grande).
- **v0.12** — bate-papo acessível com conversa privada (Fase 2 do plano grande).
- **v0.13** — amigos e convites para a mesa (Fase 3 do plano grande).
- **v0.14** — aviso de conexão e quadro de avisos (Fase 4 do plano grande).
- **v0.15** — zoom para baixa visão e responsividade no celular (Fase 5).
- **v0.16** — home enxuta, seção de mesas e F1 por botão (Fase 6 — plano concluído).
- **v0.17** — segurança: sessão expira por inatividade e sai ao fechar o navegador.
- **v0.18** — cartas sem repetir, F1 com dois-pontos, convite em janela, amigos online e chat melhorado.
- **v0.19** — convite de torneio por e-mail e início (home) mais limpo.
- **v0.20** — sons completos e personalizáveis (30 sons) + roadmap de melhorias.
- **v0.21** — foco preso nos diálogos (início do roadmap de acessibilidade).
- **v0.22** — testes automáticos da camada web (44%→66%) e correção de mesa/torneio grátis.
- **v0.23** — histórico de mãos no banco + página de Perfil e Configurações.
- **v0.24** — segurança: proteção anti-CSRF e trava contra força-bruta no login.
- **v0.25** — Integração Contínua (GitHub Actions) + faxina de lint (código limpo).
- **v0.26** — verbosidade configurável (completa/média/baixa) — você escolhe o quanto o jogo fala.
- **v0.27** — moderação: bloquear/silenciar e denunciar jogadores (+ painel de denúncias no admin).
- **v0.28** — correções pós-atualização: cache-busting, botão Abandonar, e a "sua vez" sem soletrar teclas.
- **v0.29** — narração fala TODOS os jogadores (fila de fala, sem perder nada) e no modelo pedido (Rodada, blinds, Call/Raise/All-in, Flop/Turn/River, showdown, "Você ganha o pote").
- **v0.30** — Central de Configurações (6 áreas), Central de Acessibilidade (+ alto contraste) e Jogo Responsável (lembrete de tempo, pausa e autoexclusão), inspirados no áudio-demo.
- **v0.31** — sair da mesa devolve fichas + lista de espera no cash (avisa quando abre vaga); "Torneios da casa" com resumo e confirmação antes de entrar na fila.
- **v0.32** — tela inicial enxuta (menu): Mesas, Amigos e Avisos viraram telas próprias; Carteira repetida removida do início.
- **v0.33** — nova identidade visual "Mesa de Veludo": feltro verde-escuro + ouro + creme, títulos serifados, mesa com trilho de madeira e fio de ouro (aplicada em todas as telas).
