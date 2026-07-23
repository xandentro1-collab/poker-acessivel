# ♠ Poker Acessível — Texas Hold'em para leitores de tela

Plataforma de **Poker Texas Hold'em No-Limit** desenhada do zero com foco em
**acessibilidade (WCAG 2.1 AA)**: navegação 100% por teclado, integração perfeita
com leitores de tela (NVDA, JAWS, VoiceOver, Orca) e **sons característicos** para
cada ação. Une a acessibilidade do estilo *qcsalon.net* com recursos de plataforma
profissional (login, carteira, modos de disputa) no espírito do PokerStars.

## Como rodar

Requer **Python 3.10+**. No Windows, basta dar duplo clique em **`iniciar.bat`**
(cria o ambiente, instala tudo e sobe o servidor). Ou manualmente:

```bash
python -m venv venv
venv\Scripts\python -m pip install -r requirements.txt
venv\Scripts\python -m server.app
```

Depois abra **http://localhost:5000** no navegador (com o leitor de tela ligado).

Crie uma conta (ganha R$ 1.000 em fichas de treino), crie uma mesa com bots e jogue.

## Atalhos de teclado (na mesa)

| Tecla | Ação | Tecla | Ação |
|-------|------|-------|------|
| `F` | Desistir (fold) | `D` | Descrever a mesa (pote, board, vez) |
| `C` | Pagar / passar | `S` | Dizer minhas cartas |
| `K` | Passar (check) | `P` | Dizer os stacks |
| `B` | Apostar (bet) | `V` | De quem é a vez |
| `R` | Aumentar (raise) | `H` | Ajuda / atalhos |
| `A` | All-in | `M` | Ligar/desligar sons |
| `↑ ↓` / `+ −` | Ajustar valor da aposta | `Espaço` | Iniciar / próxima mão |
| `Enter` | Confirmar aposta/aumento | | |

## Recursos de acessibilidade

- **Regiões ARIA ao vivo**: narração em `aria-live="polite"`; sua vez e resultados
  em `aria-live="assertive"`. Toda ação é falada ("Ana pagou 100", "Flop: Rei de
  copas, 7 de paus, Ás de espadas").
- **Cartas como `role="img"`** com rótulo falado ("Ás de espadas") e símbolo visual.
- **Foco gerenciado**: quando é sua vez, o foco vai para o primeiro botão de ação;
  som + anúncio assertivo avisam.
- **Foco visível** forte (WCAG 2.4.7), **pular para conteúdo**, HTML semântico.
- Respeita `prefers-reduced-motion`, `prefers-contrast` e `prefers-color-scheme`.
- **Sons procedurais** (Web Audio, sem arquivos): fold, check, call, bet, raise,
  all-in, distribuição, sua vez, vitória, derrota, erro. Desligáveis com `M`.

## Modos de disputa

- **Cash Game** — fichas = dinheiro, entra e sai quando quiser.
- **Sit & Go (torneio)** — buy-in fixo, todos começam com as mesmas fichas,
  **blinds crescentes** por tempo (estrutura turbo), **eliminação** e
  **premiação** automática (top 2 ou top 3, no estilo PokerStars). O prêmio cai
  na carteira do jogador. A classificação final é anunciada e listada na tela.

## Timer de ação e reconexão

- **Timer por jogada** (30/45/60 s ou desligado): barra visual com contagem,
  aviso sonoro e falado aos 10 s, e **auto-fold/auto-check** quando esgota.
  Atalho `T` diz o tempo restante.
- **Reconexão automática** do WebSocket: se a conexão cair, o cliente reconecta
  sozinho (com backoff) e avisa o leitor de tela.

## Arquitetura

```
engine/          Motor de poker puro (sem dependências, testável)
  cards.py         Cartas, baralho, nomes falados para leitor de tela
  evaluator.py     Avaliação de mãos (5 melhores de 7) + descrição falada
  game.py          Máquina de estados da mão: blinds, rodadas, side pots, showdown
server/
  db.py            SQLite: usuários, ledger da carteira, sessões
  auth.py          Cadastro/login (PBKDF2), sessões
  wallet.py        Saldo, depósito, saque, buy-in, extrato (em centavos)
  bot.py           IA heurística dos adversários
  mesa.py          Gerencia mãos em sequência, assentos, bots, narração
  app.py           Flask: rotas, API REST, WebSocket (tempo real)
web/
  templates/       Páginas (base, login, lobby, mesa, carteira)
  static/          app.css, poker.js (mesa), sons.js (Web Audio), a11y.js
tests/             28 testes automatizados
```

## Testes

```bash
venv\Scripts\python tests/test_evaluator.py   # avaliação de mãos
venv\Scripts\python tests/test_game.py        # regras + conservação de fichas (fuzz)
venv\Scripts\python tests/test_wallet.py      # auth + carteira
venv\Scripts\python tests/test_mesa.py        # integração mesa + bots
```

O `test_game.py` inclui um teste de **fuzzing** que joga 30 mãos aleatórias
completas e verifica que **fichas nunca somem nem aparecem** (invariante do pote).

## ⚠️ Dinheiro real — importante

A carteira está em **MODO SIMULADO**: depósito e saque **não movem dinheiro real**.
São fichas de treino. Para operar com dinheiro de verdade você precisa, além do
código:

1. **Licença de jogo/apostas** na jurisdição (no Brasil, regulamentação da SPA/MF).
2. **Gateway de pagamento** (PIX, cartão) — plugue em `wallet.depositar` / `wallet.sacar`,
   registrando o lançamento **somente após confirmação do provedor**.
3. **KYC / antifraude / jogo responsável** (verificação de identidade, limites, autoexclusão).

O ledger já é **append-only e auditável** (saldo = soma dos lançamentos), pronto
para essa integração.

## Colocar online / testar com outras pessoas

Veja **[DEPLOY.md](DEPLOY.md)**: rede local (na hora), túnel público
(Cloudflare/ngrok, hoje) ou nuvem 24h (Render, grátis — arquivos `Procfile`,
`render.yaml` e `wsgi.py` já prontos). Cada testador cria a própria conta.

## Próximos passos sugeridos

- Multi-mesa (MTT) e mesas satélite.
- Código de convite para beta fechado + painel de administrador.
- Histórico de mãos exportável e chat de mesa acessível.
- Integração de pagamento real (PIX) — requer licença e KYC.
