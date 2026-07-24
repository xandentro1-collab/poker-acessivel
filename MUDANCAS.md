# 📋 Registro de Mudanças (para leigos)

Este arquivo explica, em linguagem simples, **tudo o que foi feito** no projeto e o
que muda a cada alteração. As mudanças mais **recentes ficam no topo**. Cada item
diz **o que mudou** e **para que serve**, sem termos técnicos.

> Como ler: pense em cada bloco como "uma novidade que entrou no jogo".

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
