"""Mesa: roda mãos em sequência, gerencia assentos, bots, torneio e timer.

Uma Mesa mantém jogadores sentados com um `stack` local (fichas na mesa). O
buy-in/cash-out contra a carteira é feito na camada do app. Aqui é só o jogo.

Suporta:
- Cash Game: fichas = saldo, entra/sai quando quiser.
- Sit & Go (torneio): blinds crescentes por tempo, eliminação e premiação.
- Timer de ação por jogador com auto-fold/auto-check quando esgota.
"""
from __future__ import annotations

import threading
import time
import uuid

from engine.cards import Deck
from engine.game import MaoDePoker, Player
from engine.torneio import (ESTRUTURA_PADRAO, calcular_premios,
                            nivel_por_indice)
from . import bot


class Assento:
    def __init__(self, jogador_id, nome, stack, eh_bot=False, usuario_id=None):
        self.jogador_id = jogador_id
        self.nome = nome
        self.stack = stack
        self.eh_bot = eh_bot
        self.usuario_id = usuario_id
        self.stack_inicio_mao = stack  # snapshot p/ desempate de eliminação


MODOS = {
    "cash": {"nome": "Cash Game", "sb": 25, "bb": 50, "stack_inicial": 5000},
    "sitngo": {"nome": "Sit & Go (torneio)", "sb": 10, "bb": 20,
               "stack_inicial": 1500, "torneio": True, "duracao_nivel": 120,
               "buy_in": 1000},  # buy-in de R$ 10,00 (em centavos)
}


class Mesa:
    def __init__(self, mesa_id, nome, modo="cash", sb=25, bb=50, max_jogadores=6,
                 stack_inicial=5000, on_evento=None, torneio=False,
                 duracao_nivel=120, buy_in=0, tempo_acao=0, on_premiar=None,
                 auto_iniciar=False, fechar_ao_terminar=True, big_blind_ante=False):
        self.id = mesa_id
        self.nome = nome
        self.modo = modo
        self.sb = sb
        self.bb = bb
        self.ante = 0
        # big blind ante (cash): só o jogador do big blind paga um ante = big blind
        self.big_blind_ante = big_blind_ante
        if big_blind_ante and not torneio:
            self.ante = bb
        self.max_jogadores = max_jogadores
        self.stack_inicial = stack_inicial
        # próxima rodada: automática ou por comando (barra de espaço)
        self.auto_iniciar = auto_iniciar
        self.proxima_auto = None          # epoch para auto-iniciar a próxima mão
        # ao terminar o torneio: fechar a mesa (remover) ou reiniciar
        self.fechar_ao_terminar = fechar_ao_terminar
        self.remover = False              # sinaliza ao gerenciador para remover a mesa
        self.teve_humano = False          # já teve algum humano (evita remover mesa nova)
        self.pausada = False              # pausa (ex.: intervalo de add-on no torneio MTT)
        self.assentos: list[Assento | None] = [None] * max_jogadores
        self.button_pos = 0
        self.mao: MaoDePoker | None = None
        self.mao_ativa = False
        self.lock = threading.RLock()
        self.on_evento = on_evento or (lambda mesa, evt: None)
        self.on_premiar = on_premiar or (lambda assento, valor, colocacao: None)
        self.numero_mao = 0
        self.log_narracao: list[str] = []
        # histórico de mãos jogadas (para o relatório rodada-a-rodada, com cartas)
        self.historico: list[dict] = []

        # torneio
        self.torneio = torneio
        self.duracao_nivel = duracao_nivel
        self.buy_in = buy_in
        self.nivel_idx = 0
        self.inicio_nivel = time.time()
        self.entrantes = 0
        self.classificacao: list[dict] = []   # 1º ao último, à medida que definem
        self.torneio_encerrado = False
        if torneio:
            nivel = nivel_por_indice(ESTRUTURA_PADRAO, 0)
            self.sb, self.bb, self.ante = nivel.sb, nivel.bb, nivel.ante

        # timer de ação
        self.tempo_acao = tempo_acao           # segundos; 0 = desligado
        self.deadline: float | None = None     # epoch em que a vez expira

    # ---------- assentos ----------
    def sentar(self, jogador_id, nome, stack, eh_bot=False, usuario_id=None) -> int:
        with self.lock:
            for i, a in enumerate(self.assentos):
                if a is None:
                    self.assentos[i] = Assento(jogador_id, nome, stack, eh_bot, usuario_id)
                    if not eh_bot:
                        self.teve_humano = True
                    return i
            raise ValueError("mesa cheia")

    def levantar(self, jogador_id) -> int:
        with self.lock:
            for i, a in enumerate(self.assentos):
                if a and a.jogador_id == jogador_id:
                    stack = a.stack
                    self.assentos[i] = None
                    return stack
            return 0

    def jogadores_sentados(self) -> list[Assento]:
        return [a for a in self.assentos if a is not None]

    def humanos(self) -> list[Assento]:
        return [a for a in self.jogadores_sentados() if not a.eh_bot]

    def preencher_com_bots(self, quantidade: int) -> None:
        nomes = ["Ana", "Bruno", "Carla", "Diego", "Elisa", "Felipe", "Gabi", "Hugo"]
        usados = {a.nome for a in self.jogadores_sentados()}
        disp = [n for n in nomes if n not in usados]
        for i in range(quantidade):
            if len(self.jogadores_sentados()) >= self.max_jogadores:
                break
            nome = disp[i] if i < len(disp) else f"Bot{i}"
            self.sentar(f"bot-{uuid.uuid4().hex[:6]}", nome, self.stack_inicial, eh_bot=True)

    # ---------- ciclo de mãos ----------
    def pode_iniciar(self) -> bool:
        if self.torneio_encerrado or self.pausada:
            return False
        return sum(1 for a in self.jogadores_sentados() if a.stack > 0) >= 2

    def _avancar_nivel_se_preciso(self) -> None:
        if not self.torneio:
            return
        if self.entrantes == 0:
            self.entrantes = len(self.jogadores_sentados())
            self.inicio_nivel = time.time()
        decorrido = time.time() - self.inicio_nivel
        if decorrido >= self.duracao_nivel and self.nivel_idx < len(ESTRUTURA_PADRAO) - 1:
            self.nivel_idx += 1
            self.inicio_nivel = time.time()
            nivel = nivel_por_indice(ESTRUTURA_PADRAO, self.nivel_idx)
            self.sb, self.bb, self.ante = nivel.sb, nivel.bb, nivel.ante

    def iniciar_mao(self) -> bool:
        with self.lock:
            if self.mao_ativa or not self.pode_iniciar():
                return False
            self.proxima_auto = None
            self._avancar_nivel_se_preciso()
            self._mapa_pos = []
            players = []
            for i, a in enumerate(self.assentos):
                if a and a.stack > 0:
                    a.stack_inicio_mao = a.stack
                    players.append(Player(id=a.jogador_id, nome=a.nome, stack=a.stack))
                    self._mapa_pos.append(i)
            if len(players) < 2:
                return False
            btn_lista = self._proximo_com_stack_lista(self.button_pos)
            self.mao = MaoDePoker(
                players, button_pos=btn_lista, small_blind=self.sb,
                big_blind=self.bb, deck=Deck(), ante=self.ante,
                big_blind_ante=self.big_blind_ante,
            )
            self.numero_mao += 1
            self.mao.iniciar()
            self.mao_ativa = True
            self.log_narracao = []
            if self.ante and self.big_blind_ante:
                extra = f", big blind ante {self.ante} (pago pelo big blind)"
            elif self.ante:
                extra = f", ante {self.ante}"
            else:
                extra = ""
            nivel_txt = f" Nível {self.nivel_idx + 1}." if self.torneio else ""
            self._narrar(f"Mão número {self.numero_mao}.{nivel_txt} "
                         f"Blinds {self.sb} e {self.bb}{extra}.")
            self._emitir("nova_mao", numero=self.numero_mao)
            self._processar_bots()
            self._atualizar_deadline()
            return True

    def _proximo_com_stack_lista(self, pos_assento) -> int:
        n = self.max_jogadores
        for k in range(n):
            cand = (pos_assento + k) % n
            if cand in self._mapa_pos:
                return self._mapa_pos.index(cand)
        return 0

    def acao_humano(self, jogador_id, acao, valor=None) -> dict:
        with self.lock:
            if not self.mao or not self.mao_ativa:
                raise ValueError("nenhuma mão em andamento")
            if self.mao.to_act is None or self.mao.players[self.mao.to_act].id != jogador_id:
                raise ValueError("não é a sua vez")
            antes = len(self.mao.board)
            evt = self.mao.aplicar_acao(jogador_id, acao, valor)
            self._narrar_acao(evt)
            self._emitir("acao", **evt)
            self._narrar_board_novo(antes)
            self._pos_acao()
            self._processar_bots()
            self._atualizar_deadline()
            return evt

    def _pos_acao(self):
        if self.mao and self.mao.encerrada:
            self._finalizar_mao()

    def _processar_bots(self):
        seguranca = 0
        while self.mao and self.mao_ativa and not self.mao.encerrada:
            seguranca += 1
            if seguranca > 200:
                break
            to_act = self.mao.to_act
            if to_act is None:
                break
            player = self.mao.players[to_act]
            assento = self._assento_de(player.id)
            if assento is None or not assento.eh_bot:
                break  # vez de um humano
            acao, valor = bot.decidir(self.mao, player.id)
            antes = len(self.mao.board)
            try:
                evt = self.mao.aplicar_acao(player.id, acao, valor)
            except ValueError:
                evt = self.mao.aplicar_acao(player.id, "fold")
            self._narrar_acao(evt)
            self._emitir("acao", **evt)
            self._narrar_board_novo(antes)
            if self.mao.encerrada:
                self._finalizar_mao()
                break

    # ---------- timer de ação ----------
    def _atualizar_deadline(self):
        """Define o prazo da vez atual, se for de um humano e o timer estiver ligado."""
        if (self.tempo_acao and self.mao and self.mao_ativa
                and self.mao.to_act is not None):
            p = self.mao.players[self.mao.to_act]
            a = self._assento_de(p.id)
            self.deadline = time.time() + self.tempo_acao if (a and not a.eh_bot) else None
        else:
            self.deadline = None

    def tempo_restante(self) -> float | None:
        if self.deadline is None:
            return None
        return max(0.0, self.deadline - time.time())

    def equidade(self, jogador_id) -> float | None:
        """% de chance de vencer a mão agora, contra quem ainda está na disputa."""
        if not self.mao or not self.mao_ativa:
            return None
        p = next((pl for pl in self.mao.players if pl.id == jogador_id), None)
        if not p or not p.hole or p.foldou:
            return None
        num_op = sum(1 for pl in self.mao.players if pl.na_mao and pl.id != jogador_id)
        if num_op < 1:
            return 100.0
        from engine.evaluator import equidade as _calc
        return _calc(p.hole, self.mao.board, num_op)

    def tick(self) -> bool:
        """Chamado periodicamente pelo servidor. Auto-inicia a próxima mão (se ligado)
        e aplica auto-ação se o tempo esgotou.

        Retorna True se algo mudou (o servidor deve rebroadcastar o estado).
        """
        with self.lock:
            # auto-iniciar as mãos (modo automático): agenda e dispara sozinho
            if self.auto_iniciar and not self.mao_ativa and self.pode_iniciar():
                if self.proxima_auto is None:
                    self.proxima_auto = time.time() + 3.0   # também a primeira mão
                elif time.time() >= self.proxima_auto:
                    self.proxima_auto = None
                    self.iniciar_mao()
                    return True
            if not self.mao_ativa or self.deadline is None:
                return False
            if self.mao.to_act is None:
                return False
            if time.time() < self.deadline:
                return False
            p = self.mao.players[self.mao.to_act]
            a = self._assento_de(p.id)
            if a is None or a.eh_bot:
                self.deadline = None
                return False
            # tempo esgotado: passa se puder, senão desiste
            va = self.mao.acoes_validas()
            acao = "check" if "check" in va else "fold"
            self._narrar(f"{p.nome} não agiu a tempo.")
            antes = len(self.mao.board)
            evt = self.mao.aplicar_acao(p.id, acao)
            self._narrar_acao(evt)
            self._emitir("acao", **evt)
            self._narrar_board_novo(antes)
            self._pos_acao()
            self._processar_bots()
            self._atualizar_deadline()
            return True

    def _finalizar_mao(self):
        if self.mao:
            vencedores = [v["jogador"] for v in self.mao.vencedores]
            for i, player in enumerate(self.mao.players):
                a = self.assentos[self._mapa_pos[i]]
                if a:
                    a.stack = player.stack
            self._gravar_historico()          # registra a mão (com cartas) para o relatório
            self._narrar_resultado()
            self._emitir("fim_mao", vencedores=self.mao.vencedores,
                         estado=self.mao.estado_publico())
            # eliminação: quem zerou as fichas nesta mão -> vaia (todos) + aplauso (quem eliminou)
            for i, player in enumerate(self.mao.players):
                a = self.assentos[self._mapa_pos[i]]
                if a and a.stack <= 0 and a.stack_inicio_mao > 0:
                    elim = next((v for v in vencedores if v != a.jogador_id), None)
                    self._emitir("eliminacao", eliminado=a.nome, eliminador=elim,
                                 eliminador_nome=(self._nome(elim) if elim else None))
                    # oferece o relatório rodada-a-rodada a quem perdeu (só humanos)
                    if not a.eh_bot:
                        self._emitir("relatorio_disponivel", jogador_id=a.jogador_id,
                                     nome=a.nome, rodadas=len(self.historico))
        self.mao_ativa = False
        self.deadline = None
        if self.torneio:
            self._processar_eliminacoes()
        self.button_pos = self._proximo_assento_ocupado((self.button_pos + 1) % self.max_jogadores)
        # agenda a próxima mão automática (se ligado) — dá tempo de ouvir o resultado
        if self.auto_iniciar and not self.torneio_encerrado and self.pode_iniciar():
            self.proxima_auto = time.time() + 5.0
        else:
            self.proxima_auto = None

    # ---------- torneio: eliminação e premiação ----------
    def _processar_eliminacoes(self):
        zerados = [a for a in self.jogadores_sentados() if a.stack <= 0]
        sobreviventes = [a for a in self.jogadores_sentados() if a.stack > 0]
        if zerados:
            # mais fichas no início da mão finaliza em colocação melhor
            zerados.sort(key=lambda a: a.stack_inicio_mao, reverse=True)
            base = len(sobreviventes)
            for j, a in enumerate(zerados):
                colocacao = base + 1 + j
                self._premiar(a, colocacao)
                self._remover_assento(a)
        # sobrou um: campeão
        if self.torneio and not self.torneio_encerrado:
            vivos = [a for a in self.jogadores_sentados() if a.stack > 0]
            if len(vivos) == 1 and (len(self.classificacao) > 0 or self.entrantes > 1):
                campeao = vivos[0]
                self._premiar(campeao, 1)
                self.torneio_encerrado = True
                self._narrar(f"Fim do torneio! {campeao.nome} é o campeão.")
                self._emitir("fim_torneio", classificacao=self._classificacao_ordenada())
                # fecha (remove) a mesa ou reinicia para um novo torneio
                if self.fechar_ao_terminar:
                    self.remover = True
                else:
                    self._reiniciar_torneio()

    def _reiniciar_torneio(self):
        """Zera o torneio para uma nova rodada (mesmos jogadores humanos)."""
        self.torneio_encerrado = False
        self.classificacao = []
        self.entrantes = 0
        self.nivel_idx = 0
        nivel = nivel_por_indice(ESTRUTURA_PADRAO, 0)
        self.sb, self.bb, self.ante = nivel.sb, nivel.bb, nivel.ante
        for a in self.jogadores_sentados():
            a.stack = self.stack_inicial
        self._narrar("Novo torneio! Todos recomeçam com o stack inicial.")

    def _premiar(self, assento, colocacao):
        premios = calcular_premios(self.buy_in, self.entrantes) if self.buy_in else []
        premio = premios[colocacao - 1] if colocacao - 1 < len(premios) else 0
        registro = {
            "colocacao": colocacao, "nome": assento.nome,
            "jogador_id": assento.jogador_id, "premio": premio,
            "eh_bot": assento.eh_bot, "usuario_id": assento.usuario_id,
        }
        self.classificacao.append(registro)
        if premio > 0:
            self._narrar(f"{assento.nome} terminou em {colocacao}º e ganhou {premio}.")
            self.on_premiar(assento, premio, colocacao)
        else:
            self._narrar(f"{assento.nome} foi eliminado em {colocacao}º lugar.")

    def _classificacao_ordenada(self):
        return sorted(self.classificacao, key=lambda r: r["colocacao"])

    def _remover_assento(self, assento):
        for i, a in enumerate(self.assentos):
            if a is assento:
                self.assentos[i] = None
                return

    def _proximo_assento_ocupado(self, pos):
        for k in range(self.max_jogadores):
            cand = (pos + k) % self.max_jogadores
            if self.assentos[cand] is not None:
                return cand
        return pos

    def _assento_de(self, jogador_id):
        for a in self.assentos:
            if a and a.jogador_id == jogador_id:
                return a
        return None

    # ---------- histórico de mãos + relatório rodada-a-rodada ----------
    def _gravar_historico(self):
        """Guarda um registro da mão que acabou: cartas de cada um, board,
        vencedores e quanto cada jogador ganhou ou perdeu na rodada."""
        if not self.mao:
            return
        from engine.evaluator import descrever_melhor
        venc_ids = {v["jogador"] for v in self.mao.vencedores}
        ganho_por = {}
        for v in self.mao.vencedores:
            ganho_por[v["jogador"]] = ganho_por.get(v["jogador"], 0) + v["valor"]
        board = list(self.mao.board)
        jogadores = []
        for i, player in enumerate(self.mao.players):
            a = self.assentos[self._mapa_pos[i]] if i < len(self._mapa_pos) else None
            inicio = a.stack_inicio_mao if a else player.stack
            delta = player.stack - inicio
            # melhor combinação do jogador (mesmo se desistiu, mostramos as cartas)
            try:
                melhor = descrever_melhor(list(player.hole) + board) if player.hole else "Nada"
            except Exception:
                melhor = "Nada"
            jogadores.append({
                "jogador_id": player.id,
                "nome": player.nome,
                "eh_bot": bool(a and a.eh_bot),
                "cartas": [c.nome_falado for c in player.hole],
                "cartas_curto": [str(c) for c in player.hole],
                "foldou": player.foldou,
                "delta": delta,
                "venceu": player.id in venc_ids,
                "ganho": ganho_por.get(player.id, 0),
                "melhor": melhor,
            })
        self.historico.append({
            "numero": self.numero_mao,
            "nivel": (self.nivel_idx + 1) if self.torneio else None,
            "board": [c.nome_falado for c in board],
            "jogadores": jogadores,
        })

    def _humanos_conhecidos(self) -> list[str]:
        """Nomes de todos os humanos que aparecem no histórico (para 'todos')."""
        vistos = []
        for h in self.historico:
            for j in h["jogadores"]:
                if not j["eh_bot"] and j["nome"] not in vistos:
                    vistos.append(j["nome"])
        return vistos

    def _relatorio_de_um(self, nome: str) -> str:
        """Monta o texto do relatório rodada-a-rodada de UM jogador (pelo nome)."""
        linhas = [f"===== Relatório de {nome} ====="]
        rodadas_jogadas = 0
        ganhou, perdeu = [], []
        eliminado_em = None
        for h in self.historico:
            j = next((x for x in h["jogadores"] if x["nome"] == nome), None)
            if not j:
                continue
            rodadas_jogadas += 1
            cartas = " e ".join(j["cartas"]) if j["cartas"] else "sem cartas"
            num = h["numero"]
            nivel = f" (nível {h['nivel']})" if h["nivel"] else ""
            if j["delta"] > 0:
                ganhou.append(f"  - Rodada {num}{nivel}: ganhou {j['delta']} fichas "
                              f"com {cartas}. Mão: {j['melhor']}.")
            elif j["delta"] < 0:
                perdeu.append(f"  - Rodada {num}{nivel}: perdeu {abs(j['delta'])} fichas "
                              f"com {cartas}. Mão: {j['melhor']}.")
                eliminado_em = (num, cartas)  # a última perda vira a eliminação
        linhas.append(f"Você jogou {rodadas_jogadas} rodada(s).")
        linhas.append("")
        linhas.append(f"Rodadas que você GANHOU ({len(ganhou)}):")
        linhas += (ganhou or ["  - Nenhuma."])
        linhas.append("")
        linhas.append(f"Rodadas em que você PERDEU fichas ({len(perdeu)}):")
        linhas += (perdeu or ["  - Nenhuma."])
        if eliminado_em:
            linhas.append("")
            linhas.append(f"Você perdeu o jogo na rodada {eliminado_em[0]}, "
                          f"com {eliminado_em[1]}.")
        return "\n".join(linhas)

    def relatorio(self, jogador_id, escopo="proprio", alvos=None) -> str:
        """Gera o relatório em texto.

        escopo: 'proprio' (só quem pediu), 'selecionados' (nomes em `alvos`) ou
        'todos' (todos os humanos que jogaram).
        """
        meu_nome = self._nome(jogador_id)
        if escopo == "todos":
            nomes = self._humanos_conhecidos()
        elif escopo == "selecionados":
            nomes = [n for n in (alvos or []) if n in self._humanos_conhecidos()]
            if not nomes:
                nomes = [meu_nome]
        else:  # proprio
            nomes = [meu_nome]
        if not self.historico:
            return "Ainda não há rodadas registradas nesta mesa."
        partes = [self._relatorio_de_um(n) for n in nomes]
        return ("\n\n".join(partes)).strip()

    # ---------- narração acessível ----------
    def _narrar(self, texto):
        self.log_narracao.append(texto)

    def _nome(self, jogador_id):
        a = self._assento_de(jogador_id)
        return a.nome if a else jogador_id

    def _narrar_acao(self, evt):
        tipo = evt.get("tipo")
        nome = self._nome(evt.get("jogador", ""))
        if tipo == "fold":
            self._narrar(f"{nome} desistiu.")
        elif tipo == "check":
            self._narrar(f"{nome} passou.")
        elif tipo == "call":
            self._narrar(f"{nome} pagou {evt['valor']}.")
        elif tipo == "bet":
            self._narrar(f"{nome} apostou {evt['total']}.")
        elif tipo == "raise":
            self._narrar(f"{nome} aumentou para {evt['total']}.")
        elif tipo == "all_in":
            self._narrar(f"{nome} foi all-in com {evt['total']}.")

    def _narrar_board_novo(self, antes: int):
        """Narra automaticamente as cartas novas que apareceram no board (flop/turn/river)."""
        if not self.mao:
            return
        board = self.mao.board
        if len(board) >= 3 and antes < 3:
            cartas = ", ".join(self._descrever_carta(c) for c in board[:3])
            self._narrar(f"Flop: {cartas}.")
            self._emitir("street", street="flop")
        if len(board) >= 4 and antes < 4:
            self._narrar(f"Turn, carta que caiu: {self._descrever_carta(board[3])}.")
            self._emitir("street", street="turn")
        if len(board) >= 5 and antes < 5:
            self._narrar(f"River, carta que caiu: {self._descrever_carta(board[4])}.")
            self._emitir("street", street="river")

    def _descrever_carta(self, card):
        return card.nome_falado

    def _narrar_resultado(self):
        for v in self.mao.vencedores:
            nome = self._nome(v["jogador"])
            mao_desc = f" com {v['mao']}" if v.get("mao") else ""
            self._narrar(f"{nome} venceu {v['valor']}{mao_desc}.")

    def _emitir(self, msg, **kw):
        self.on_evento(self, {"msg": msg, "mesa": self.id,
                              "narracao": list(self.log_narracao), **kw})

    # ---------- estado ----------
    def estado(self, ponto_de_vista=None) -> dict:
        restante = self.tempo_restante()
        base = {
            "id": self.id, "nome": self.nome, "modo": self.modo,
            "sb": self.sb, "bb": self.bb, "ante": self.ante,
            "numero_mao": self.numero_mao, "mao_ativa": self.mao_ativa,
            "tempo_acao": self.tempo_acao,
            "deadline_ms": int(self.deadline * 1000) if self.deadline else None,
            "tempo_restante": restante,
            "torneio": self.torneio,
            "torneio_encerrado": self.torneio_encerrado,
            "auto_iniciar": self.auto_iniciar,
            "stack_inicial": self.stack_inicial,
            "assentos": [
                None if a is None else {
                    "jogador_id": a.jogador_id, "nome": a.nome,
                    "stack": a.stack, "eh_bot": a.eh_bot,
                }
                for a in self.assentos
            ],
            "narracao": list(self.log_narracao),
        }
        if self.torneio:
            nivel = nivel_por_indice(ESTRUTURA_PADRAO, self.nivel_idx)
            prox = max(0, int(self.duracao_nivel - (time.time() - self.inicio_nivel)))
            base["nivel"] = {"idx": self.nivel_idx + 1, "sb": nivel.sb,
                             "bb": nivel.bb, "ante": nivel.ante,
                             "proximo_em": prox if self.entrantes else self.duracao_nivel}
            base["entrantes"] = self.entrantes
            base["classificacao"] = self._classificacao_ordenada()
        if self.mao:
            base["mao"] = self.mao.estado_publico(ponto_de_vista)
            if self.mao.to_act is not None:
                base["acoes_validas"] = (
                    self.mao.acoes_validas()
                    if self.mao.players[self.mao.to_act].id == ponto_de_vista else {}
                )
        return base
