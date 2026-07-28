"""Torneio multi-mesa (MTT).

Coordena várias mesas (objetos Mesa) ao mesmo tempo:
- inscrição (com número-alvo de participantes; o resto é preenchido com bots);
- distribuição aleatória dos jogadores nas mesas (9-max);
- blinds sincronizados entre todas as mesas;
- rebuy (recompra) durante os primeiros níveis e add-on (fichas extras);
- reposicionamento (balanceamento): junta jogadores e quebra mesas conforme as
  eliminações, até a mesa final;
- premiação (top ~15%).

Cada Mesa é criada em modo NÃO-autogerenciado (torneio=False) para não cuidar de
blinds/eliminação sozinha — quem cuida disso é o Torneio.
"""
from __future__ import annotations

import math
import random
import time
import uuid

from engine.torneio import ESTRUTURA_PADRAO, nivel_por_indice, premios_mtt

NOMES_BOTS = ["Ana", "Bruno", "Carla", "Diego", "Elisa", "Felipe", "Gabi", "Hugo",
              "Ivo", "Joana", "Kaue", "Lia", "Marco", "Nina", "Otto", "Paula",
              "Rui", "Sara", "Tiago", "Ugo", "Val", "Wesley", "Xuxa", "Yuri", "Zeca"]


class Torneio:
    def __init__(self, id, nome, num_participantes, stack_inicial, buy_in,
                 jogadores_por_mesa=9, tempo_acao=20, duracao_nivel=180,
                 rebuy_permitido=False, rebuy_ate_nivel=3,
                 addon_permitido=False, addon_valor=0, addon_fichas=0,
                 criar_mesa=None, remover_mesa=None, on_creditar=None, on_debitar=None):
        self.id = id
        self.nome = nome
        self.num_participantes = max(2, int(num_participantes))
        self.stack_inicial = int(stack_inicial)
        self.buy_in = int(buy_in)
        self.jogadores_por_mesa = max(2, min(int(jogadores_por_mesa), 9))
        self.tempo_acao = int(tempo_acao)
        self.duracao_nivel = int(duracao_nivel)
        self.rebuy_permitido = bool(rebuy_permitido)
        self.rebuy_ate_nivel = int(rebuy_ate_nivel)         # rebuy nos níveis < este (1-index)
        self.addon_permitido = bool(addon_permitido)
        self.addon_valor = int(addon_valor)
        self.addon_fichas = int(addon_fichas)

        # callbacks para o gerenciador (criar/remover mesas, mexer na carteira)
        self.criar_mesa = criar_mesa or (lambda nome, maxj: None)
        self.remover_mesa = remover_mesa or (lambda mid: None)
        self.on_creditar = on_creditar or (lambda usuario_id, valor, desc: None)
        self.on_debitar = on_debitar or (lambda usuario_id, valor, desc: None)

        self.estado = "inscricao"       # inscricao | andamento | intervalo | encerrado
        self.inscritos: list[dict] = [] # {jogador_id, nome, usuario_id, eh_bot}
        self.mesas: dict[str, object] = {}   # id -> Mesa
        self.jogador_mesa: dict[str, str] = {}  # jogador_id -> mesa_id (quem ainda joga)
        self.nivel_idx = 0
        self.inicio_nivel = None
        self.classificacao: list[dict] = []
        self.total_rebuys = 0
        self.total_addons = 0
        self.rebuy_pendente: dict[str, float] = {}   # jogador_id -> deadline
        self.addon_ate = None            # epoch até quando o add-on é oferecido
        self.addon_feito: set[str] = set()
        self.remover = False             # sinaliza remoção do torneio ao gerenciador

    # ---------- inscrição / início ----------
    def inscrever(self, jogador_id, nome, usuario_id=None):
        if self.estado != "inscricao":
            raise ValueError("as inscrições já foram encerradas")
        if any(i["jogador_id"] == jogador_id for i in self.inscritos):
            return
        humanos = [i for i in self.inscritos if not i["eh_bot"]]
        if len(humanos) >= self.num_participantes:
            raise ValueError("torneio lotado")
        self.inscritos.append({"jogador_id": jogador_id, "nome": nome,
                               "usuario_id": usuario_id, "eh_bot": False})

    def num_humanos(self):
        return len([i for i in self.inscritos if not i["eh_bot"]])

    def iniciar(self):
        if self.estado != "inscricao":
            return False
        # completa com bots até o número de participantes
        random.shuffle(NOMES_BOTS)
        bi = 0
        while len(self.inscritos) < self.num_participantes:
            nome = NOMES_BOTS[bi % len(NOMES_BOTS)] + (f" {bi // len(NOMES_BOTS) + 1}"
                                                       if bi >= len(NOMES_BOTS) else "")
            self.inscritos.append({"jogador_id": f"bot-{uuid.uuid4().hex[:6]}",
                                   "nome": nome, "usuario_id": None, "eh_bot": True})
            bi += 1

        random.shuffle(self.inscritos)
        n_mesas = max(1, math.ceil(len(self.inscritos) / self.jogadores_por_mesa))
        mesas = []
        for k in range(n_mesas):
            m = self.criar_mesa(f"{self.nome} - Mesa {k + 1}", self.jogadores_por_mesa)
            m.tempo_acao = self.tempo_acao
            self.mesas[m.id] = m
            mesas.append(m)
        # distribuição em rodízio (mantém as mesas equilibradas)
        for idx, jog in enumerate(self.inscritos):
            m = mesas[idx % n_mesas]
            m.sentar(jog["jogador_id"], jog["nome"], self.stack_inicial,
                     eh_bot=jog["eh_bot"], usuario_id=jog["usuario_id"])
            self.jogador_mesa[jog["jogador_id"]] = m.id

        self.estado = "andamento"
        self.nivel_idx = 0
        self.inicio_nivel = time.time()
        self._aplicar_blinds()
        return True

    def _aplicar_blinds(self):
        nivel = nivel_por_indice(ESTRUTURA_PADRAO, self.nivel_idx)
        for m in self.mesas.values():
            m.sb, m.bb, m.ante = nivel.sb, nivel.bb, nivel.ante

    # ---------- economia ----------
    def _pool(self):
        return (len(self.inscritos) + self.total_rebuys) * self.buy_in \
            + self.total_addons * self.addon_valor

    def _no_periodo_rebuy(self):
        return self.rebuy_permitido and (self.nivel_idx + 1) < self.rebuy_ate_nivel

    # ---------- tick principal ----------
    def tick(self) -> bool:
        if self.estado not in ("andamento", "intervalo"):
            return False
        mudou = False
        agora = time.time()

        # avanço de nível
        if (self.inicio_nivel and agora - self.inicio_nivel >= self.duracao_nivel
                and self.nivel_idx < len(ESTRUTURA_PADRAO) - 1):
            nivel_antes = self.nivel_idx
            self.nivel_idx += 1
            self.inicio_nivel = agora
            self._aplicar_blinds()
            mudou = True
            # ao terminar o período de rebuy, abre a janela de add-on
            if (self.addon_permitido and (nivel_antes + 1) < self.rebuy_ate_nivel
                    and (self.nivel_idx + 1) >= self.rebuy_ate_nivel):
                self._abrir_addon(agora)

        # add-on (janela): bots fazem sozinhos; encerra a janela no fim
        if self.estado == "intervalo":
            mudou |= self._processar_addon(agora)

        mudou |= self._processar_bustados(agora)
        mudou |= self._rebalancear()
        mudou |= self._checar_fim()
        return mudou

    # ---------- rebuy / eliminação ----------
    def _fazer_rebuy(self, mesa, assento):
        assento.stack = self.stack_inicial
        self.total_rebuys += 1
        self.rebuy_pendente.pop(assento.jogador_id, None)
        if assento.usuario_id:
            self.on_debitar(assento.usuario_id, self.buy_in, f"Rebuy torneio {self.nome}")
        mesa._narrar(f"{assento.nome} fez rebuy e voltou com {self.stack_inicial} fichas.")

    def rebuy(self, jogador_id):
        """Ação de rebuy de um humano (chamada pelo app)."""
        mid = self.jogador_mesa.get(jogador_id)
        if not mid:
            return False
        mesa = self.mesas.get(mid)
        a = mesa and mesa._assento_de(jogador_id)
        if a and a.stack <= 0 and self._no_periodo_rebuy():
            self._fazer_rebuy(mesa, a)
            return True
        return False

    def _eliminar(self, mesa, assento):
        colocacao = len(self.jogador_mesa)     # inclui ele; 1º a cair = último lugar
        premios = premios_mtt(self._pool(), len(self.inscritos))
        premio = premios[colocacao - 1] if 0 < colocacao <= len(premios) else 0
        self.classificacao.append({
            "colocacao": colocacao, "nome": assento.nome, "jogador_id": assento.jogador_id,
            "premio": premio, "eh_bot": assento.eh_bot, "usuario_id": assento.usuario_id,
        })
        if premio > 0 and assento.usuario_id:
            self.on_creditar(assento.usuario_id, premio, colocacao)
        mesa._narrar(f"{assento.nome} foi eliminado em {colocacao}º lugar" +
                     (f" e ganhou {premio}." if premio else "."))
        mesa.levantar(jogador_id=assento.jogador_id)
        self.jogador_mesa.pop(assento.jogador_id, None)

    def _processar_bustados(self, agora):
        mudou = False
        for mesa in list(self.mesas.values()):
            if mesa.mao_ativa:
                continue
            for a in list(mesa.jogadores_sentados()):
                if a.stack > 0:
                    continue
                if self._no_periodo_rebuy():
                    if a.eh_bot:
                        self._fazer_rebuy(mesa, a); mudou = True; continue
                    dl = self.rebuy_pendente.get(a.jogador_id)
                    if dl is None:
                        self.rebuy_pendente[a.jogador_id] = agora + 25
                        mesa._emitir("rebuy_oferta", jogador_id=a.jogador_id, valor=self.buy_in)
                        mudou = True
                        continue
                    if agora < dl:
                        continue           # ainda dentro do prazo de rebuy
                    self.rebuy_pendente.pop(a.jogador_id, None)
                self._eliminar(mesa, a); mudou = True
        return mudou

    # ---------- add-on ----------
    def _abrir_addon(self, agora):
        self.estado = "intervalo"
        self.addon_ate = agora + 30       # 30s de janela de add-on
        self.addon_feito = set()
        for m in self.mesas.values():
            m.pausada = True
            m._narrar(f"Intervalo! Add-on disponível: +{self.addon_fichas} fichas.")
            m._emitir("addon_oferta", fichas=self.addon_fichas, valor=self.addon_valor)

    def addon(self, jogador_id):
        """Ação de add-on de um humano."""
        if self.estado != "intervalo" or jogador_id in self.addon_feito:
            return False
        mid = self.jogador_mesa.get(jogador_id)
        mesa = self.mesas.get(mid) if mid else None
        a = mesa and mesa._assento_de(jogador_id)
        if a and a.stack > 0:
            a.stack += self.addon_fichas
            self.total_addons += 1
            self.addon_feito.add(jogador_id)
            if a.usuario_id:
                self.on_debitar(a.usuario_id, self.addon_valor, f"Add-on torneio {self.nome}")
            return True
        return False

    def _processar_addon(self, agora):
        # bots fazem add-on automaticamente
        for mesa in self.mesas.values():
            for a in mesa.jogadores_sentados():
                if a.eh_bot and a.stack > 0 and a.jogador_id not in self.addon_feito:
                    a.stack += self.addon_fichas
                    self.total_addons += 1
                    self.addon_feito.add(a.jogador_id)
        if self.addon_ate and agora >= self.addon_ate:
            self.estado = "andamento"
            self.addon_ate = None
            for m in self.mesas.values():
                m.pausada = False
                m._narrar("Fim do intervalo. Voltando a jogar!")
            return True
        return False

    # ---------- reposicionamento (balanceamento) ----------
    def _n_ativos(self, mesa):
        return len([a for a in mesa.jogadores_sentados() if a.stack > 0])

    def _mover(self, jogador_id, origem, destino):
        a = origem._assento_de(jogador_id)
        if not a:
            return
        stack = origem.levantar(jogador_id)
        destino.sentar(a.jogador_id, a.nome, stack, eh_bot=a.eh_bot, usuario_id=a.usuario_id)
        self.jogador_mesa[jogador_id] = destino.id
        # avisa o jogador (humano) para ir para a nova mesa
        origem._emitir("mudanca_mesa", jogador_id=jogador_id, nova_mesa=destino.id)

    def _rebalancear(self):
        if self.estado != "andamento":
            return False
        mudou = False
        # remove mesas sem ninguém
        for mid in [mid for mid, m in self.mesas.items() if not m.jogadores_sentados()]:
            self.remover_mesa(mid)
            self.mesas.pop(mid, None)
            mudou = True

        ativas = [m for m in self.mesas.values()]
        if len(ativas) <= 1:
            return mudou
        total = sum(self._n_ativos(m) for m in ativas)
        mesas_necessarias = max(1, math.ceil(total / self.jogadores_por_mesa))

        # quebra a menor mesa (entre mãos) se dá para juntar em menos mesas
        if len(ativas) > mesas_necessarias:
            candidatas = sorted([m for m in ativas if not m.mao_ativa and self._n_ativos(m) > 0],
                                key=self._n_ativos)
            if candidatas:
                quebrar = candidatas[0]
                destinos = sorted([m for m in ativas if m is not quebrar],
                                  key=self._n_ativos)
                for a in list(quebrar.jogadores_sentados()):
                    dest = min(destinos, key=self._n_ativos)
                    if self._n_ativos(dest) < self.jogadores_por_mesa:
                        self._mover(a.jogador_id, quebrar, dest)
                        mudou = True
                if not quebrar.jogadores_sentados():
                    self.remover_mesa(quebrar.id)
                    self.mesas.pop(quebrar.id, None)
                return mudou

        # equilíbrio: move 1 jogador da maior para a menor se a diferença >= 2
        maior = max(ativas, key=self._n_ativos)
        menor = min(ativas, key=self._n_ativos)
        if self._n_ativos(maior) - self._n_ativos(menor) >= 2 and not maior.mao_ativa:
            a = next((x for x in maior.jogadores_sentados() if x.stack > 0), None)
            if a:
                self._mover(a.jogador_id, maior, menor)
                mudou = True
        return mudou

    # ---------- fim ----------
    def _checar_fim(self):
        if self.estado == "encerrado":
            return False
        if len(self.jogador_mesa) == 1:
            jid = next(iter(self.jogador_mesa))
            campeao = None
            for m in self.mesas.values():
                campeao = m._assento_de(jid)
                if campeao:
                    break
            premios = premios_mtt(self._pool(), len(self.inscritos))
            premio = premios[0] if premios else 0
            nome = campeao.nome if campeao else jid
            self.classificacao.append({"colocacao": 1, "nome": nome, "jogador_id": jid,
                                       "premio": premio,
                                       "eh_bot": campeao.eh_bot if campeao else True,
                                       "usuario_id": campeao.usuario_id if campeao else None})
            if premio > 0 and campeao and campeao.usuario_id:
                self.on_creditar(campeao.usuario_id, premio, 1)
            self.estado = "encerrado"
            self.jogador_mesa.clear()
            self.remover = True
            return True
        return False

    # ---------- estado para o cliente ----------
    def classificacao_ordenada(self):
        return sorted(self.classificacao, key=lambda r: r["colocacao"])

    def resumo(self):
        nivel = nivel_por_indice(ESTRUTURA_PADRAO, self.nivel_idx)
        return {
            "id": self.id, "nome": self.nome, "estado": self.estado,
            "num_participantes": self.num_participantes,
            "inscritos": len(self.inscritos), "humanos": self.num_humanos(),
            "vivos": len(self.jogador_mesa),
            "nivel": {"idx": self.nivel_idx + 1, "sb": nivel.sb, "bb": nivel.bb, "ante": nivel.ante},
            "premio_total": self._pool(),
            "classificacao": self.classificacao_ordenada(),
            "mesas": len(self.mesas),
            "stack_inicial": self.stack_inicial, "buy_in": self.buy_in,
            "rebuy": self.rebuy_permitido, "addon": self.addon_permitido,
        }
