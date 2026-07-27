# 📋 Registro de Mudanças (para leigos)

Este arquivo explica, em linguagem simples, **tudo o que foi feito** no projeto e o
que muda a cada alteração. As mudanças mais **recentes ficam no topo**. Cada item
diz **o que mudou** e **para que serve**, sem termos técnicos.

> Como ler: pense em cada bloco como "uma novidade que entrou no jogo".

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
