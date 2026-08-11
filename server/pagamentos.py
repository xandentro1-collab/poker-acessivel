"""Loja e pagamentos: assinatura Premium e compra de fichas (recarga de saldo).

Modelo NÃO jogo de azar: as fichas compradas servem só para JOGAR e NÃO têm saque.

Funciona em modo SANDBOX (sem gateway configurado) para testar o fluxo completo
de ponta a ponta sem dinheiro real. Quando um gateway (Mercado Pago, Asaas, ...)
for configurado por variáveis de ambiente, a criação da cobrança (PIX/checkout) e
a confirmação por webhook passam a ser reais — o resto do código continua igual.
"""
import os
import time
from datetime import datetime

from . import db, social, wallet

# "" (vazio) = modo sandbox (simulado). Ex. futuro: PAGAMENTO_GATEWAY=mercadopago
GATEWAY = os.environ.get("PAGAMENTO_GATEWAY", "").strip().lower()

# Catálogo. Valores em centavos. Fichas: 'credito' é quanto entra na carteira.
PRODUTOS = {
    "fichas_5":    {"tipo": "fichas", "nome": "Recarga de R$ 5",  "preco": 500,  "credito": 500,
                    "desc": "Cinco reais em fichas para jogar."},
    "fichas_20":   {"tipo": "fichas", "nome": "Recarga de R$ 20", "preco": 2000, "credito": 2200,
                    "desc": "Vinte reais em fichas, com 2 reais de bônus."},
    "fichas_50":   {"tipo": "fichas", "nome": "Recarga de R$ 50", "preco": 5000, "credito": 5800,
                    "desc": "Cinquenta reais em fichas, com 8 reais de bônus."},
    "premium_mes": {"tipo": "assinatura", "nome": "Premium mensal", "preco": 1990, "dias": 30,
                    "desc": "Assinatura Premium por 30 dias: mesas e torneios privados sem "
                            "limite e apoio ao projeto."},
}


def modo() -> str:
    return GATEWAY or "sandbox"


def eh_sandbox() -> bool:
    return not GATEWAY


def _int(s, padrao=0):
    try:
        return int(float(s))
    except (TypeError, ValueError):
        return padrao


def _data_txt(ts) -> str:
    try:
        return datetime.fromtimestamp(int(ts)).strftime("%d/%m/%Y")
    except (OverflowError, OSError, ValueError):
        return ""


def listar_produtos() -> list:
    saida = []
    for pid, p in PRODUTOS.items():
        item = {"id": pid, "tipo": p["tipo"], "nome": p["nome"],
                "preco": p["preco"], "desc": p["desc"]}
        if p["tipo"] == "fichas":
            item["credito"] = p["credito"]
        if p["tipo"] == "assinatura":
            item["dias"] = p["dias"]
        saida.append(item)
    return saida


def criar_cobranca(usuario_id, produto_id) -> dict:
    """Cria uma cobrança pendente. No sandbox devolve um link para 'simular' o
    pagamento; com gateway real, devolveria o PIX / a página de checkout."""
    p = PRODUTOS.get(produto_id)
    if not p:
        return {"ok": False, "erro": "produto inválido"}
    conn = db.conexao()
    row = conn.execute(
        "INSERT INTO cobrancas (usuario_id, produto, tipo, valor, status, gateway) "
        "VALUES (?, ?, ?, ?, 'pendente', ?) RETURNING id",
        (usuario_id, produto_id, p["tipo"], p["preco"], modo())).fetchone()
    conn.commit()
    cid = row["id"]
    resp = {"ok": True, "cobranca_id": cid, "produto": produto_id, "nome": p["nome"],
            "valor": p["preco"], "sandbox": eh_sandbox()}
    if eh_sandbox():
        resp["simular_url"] = f"/api/pagamentos/simular/{cid}"
    else:
        # Aqui entraria a chamada real ao gateway (gerar PIX/checkout). A preencher
        # quando as chaves de API forem configuradas.
        resp["pix"] = None
        resp["checkout_url"] = None
    return resp


def confirmar_pagamento(cobranca_id, ref_externa="") -> dict:
    """Confirma o pagamento de uma cobrança e aplica o efeito (creditar fichas ou
    ativar assinatura). Idempotente: não credita duas vezes."""
    conn = db.conexao()
    row = conn.execute("SELECT * FROM cobrancas WHERE id=?", (cobranca_id,)).fetchone()
    if not row:
        return {"ok": False, "erro": "cobrança não encontrada"}
    if row["status"] == "paga":
        return {"ok": True, "ja_paga": True, "tipo": row["tipo"]}
    conn.execute(f"UPDATE cobrancas SET status='paga', ref_externa=?, pago_em={db._NOW} "
                 "WHERE id=?", (ref_externa, cobranca_id))
    conn.commit()
    return _aplicar(row)


def _aplicar(row) -> dict:
    p = PRODUTOS.get(row["produto"])
    uid = row["usuario_id"]
    if not p:
        return {"ok": True, "tipo": row["tipo"]}
    if p["tipo"] == "fichas":
        novo = wallet.creditar_compra(uid, p["credito"], ref=f"cobranca:{row['id']}")
        return {"ok": True, "tipo": "fichas", "credito": p["credito"],
                "saldo": novo, "saldo_fmt": wallet.formatar_reais(novo),
                "credito_fmt": wallet.formatar_reais(p["credito"])}
    if p["tipo"] == "assinatura":
        ate = ativar_assinatura(uid, p["dias"])
        return {"ok": True, "tipo": "assinatura", "ate": ate, "ate_txt": _data_txt(ate)}
    return {"ok": True, "tipo": row["tipo"]}


def ativar_assinatura(uid, dias) -> int:
    agora = int(time.time())
    atual = _int(social.get_pref(uid, "assinatura_ate", "0"))
    base = max(agora, atual)   # se já tem assinatura, soma a partir do fim
    ate = base + int(dias) * 86400
    social.set_pref(uid, "assinatura_ate", str(ate))
    return ate


def assinatura_estado(uid) -> dict:
    ate = _int(social.get_pref(uid, "assinatura_ate", "0"))
    ativa = ate > time.time()
    return {"ativa": ativa, "ate": ate, "ate_txt": _data_txt(ate) if ativa else ""}
