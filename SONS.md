# 🔊 Catálogo de sons do Poker Acessível

Todos os sons são **gerados pelo navegador** por padrão (não precisa de arquivo).
Para **personalizar**, coloque um arquivo **MP3** na pasta `web/static/sons/` com o
**nome do arquivo** indicado abaixo. Ex.: para trocar o som de desistir, crie
`web/static/sons/foldar.mp3`.

- **Ligar/desligar** todos os sons: tecla **M** (ou o botão "🔊 Som").
- **Volume**: teclas **vírgula** (menor) e **ponto** (maior), ou os botões de volume.
- Dica: use MP3 **curtos** (menos de 1–2 s).

> Legenda: **Nome interno** é como o código chama o som; **Arquivo p/ trocar** é o
> nome do MP3 que você coloca na pasta; **Quando toca** é a função.

## 🎮 Ações do jogo

| Nome interno | Arquivo p/ trocar | Quando toca |
|---|---|---|
| `fold` | `foldar.mp3` | Alguém desiste da mão (fold) |
| `check` | `passar.mp3` | Alguém passa (check) |
| `call` | `pagar.mp3` | Alguém paga (call) |
| `bet` | `apostar.mp3` | Alguém aposta (bet) |
| `raise` | `aumentar.mp3` | Alguém aumenta (raise) |
| `allin` | `all-in.mp3` | Alguém vai de tudo (all-in) |
| `inicioMao` | `inicio-mao.mp3` | Começa uma nova mão (embaralhar/repartir) |
| `deal` | `distribuir.mp3` | Cartas sendo entregues |
| `cartaMesa` | `carta-mesa.mp3` | Vira carta na mesa (flop, turn, river) |
| `suaVez` | `sua-vez.mp3` | Chegou a **sua** vez de agir |
| `vitoria` | `vitoria.mp3` | Você ganhou a mão |
| `derrota` | `derrota.mp3` | Você perdeu a mão |
| `erro` | `erro.mp3` | Ação inválida / algo deu errado |

## 💬 Social e avisos

| Nome interno | Arquivo p/ trocar | Quando toca |
|---|---|---|
| `mensagem` | `mensagem.mp3` | Mensagem no bate-papo (para todos) |
| `mensagemPrivada` | `mensagem-privada.mp3` | Mensagem privada (PV) recebida |
| `conexao` | `conexao.mp3` | Alguém entrou na plataforma |
| `aviso` | `aviso.mp3` | Comunicado da plataforma (quadro de avisos) |
| `convite` | `convite.mp3` | Convite recebido (mesa ou torneio) |
| `amigo` | `amigo.mp3` | Alguém te adicionou como amigo |
| `copiar` | `copiar.mp3` | Texto copiado para a área de transferência |
| `emailEnviado` | `email-enviado.mp3` | E-mail enviado (relatório, convite) |
| `clique` | `clique.mp3` | Confirmação curta de botão (feedback geral) |

## 💰 Dinheiro

| Nome interno | Arquivo p/ trocar | Quando toca |
|---|---|---|
| `deposito` | `deposito.mp3` | Depósito na carteira (caixa registradora) |
| `saque` | `saque.mp3` | Saque da carteira |
| `rebuy` | `rebuy.mp3` | Você fez rebuy (recompra) no torneio |
| `addon` | `addon.mp3` | Você comprou o add-on no torneio |

## 🏆 Torneio e plateia

| Nome interno | Arquivo p/ trocar | Quando toca |
|---|---|---|
| `vaia` | `vaia.mp3` | Um jogador perdeu todas as fichas (vaia da plateia) |
| `aplauso` | `aplauso.mp3` | **Você** eliminou alguém (aplausos) |
| `terror` | `aviso-tempo.mp3` | Aviso tenso de tempo acabando (timer curto) |
| `novoNivel` | `novo-nivel.mp3` | Os blinds subiram de nível *(reservado)* |

---

**Total: 30 sons.** Todos já têm um som gerado automaticamente; troque só os que
você quiser. Se um arquivo MP3 não existir, o som automático é usado no lugar.
