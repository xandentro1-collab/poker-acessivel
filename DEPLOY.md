# 🚀 Como liberar para testadores e colocar online

## ⭐ Quero ficar 24 horas online — escolha UMA

**Opção A — Nuvem (recomendada): link fixo, não depende do seu PC.**
Truly 24h. Passos resumidos (detalhe no Caminho 3 abaixo):
1. Suba esta pasta para um repositório **público** no GitHub.
2. Clique no botão (troque `SEU_USUARIO` pela sua conta do GitHub):

   [![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/SEU_USUARIO/poker-acessivel)

3. Faça login no Render e clique **Apply**. Em ~3 min você recebe um link fixo
   `https://...onrender.com`. Pronto — é o endereço dos testadores, no ar 24h.

   > As duas coisas que só **você** pode fazer (eu não posso por segurança):
   > criar sua conta no GitHub/Render e clicar em Apply. Todo o resto já está
   > configurado (`render.yaml`), inclusive **beta fechado por convite** e banco
   > persistente.

**Opção B — No seu próprio PC, sempre ligado.**
O servidor sobe sozinho a cada login do Windows e se reinicia se cair. Só fica no
ar enquanto o PC estiver ligado e com internet.
1. Dê dois cliques em **`instalar_tarefa_24h.bat`** (se disser "Acesso negado",
   clique com o botão direito → *Executar como administrador*).
2. Para deixar público com link, baixe o `cloudflared.exe` (ver Caminho 2) para a
   pasta do projeto — o `online_24h.bat` sobe o túnel automaticamente.
3. Para começar agora sem reiniciar: dê dois cliques em **`online_24h.bat`**.
   Para desativar o início automático: **`remover_tarefa_24h.bat`**.

---

## Detalhes e outras opções

Este guia vai do mais rápido (testar hoje com amigos) ao definitivo (online 24h).

Resumo dos caminhos:

| Quero… | Use | Dificuldade | Público |
|--------|-----|-------------|---------|
| Testar agora com quem está na minha casa/escritório | **Rede local** | ⭐ | Mesma Wi-Fi |
| Testar hoje com qualquer pessoa, sem hospedar | **Túnel (Cloudflare/ngrok)** | ⭐⭐ | Internet (link temporário) |
| Deixar no ar 24h com link fixo | **Render (nuvem)** | ⭐⭐⭐ | Internet (link fixo) |

Em **todos** os casos, cada testador **cria a própria conta** na tela de entrar
(ganha R$ 1.000 de fichas simuladas). Não há nada a "liberar" manualmente: quem
tem o endereço e cria conta, joga. (Como restringir, veja o fim do guia.)

---

## Caminho 1 — Rede local (mais rápido, zero instalação)

Serve para testar com pessoas **na mesma rede Wi-Fi** que você.

1. Dê dois cliques em **`testar_com_amigos.bat`**.
2. Ele mostra endereços como `http://192.168.0.15:5000`.
3. Passe esse endereço para os testadores (mesmo Wi-Fi). Eles abrem no navegador,
   criam conta e jogam.

Se não abrir no PC do testador, o **Firewall do Windows** pode estar bloqueando.
Na primeira execução, o Windows costuma perguntar — clique em **Permitir acesso**
em "Redes privadas". Para liberar manualmente:

```powershell
New-NetFirewallRule -DisplayName "Poker Acessivel" -Direction Inbound -LocalPort 5000 -Protocol TCP -Action Allow
```

---

## Caminho 2 — Túnel público (testar com qualquer pessoa, hoje)

Cria um **link público temporário** que aponta para o seu PC. Ótimo para uma
rodada de testes sem hospedar nada. O link vale enquanto seu PC e o túnel ficam
ligados.

### Opção A — Cloudflare Tunnel (grátis, sem cadastro para teste rápido)

1. Baixe o `cloudflared` (Windows): https://github.com/cloudflare/cloudflared/releases
   (arquivo `cloudflared-windows-amd64.exe`, renomeie para `cloudflared.exe`).
2. Rode o servidor normalmente (`iniciar.bat`).
3. Em outro terminal:

```bash
cloudflared tunnel --url http://localhost:5000
```

4. Ele imprime um link tipo `https://algo-aleatorio.trycloudflare.com`.
   Mande esse link aos testadores. Pronto.

### Opção B — ngrok (grátis, exige cadastro)

1. Crie conta em https://ngrok.com e instale o ngrok.
2. Rode o servidor (`iniciar.bat`) e depois:

```bash
ngrok http 5000
```

3. Copie o link `https://....ngrok-free.app` e compartilhe.

> Os dois já são **HTTPS**, então os WebSockets do jogo funcionam sem ajuste.

---

## Caminho 3 — Online 24h com link fixo (Render, grátis)

Coloca a plataforma na nuvem, acessível a qualquer momento. Usaremos o **Render**
(plano free). Já deixei os arquivos prontos: `Procfile`, `render.yaml`, `wsgi.py`.

### Passo a passo

1. **Crie um repositório no GitHub** com esta pasta (`poker-acessivel`).
   - Instale o Git, e dentro da pasta:
     ```bash
     git init
     git add .
     git commit -m "Poker acessível"
     ```
   - Crie um repo vazio em github.com e siga as instruções de `git remote add` +
     `git push` que o GitHub mostra.
   - O `.gitignore` já evita subir o banco e a `venv`.

2. **Crie a conta no Render** em https://render.com (pode entrar com o GitHub).

3. No painel do Render: **New +** → **Blueprint** → selecione seu repositório.
   O Render lê o `render.yaml` e configura tudo sozinho (build, start, disco,
   chave secreta). Clique em **Apply**.

4. Aguarde o build (2–4 min). No fim, o Render te dá um link fixo, tipo
   `https://poker-acessivel.onrender.com`. **Esse é o endereço dos testadores.**

### Observações importantes do plano free do Render
- **Dorme após inatividade:** sem acessos por ~15 min, o serviço "hiberna" e o
  primeiro acesso seguinte demora ~30 s para acordar. Normal no plano grátis.
- **1 worker só:** as mesas ficam na memória do processo; por isso usamos
  `-w 1` (um worker). Está correto para começar. Escalar para vários processos
  exigiria mover o estado das mesas para um Redis (evolução futura).
- **Banco:** configurei um **disco persistente** de 1 GB (`/var/data/poker.db`),
  então contas e saldos **não** se perdem entre deploys.

### Alternativas equivalentes
- **Railway** (railway.app): suba o repo, ele detecta o `Procfile`. Defina as
  variáveis `POKER_SECRET` e `POKER_DB`.
- **Fly.io** ou uma **VPS** (Ubuntu): rode `gunicorn -k gevent -w 1 wsgi:app`
  atrás de um Nginx com proxy de WebSocket. Mais controle, mais trabalho.

---

## Como dar / restringir acesso aos testadores (JÁ IMPLEMENTADO)

O **beta fechado por convite** já está pronto:

- **Ligar o modo convite:** defina a variável de ambiente `POKER_EXIGIR_CONVITE=1`.
  No Render isso já vem ligado pelo `render.yaml`. No PC, o `online_24h.bat` já
  liga sozinho. Com ele ligado, todo cadastro exige um código válido (um código
  serve para um cadastro).
- **Quem é administrador:** o **primeiro** usuário que se cadastrar vira admin
  automaticamente. Você também pode forçar via `POKER_ADMIN_EMAILS=seu@email.com`
  (o `online_24h.bat` já usa o seu e-mail).
- **Painel de administração (`/admin`):** só admins acessam. Lá você:
  - **Gera os códigos de convite** (quantos quiser) e copia para enviar aos
    testadores.
  - Vê a **lista de convites** (usados/disponíveis) e a **lista de testadores**
    com saldo e data de cadastro.
- **Cadastro aberto:** se preferir sem convite, deixe `POKER_EXIGIR_CONVITE=0`
  (ou não defina). Aí qualquer um com o link cria conta.

Fluxo típico de um beta fechado: você entra em `/admin` → gera 10 códigos →
manda um para cada testador → eles se cadastram com o código.

---

## Ligar o e-mail de boas-vindas (opcional)

Para os testadores receberem um e-mail com seus dados ao se cadastrar, configure um
serviço de envio (SMTP). Caminho mais fácil: **Gmail com "senha de app"**.

1. **Gerar a senha de app do Gmail** (exige verificação em 2 etapas ativada):
   - Acesse `https://myaccount.google.com/apppasswords`
   - Crie uma senha de app (16 letras) e copie.
2. **No Render**, no serviço `poker-acessivel` → aba **Environment** → adicione:
   - `SMTP_HOST` = `smtp.gmail.com`
   - `SMTP_PORT` = `587`
   - `SMTP_USER` = seu e-mail do Gmail
   - `SMTP_PASS` = a senha de app gerada (16 letras)
   - `SMTP_FROM` = seu e-mail do Gmail
3. Salve. O Render republica sozinho. Pronto — novos cadastros recebem o e-mail.

> Nunca coloque a `SMTP_PASS` no código/repositório — só nas variáveis do Render.
> Se essas variáveis não existirem, o cadastro funciona normalmente, só sem enviar
> e-mail. A senha do usuário **nunca** é enviada por e-mail.

## Antes de abrir para muita gente (checklist)

- [x] Chave secreta vem de variável de ambiente (`POKER_SECRET`) — já configurado.
- [x] Servidor de produção (gunicorn + gevent) — já configurado.
- [x] Banco em disco persistente — já configurado no `render.yaml`.
- [x] Beta fechado por convite + painel de admin — já implementado (`/admin`).
- [ ] **Dinheiro real:** continua **simulado**. Só habilite depósito/saque reais
      com licença de jogo + gateway (PIX) + KYC. Ver seção no `README.md`.
- [ ] HTTPS: os três caminhos com túnel/Render já entregam HTTPS. Em VPS própria,
      configure um certificado (Let's Encrypt).
