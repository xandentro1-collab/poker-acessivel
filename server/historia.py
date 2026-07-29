"""Histórico de mãos no banco (persistente) e estatísticas por usuário.

A Mesa (motor do jogo) NÃO fala com o banco: ela chama um callback, e é a camada
do app que grava aqui. Assim os testes do motor não tocam no banco.
"""
from __future__ import annotations

from . import db


def salvar_mao(mesa_id: str, torneio_id: str | None, numero: int,
               board: list[str], jogadores: list[dict]) -> None:
    """Grava uma mão: uma linha em `maos` + uma por jogador em `mao_jogadores`.

    `jogadores` são os dicts do registro (com apelido, usuario_id, cartas, delta,
    venceu, ganho, melhor, foldou, eh_bot)."""
    conn = db.conexao()
    cur = conn.execute(
        "INSERT INTO maos (mesa_id, torneio_id, numero, board) VALUES (?,?,?,?)",
        (mesa_id, torneio_id, numero, " ".join(board or [])))
    row = cur.fetchone() if hasattr(cur, "fetchone") else None
    # id da mão recém-criada (RETURNING no PG; lastrowid no SQLite)
    if row and "id" in (row.keys() if hasattr(row, "keys") else {}):
        mao_id = row["id"]
    else:
        mao_id = cur.lastrowid
    for j in jogadores:
        conn.execute(
            "INSERT INTO mao_jogadores (mao_id, usuario_id, apelido, cartas, foldou, "
            "delta, venceu, ganho, melhor) VALUES (?,?,?,?,?,?,?,?,?)",
            (mao_id, j.get("usuario_id"), j.get("nome") or j.get("jogador_id"),
             " e ".join(j.get("cartas") or []), 1 if j.get("foldou") else 0,
             int(j.get("delta") or 0), 1 if j.get("venceu") else 0,
             int(j.get("ganho") or 0), j.get("melhor")))
    conn.commit()


def stats_usuario(usuario_id: int) -> dict:
    """Estatísticas acumuladas do usuário (todas as mesas/torneios)."""
    conn = db.conexao()
    row = conn.execute(
        "SELECT COUNT(*) AS jogadas, "
        "COALESCE(SUM(venceu),0) AS ganhas, "
        "COALESCE(SUM(delta),0) AS saldo, "
        "COALESCE(MAX(ganho),0) AS maior_pote "
        "FROM mao_jogadores WHERE usuario_id=?", (usuario_id,)).fetchone()
    jogadas = row["jogadas"] or 0
    ganhas = row["ganhas"] or 0
    pct = round(100.0 * ganhas / jogadas, 1) if jogadas else 0.0
    return {
        "maos_jogadas": jogadas,
        "maos_ganhas": ganhas,
        "aproveitamento": pct,      # % de mãos ganhas
        "saldo_fichas": row["saldo"] or 0,
        "maior_pote": row["maior_pote"] or 0,
    }


def salvar_mao_registro(mesa_id: str, torneio_id: str | None, registro: dict) -> None:
    """Atalho: grava a partir do dict de registro produzido pela Mesa."""
    salvar_mao(mesa_id, torneio_id, registro.get("numero"),
               registro.get("board") or [], registro.get("jogadores") or [])
