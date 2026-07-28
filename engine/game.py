"""Máquina de estados de uma mão de Texas Hold'em No-Limit.

Responsável por: posições (botão/blinds), rodadas de aposta (preflop/flop/turn/
river), regras de raise mínimo, all-in, cálculo de side pots e showdown.

Multi-mesa/persistência ficam em camadas acima. Aqui é lógica pura e testável.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from .cards import Card, Deck
from .evaluator import evaluate_best, descrever_forca, descrever_melhor


class Street(Enum):
    PREFLOP = "preflop"
    FLOP = "flop"
    TURN = "turn"
    RIVER = "river"
    SHOWDOWN = "showdown"
    ENCERRADA = "encerrada"


class Acao(Enum):
    FOLD = "fold"
    CHECK = "check"
    CALL = "call"
    BET = "bet"
    RAISE = "raise"
    ALL_IN = "all_in"


@dataclass
class Player:
    id: str
    nome: str
    stack: int
    hole: list[Card] = field(default_factory=list)
    aposta_rodada: int = 0     # apostado na rodada atual
    total_mao: int = 0         # total comprometido na mão inteira
    foldou: bool = False
    all_in: bool = False
    agiu_na_rodada: bool = False
    sentado_fora: bool = False  # sem stack / esperando

    @property
    def ativo(self) -> bool:
        """Ainda pode tomar decisões (não foldou, não all-in, tem ficha)."""
        return not self.foldou and not self.all_in and not self.sentado_fora

    @property
    def na_mao(self) -> bool:
        """Ainda disputa o pote (não foldou)."""
        return not self.foldou and not self.sentado_fora


@dataclass
class Pot:
    valor: int
    elegiveis: list[str]  # ids que disputam este pote


class MaoDePoker:
    """Uma única mão. Crie, chame `iniciar()`, depois `aplicar_acao()` em loop."""

    def __init__(
        self,
        players: list[Player],
        button_pos: int,
        small_blind: int,
        big_blind: int,
        deck: Deck | None = None,
        ante: int = 0,
    ) -> None:
        if len([p for p in players if not p.sentado_fora]) < 2:
            raise ValueError("são necessários ao menos 2 jogadores com stack")
        self.players = players
        self.button_pos = button_pos
        self.sb = small_blind
        self.bb = big_blind
        self.ante = ante
        self.deck = deck or Deck()
        self.board: list[Card] = []
        self.street = Street.PREFLOP
        self.pots: list[Pot] = []
        self.aposta_atual = 0        # maior aposta da rodada corrente
        self.min_raise = big_blind   # incremento mínimo de raise
        self.to_act: int | None = None
        self.ultimo_agressor: int | None = None
        self.log: list[dict] = []
        self.vencedores: list[dict] = []
        self.showdown_info: list[dict] = []

    # ---------- utilidades de posição ----------
    def _ordem_a_partir(self, start: int) -> list[int]:
        n = len(self.players)
        return [(start + i) % n for i in range(n)]

    def _proximo_ativo(self, start: int) -> int | None:
        for idx in self._ordem_a_partir(start):
            if self.players[idx].ativo:
                return idx
        return None

    def _jogadores_na_mao(self) -> list[int]:
        return [i for i, p in enumerate(self.players) if p.na_mao]

    # ---------- início ----------
    def iniciar(self) -> None:
        n = len(self.players)
        ativos = [i for i in range(n) if not self.players[i].sentado_fora]
        heads_up = len(ativos) == 2

        # Antes
        if self.ante:
            for i in ativos:
                pago = min(self.ante, self.players[i].stack)
                self._committar(i, pago)

        # Blinds. Heads-up: botão é o small blind.
        if heads_up:
            sb_pos = self.button_pos
            bb_pos = self._proximo_na_lista(ativos, self.button_pos)
        else:
            sb_pos = self._proximo_na_lista(ativos, self.button_pos)
            bb_pos = self._proximo_na_lista(ativos, sb_pos)

        self._postar_blind(sb_pos, self.sb)
        self._postar_blind(bb_pos, self.bb)
        self.aposta_atual = self.bb
        self.min_raise = self.bb

        # Cartas: 2 para cada, começando à esquerda do botão
        for i in self._ordem_a_partir(self.button_pos + 1):
            if not self.players[i].sentado_fora:
                self.players[i].hole = self.deck.draw(2)

        # Quem age primeiro no preflop: à esquerda do BB (ou o botão no heads-up)
        primeiro = self._proximo_ativo((bb_pos + 1) % n)
        self.to_act = primeiro
        self.ultimo_agressor = bb_pos  # o BB "fechou" a aposta inicial
        self._registrar("inicio", street="preflop")
        self._checar_rodada_trivial()

    def _proximo_na_lista(self, ativos: list[int], pos: int) -> int:
        n = len(self.players)
        for i in range(1, n + 1):
            cand = (pos + i) % n
            if cand in ativos:
                return cand
        raise RuntimeError("sem próximo jogador ativo")

    def _postar_blind(self, pos: int, valor: int) -> None:
        p = self.players[pos]
        pago = min(valor, p.stack)
        self._committar(pos, pago)
        self._registrar("blind", jogador=p.id, valor=pago)

    def _committar(self, pos: int, valor: int) -> None:
        """Move `valor` do stack para o pote comprometido do jogador."""
        p = self.players[pos]
        valor = min(valor, p.stack)
        p.stack -= valor
        p.aposta_rodada += valor
        p.total_mao += valor
        if p.stack == 0 and valor > 0:
            p.all_in = True

    # ---------- ações ----------
    def acoes_validas(self) -> dict:
        """Ações legais para o jogador da vez, com limites (para UI/atalhos)."""
        if self.to_act is None:
            return {}
        p = self.players[self.to_act]
        falta = self.aposta_atual - p.aposta_rodada
        acoes: dict = {}
        acoes["fold"] = True
        if falta <= 0:
            acoes["check"] = True
        else:
            acoes["call"] = min(falta, p.stack)
        # bet/raise
        if p.stack > falta:
            if self.aposta_atual == 0:
                # bet: mínimo = big blind (ou resto do stack)
                min_bet = min(self.bb, p.stack)
                acoes["bet"] = {"min": min_bet, "max": p.stack}
            else:
                # raise: precisa cobrir o call + min_raise
                min_total = self.aposta_atual + self.min_raise
                custo_min = min_total - p.aposta_rodada
                if p.stack >= custo_min:
                    acoes["raise"] = {"min": min_total, "max": p.aposta_rodada + p.stack}
                else:
                    # só dá para all-in (raise incompleto)
                    acoes["all_in"] = p.aposta_rodada + p.stack
        acoes["all_in"] = p.aposta_rodada + p.stack
        return acoes

    def aplicar_acao(self, jogador_id: str, acao: str, valor: int | None = None) -> dict:
        """Processa uma ação. `valor` = aposta TOTAL da rodada (não o incremento).

        Retorna dict com o evento resultante. Levanta ValueError se ilegal.
        """
        if self.to_act is None:
            raise ValueError("não há ação pendente (mão encerrada?)")
        p = self.players[self.to_act]
        if p.id != jogador_id:
            raise ValueError(f"não é a vez de {jogador_id}; é de {p.id}")

        acao = acao.lower()
        falta = self.aposta_atual - p.aposta_rodada
        evento: dict

        if acao == "fold":
            p.foldou = True
            evento = self._registrar("fold", jogador=p.id)

        elif acao == "check":
            if falta > 0:
                raise ValueError("não pode dar check: há aposta a pagar")
            evento = self._registrar("check", jogador=p.id)

        elif acao == "call":
            pago = min(falta, p.stack)
            if pago <= 0:
                raise ValueError("nada para pagar; use check")
            self._committar(self.to_act, pago)
            evento = self._registrar("call", jogador=p.id, valor=pago)

        elif acao in ("bet", "raise", "all_in"):
            evento = self._processar_aposta(acao, valor)
        else:
            raise ValueError(f"ação desconhecida: {acao}")

        p.agiu_na_rodada = True
        self._avancar(evento)
        return evento

    def _processar_aposta(self, acao: str, valor: int | None) -> dict:
        p = self.players[self.to_act]  # type: ignore[index]
        if acao == "all_in":
            total = p.aposta_rodada + p.stack
        else:
            if valor is None:
                raise ValueError("bet/raise exige valor (aposta total da rodada)")
            total = valor
        if total <= p.aposta_rodada:
            raise ValueError("aposta precisa aumentar seu valor na rodada")
        custo = total - p.aposta_rodada
        if custo > p.stack:
            raise ValueError("fichas insuficientes")

        incremento = total - self.aposta_atual
        eh_all_in = custo == p.stack
        # Raise válido precisa alcançar min_raise, exceto all-in incompleto
        if total > self.aposta_atual and not eh_all_in:
            if incremento < self.min_raise:
                raise ValueError(
                    f"raise mínimo é {self.min_raise}; total mínimo {self.aposta_atual + self.min_raise}"
                )

        self._committar(self.to_act, custo)  # type: ignore[arg-type]

        # Atualiza aposta corrente e min_raise apenas se foi um raise "cheio"
        if total > self.aposta_atual:
            if incremento >= self.min_raise:
                self.min_raise = incremento
            self.aposta_atual = total
            self.ultimo_agressor = self.to_act
            # Reabre a rodada: todos os outros precisam agir de novo
            for i, jog in enumerate(self.players):
                if i != self.to_act and jog.ativo:
                    jog.agiu_na_rodada = False

        nome_evt = "all_in" if eh_all_in else acao
        return self._registrar(nome_evt, jogador=p.id, valor=custo, total=total)

    # ---------- avanço de rodada ----------
    def _rodada_completa(self) -> bool:
        ativos = [p for p in self.players if p.ativo]
        if not ativos:
            return True
        # Todos os ativos precisam ter agido e igualado a aposta corrente
        for p in ativos:
            if not p.agiu_na_rodada:
                return False
            if p.aposta_rodada != self.aposta_atual:
                return False
        return True

    def _avancar(self, evento: dict) -> None:
        na_mao = self._jogadores_na_mao()
        if len(na_mao) == 1:
            self._encerrar_por_desistencia(na_mao[0])
            return

        if self._rodada_completa():
            self._proxima_street()
        else:
            prox = self._proximo_ativo((self.to_act + 1) % len(self.players))  # type: ignore[operator]
            self.to_act = prox
            if prox is None:
                # ninguém mais pode agir (todos all-in) -> vai ao showdown
                self._resolver_ate_showdown()

    def _checar_rodada_trivial(self) -> None:
        """Se todos já estão all-in no início, resolve direto."""
        if self._proximo_ativo(self.to_act or 0) is None:
            self._resolver_ate_showdown()

    def _proxima_street(self) -> None:
        # Zera apostas da rodada
        for p in self.players:
            p.aposta_rodada = 0
            p.agiu_na_rodada = False
        self.aposta_atual = 0
        self.min_raise = self.bb

        if self.street == Street.PREFLOP:
            self.board += self.deck.draw(3)
            self.street = Street.FLOP
        elif self.street == Street.FLOP:
            self.board += self.deck.draw(1)
            self.street = Street.TURN
        elif self.street == Street.TURN:
            self.board += self.deck.draw(1)
            self.street = Street.RIVER
        elif self.street == Street.RIVER:
            self._showdown()
            return

        self._registrar("street", street=self.street.value)
        # Primeiro a agir pós-flop: à esquerda do botão
        prox = self._proximo_ativo((self.button_pos + 1) % len(self.players))
        self.to_act = prox
        self.ultimo_agressor = None
        if prox is None or len([p for p in self.players if p.ativo]) < 1:
            self._resolver_ate_showdown()

    def _resolver_ate_showdown(self) -> None:
        """Distribui board restante quando não há mais ação possível."""
        self.to_act = None
        while len(self.board) < 5:
            faltam = 5 - len(self.board)
            if self.street == Street.PREFLOP:
                self.board += self.deck.draw(3)
                self.street = Street.FLOP
            elif self.street == Street.FLOP:
                self.board += self.deck.draw(1)
                self.street = Street.TURN
            elif self.street == Street.TURN:
                self.board += self.deck.draw(1)
                self.street = Street.RIVER
            else:
                self.board += self.deck.draw(faltam)
        self._showdown()

    # ---------- side pots e showdown ----------
    def _construir_pots(self) -> list[Pot]:
        """Calcula pote principal e side pots a partir de total_mao de cada um."""
        contrib = {p.id: p.total_mao for p in self.players if p.total_mao > 0}
        pots: list[Pot] = []
        niveis = sorted(set(contrib.values()))
        anterior = 0
        for nivel in niveis:
            camada = nivel - anterior
            participantes = [pid for pid, v in contrib.items() if v >= nivel]
            valor = camada * len(participantes)
            # elegíveis a ganhar: os que não foldaram
            elegiveis = [pid for pid in participantes
                         if not self._player(pid).foldou]
            if valor > 0:
                pots.append(Pot(valor=valor, elegiveis=elegiveis))
            anterior = nivel
        # une potes consecutivos com mesmos elegíveis
        unidos: list[Pot] = []
        for pot in pots:
            if unidos and unidos[-1].elegiveis == pot.elegiveis:
                unidos[-1].valor += pot.valor
            else:
                unidos.append(pot)
        return unidos

    def _player(self, pid: str) -> Player:
        return next(p for p in self.players if p.id == pid)

    def _showdown(self) -> None:
        self.street = Street.SHOWDOWN
        self.to_act = None
        self.pots = self._construir_pots()
        resultados: list[dict] = []

        for pot in self.pots:
            elegiveis = [pid for pid in pot.elegiveis]
            if not elegiveis:
                continue
            if len(elegiveis) == 1:
                ganhadores = elegiveis
            else:
                forcas = {}
                for pid in elegiveis:
                    p = self._player(pid)
                    forca, _ = evaluate_best(p.hole + self.board)
                    forcas[pid] = forca
                melhor = max(forcas.values())
                ganhadores = [pid for pid, f in forcas.items() if f == melhor]

            base, resto = divmod(pot.valor, len(ganhadores))
            # ordena por posição para dar o odd chip ao mais próximo à esquerda do botão
            ganhadores_ord = sorted(
                ganhadores,
                key=lambda pid: (self._indice(pid) - self.button_pos) % len(self.players),
            )
            for j, pid in enumerate(ganhadores_ord):
                premio = base + (1 if j < resto else 0)
                self._player(pid).stack += premio
                desc = None
                if len(elegiveis) > 1:
                    forca, _ = evaluate_best(self._player(pid).hole + self.board)
                    desc = descrever_forca(forca)
                resultados.append({"jogador": pid, "valor": premio, "mao": desc})

        self.vencedores = resultados
        # resumo do showdown: mão e cartas de TODOS que não desistiram (para narrar)
        venc_ids = {r["jogador"] for r in resultados}
        self.showdown_info = []
        for p in self.players:
            if not p.foldou and p.hole:
                forca, _ = evaluate_best(p.hole + self.board)
                self.showdown_info.append({
                    "jogador": p.id, "nome": p.nome,
                    "mao": descrever_forca(forca),
                    "cartas": [c.codigo for c in p.hole],
                    "venceu": p.id in venc_ids,
                })
        self.showdown_info.sort(key=lambda x: not x["venceu"])  # vencedores primeiro
        self.street = Street.ENCERRADA
        self._registrar("showdown", resultados=resultados)

    def _indice(self, pid: str) -> int:
        return next(i for i, p in enumerate(self.players) if p.id == pid)

    def _encerrar_por_desistencia(self, idx_vencedor: int) -> None:
        self.pots = self._construir_pots()
        total = sum(p.valor for p in self.pots)
        vencedor = self.players[idx_vencedor]
        vencedor.stack += total
        self.to_act = None
        self.street = Street.ENCERRADA
        self.vencedores = [{"jogador": vencedor.id, "valor": total, "mao": None}]
        self._registrar("vitoria_sem_showdown", jogador=vencedor.id, valor=total)

    # ---------- log / estado ----------
    def _registrar(self, tipo: str, **kw) -> dict:
        evt = {"tipo": tipo, **kw}
        self.log.append(evt)
        return evt

    @property
    def pote_total(self) -> int:
        return sum(p.total_mao for p in self.players)

    @property
    def encerrada(self) -> bool:
        return self.street == Street.ENCERRADA

    def estado_publico(self, ponto_de_vista: str | None = None) -> dict:
        """Snapshot para enviar ao cliente. Esconde cartas alheias."""
        def cartas_visiveis(p: Player):
            revela = (ponto_de_vista == p.id) or self.encerrada
            if revela and p.hole and not p.foldou:
                return [c.codigo for c in p.hole]
            return ["??", "??"] if p.hole else []

        # melhor combinação atual do jogador que está vendo (para o atalho "G")
        minha_mao = None
        if ponto_de_vista:
            eu = next((p for p in self.players if p.id == ponto_de_vista), None)
            if eu and eu.hole and not eu.foldou:
                minha_mao = descrever_melhor(eu.hole + self.board)

        return {
            "street": self.street.value,
            "board": [c.codigo for c in self.board],
            "pote_total": self.pote_total,
            "aposta_atual": self.aposta_atual,
            "min_raise": self.min_raise,
            "to_act": self.players[self.to_act].id if self.to_act is not None else None,
            "button": self.players[self.button_pos].id,
            "minha_mao": minha_mao,
            "jogadores": [
                {
                    "id": p.id, "nome": p.nome, "stack": p.stack,
                    "aposta_rodada": p.aposta_rodada, "foldou": p.foldou,
                    "all_in": p.all_in, "cartas": cartas_visiveis(p),
                }
                for p in self.players
            ],
            "vencedores": self.vencedores,
            "showdown": self.showdown_info,
            "encerrada": self.encerrada,
        }
