"""Carteira: saldo, depósito, saque, buy-in e histórico.

Valores em CENTAVOS (inteiros) para evitar erros de ponto flutuante.
Saldo = soma de todos os lançamentos do usuário. Nunca guardamos saldo à parte.

MODO SIMULADO: depósito/saque não movem dinheiro real. Para produção, plugue um
gateway (PIX/cartão) em `depositar`/`sacar` e só registre o lançamento após a
confirmação do provedor. Exige licença de jogo e KYC — fora do escopo do código.
"""
from __future__ import annotations

from . import db


class ErroCarteira(Exception):
    pass


def saldo(usuario_id: int) -> int:
    conn = db.conexao()
    row = conn.execute(
        "SELECT COALESCE(SUM(valor), 0) AS s FROM lancamentos WHERE usuario_id=?",
        (usuario_id,),
    ).fetchone()
    return int(row["s"])


def _lancar(usuario_id: int, tipo: str, valor: int, descricao: str = "", ref: str = "") -> int:
    conn = db.conexao()
    cur = conn.execute(
        "INSERT INTO lancamentos (usuario_id, tipo, valor, descricao, ref) "
        "VALUES (?,?,?,?,?) RETURNING id",
        (usuario_id, tipo, valor, descricao, ref),
    )
    novo_id = cur.fetchone()["id"]
    conn.commit()
    return novo_id


def depositar(usuario_id: int, valor: int, descricao: str = "Depósito (simulado)") -> int:
    if valor <= 0:
        raise ErroCarteira("valor de depósito deve ser positivo")
    if valor > 5_000_000:  # limite de sanidade: R$ 50.000
        raise ErroCarteira("valor acima do limite por transação")
    _lancar(usuario_id, "deposito", valor, descricao)
    return saldo(usuario_id)


def sacar(usuario_id: int, valor: int, descricao: str = "Saque (simulado)") -> int:
    if valor <= 0:
        raise ErroCarteira("valor de saque deve ser positivo")
    if valor > saldo(usuario_id):
        raise ErroCarteira("saldo insuficiente")
    _lancar(usuario_id, "saque", -valor, descricao)
    return saldo(usuario_id)


def debitar_buy_in(usuario_id: int, valor: int, mesa: str) -> int:
    if valor <= 0:
        raise ErroCarteira("buy-in inválido")
    if valor > saldo(usuario_id):
        raise ErroCarteira("saldo insuficiente para o buy-in")
    _lancar(usuario_id, "buy_in", -valor, f"Buy-in mesa {mesa}", ref=mesa)
    return saldo(usuario_id)


def creditar_cash_out(usuario_id: int, valor: int, mesa: str) -> int:
    """Devolve fichas da mesa ao saldo (ao sair da mesa)."""
    if valor < 0:
        raise ErroCarteira("cash-out inválido")
    if valor > 0:
        _lancar(usuario_id, "cash_out", valor, f"Saída da mesa {mesa}", ref=mesa)
    return saldo(usuario_id)


def creditar_premio(usuario_id: int, valor: int, mesa: str, colocacao: int) -> int:
    """Credita prêmio de torneio ao saldo do jogador."""
    if valor > 0:
        _lancar(usuario_id, "premio", valor,
                f"Prêmio {colocacao}º lugar (torneio {mesa})", ref=mesa)
    return saldo(usuario_id)


def extrato(usuario_id: int, limite: int = 50) -> list[dict]:
    conn = db.conexao()
    rows = conn.execute(
        "SELECT tipo, valor, descricao, criado_em FROM lancamentos "
        "WHERE usuario_id=? ORDER BY id DESC LIMIT ?",
        (usuario_id, limite),
    ).fetchall()
    return [dict(r) for r in rows]


def formatar_reais(centavos: int) -> str:
    """12345 -> 'R$ 123,45' (para leitor de tela e UI)."""
    sinal = "-" if centavos < 0 else ""
    c = abs(centavos)
    return f"{sinal}R$ {c // 100},{c % 100:02d}"
