# Ideias e estrutura extraídas do áudio "demonstrado.m4a"

> O áudio é uma demonstração, navegada por uma pessoa cega com **VoiceOver**, de um
> aplicativo de poker acessível chamado **"Roadhouse Poker"** — tagline *"Poker
> acessível, competitivo e feito para todos"*. Abaixo está a **estrutura reconstruída**
> a partir da transcrição (que é ruidosa por causa da fala do leitor de tela).

## Fluxo geral (telas, em ordem)

1. **Boas-vindas / login**
   - "Bem-vindo ao Roadhouse Poker."
   - "Entre na sua conta ou faça seu cadastro para acessar torneios, cash games e mesas privadas."
   - Botões: **Fazer login** · **Criar cadastro**

2. **Cadastro em 3 ETAPAS (assistente passo a passo)**
   - **Etapa 1 de 3 — Seus dados**
     - *Dados pessoais:* Nome completo, Data de nascimento, CPF
     - *Contato e segurança:* E-mail, Celular com DDD, Senha
       (regra falada: "mínimo 8 caracteres, uma letra maiúscula, um número…")
     - *Endereço:* CEP, Logradouro (rua/avenida/outro), Número, Complemento (opcional),
       Bairro, Cidade, Estado
     - Botão: **Próximo: verificar identidade**
   - **Etapa 2 de 3 — Verificação de identidade (KYC)**
     - Aviso: "um protótipo apenas simula a captura e **não salva imagens**."
     - *Selfie segurando o RG* — "tenha o rosto e o documento visíveis, não use óculos
       escuros, filtros ou foto de outra tela." Botão **Tirar selfie com RG**
     - *Fotos do RG* — "fotografe a frente e o verso, com boa iluminação e sem cortar as
       bordas." Botão **Fotografar frente e verso do RG**
     - Botão: **Próximo: validar contato**
   - **Etapa 3 de 3 — Valide sua conta**
     - "Escolha onde deseja receber o código de validação."
     - Opções: **SMS** · **WhatsApp** · **E-mail**
     - Campo "Digite o código recebido" + botão **Concluir cadastro**
     - "Conta validada. Cadastro concluído com sucesso." → **Continuar**

3. **Home / boas-vindas (depois de logado)**
   - "Bem-vindo, novo jogador. Prepare-se para viver grandes momentos, disputar potes,
     enfrentar novos desafios e compartilhar mesas com seus amigos."
   - Seções: **Torneios** · **Cash Game** · **Configurações** · **Sair**
     (cada uma com uma frase explicando o que é)

4. **Cash Game**
   - "Entre em uma lista de espera ou crie a mesa para até nove jogadores."
   - Mesa em andamento: mínimo R$ 300,00, "valores fixos definidos pela mesa; você será
     chamado quando houver vaga." Botão **Entrar na lista de espera**
   - **Criar Cash Game privado** → "Configurar nova mesa" (marcado como "próxima versão")

5. **Torneios**
   - "Escolha um torneio programado ou organize uma competição privada."
   - *Torneio da casa:* entrada R$ 100,00, stack inicial 30 mil fichas, mesa de até 9,
     "horário e premiação exibidos antes da confirmação." Botão **Entrar na fila do torneio**
   - **Criar torneio privado** → "defina nome, participantes, valor, fichas iniciais,
     níveis, rebuy, add-on e compartilhe" (marcado como "próxima versão")

6. **Configurações (o coração acessível do app)** — uma central com 6 áreas, cada uma
   com título + descrição + botão "Abrir":
   - **Acessibilidade** — anúncios das jogadas, sons, vibração, confirmações e alto contraste
   - **Ajuda e suporte** — perguntas frequentes, contato e orientação sobre o app
   - **Jogo responsável** — limites, pausas, autoexclusão e informações de prevenção
   - **Privacidade** — uso de dados pessoais, documentos, biometria e direitos do titular
   - **Termos e contratos** — termos de uso, regras das mesas, pagamentos e cancelamento
   - **Segurança** — senha, sessões, dispositivos autorizados e autenticação em duas etapas

7. **Sair**
   - "Deseja encerrar sua sessão?" (Cancelar / Sair)
   - "Até logo. Esperamos ver você novamente nas mesas."

## Padrões de acessibilidade que o demo usa (e valem copiar)

- Toda tela tem **título** claro, um **parágrafo explicativo** e **botões com rótulo
  descritivo** ("Abrir acessibilidade", "Entrar na fila do torneio").
- **Diálogos de confirmação** ("Atenção…") para toda ação importante, com feedback
  falado do que aconteceu.
- **Assistente passo a passo** ("Etapa 1 de 3") em vez de um formulário gigante.
- **Central de Configurações organizada por temas** — fácil de varrer com o leitor de tela.
