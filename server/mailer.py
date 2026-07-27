"""Envio de e-mail (boas-vindas) via SMTP.

É OPCIONAL: se as variáveis de ambiente SMTP não estiverem configuradas, o envio
é simplesmente ignorado (o cadastro continua funcionando normalmente).

Configuração (variáveis de ambiente):
    SMTP_HOST   ex.: smtp.gmail.com
    SMTP_PORT   ex.: 587 (padrão)
    SMTP_USER   o e-mail que envia (ex.: seu@gmail.com)
    SMTP_PASS   a senha/token de app do e-mail
    SMTP_FROM   (opcional) remetente exibido; padrão = SMTP_USER

Segurança: NUNCA enviamos a senha do usuário por e-mail.
"""
from __future__ import annotations

import os
import smtplib
import ssl
import threading
from email.message import EmailMessage


def _cfg() -> dict:
    return {
        "host": os.environ.get("SMTP_HOST", "").strip(),
        "port": int(os.environ.get("SMTP_PORT", "587") or "587"),
        "user": os.environ.get("SMTP_USER", "").strip(),
        "pass": os.environ.get("SMTP_PASS", "").strip(),
        "from": (os.environ.get("SMTP_FROM") or os.environ.get("SMTP_USER", "")).strip(),
    }


def configurado() -> bool:
    c = _cfg()
    return bool(c["host"] and c["user"] and c["pass"])


def _enviar(destino: str, assunto: str, corpo_txt: str, corpo_html: str | None = None) -> None:
    c = _cfg()
    msg = EmailMessage()
    msg["Subject"] = assunto
    msg["From"] = c["from"]
    msg["To"] = destino
    msg.set_content(corpo_txt)
    if corpo_html:
        msg.add_alternative(corpo_html, subtype="html")
    ctx = ssl.create_default_context()
    with smtplib.SMTP(c["host"], c["port"], timeout=20) as s:
        s.starttls(context=ctx)
        s.login(c["user"], c["pass"])
        s.send_message(msg)


def enviar_boas_vindas(email: str, apelido: str, saldo_fmt: str, link: str) -> bool:
    """Envia (em segundo plano) o e-mail de boas-vindas. Retorna False se SMTP off."""
    if not configurado():
        return False

    assunto = "Bem-vindo ao Poker Acessível!"
    txt = (
        f"Olá, {apelido}!\n\n"
        f"Sua conta no Poker Acessível foi criada com sucesso.\n\n"
        f"Seus dados de cadastro:\n"
        f"  • Apelido: {apelido}\n"
        f"  • E-mail: {email}\n"
        f"  • Saldo inicial de treino: {saldo_fmt}\n\n"
        f"Acesse a plataforma em: {link}\n\n"
        f"Por segurança, sua senha NÃO é enviada por e-mail. Guarde-a com você.\n\n"
        f"Bom jogo!\n— Equipe Poker Acessível"
    )
    html = (
        f"<div style='font-family:Arial,sans-serif;font-size:15px;color:#16233f'>"
        f"<h2>Olá, {apelido}! 🎉</h2>"
        f"<p>Sua conta no <strong>Poker Acessível</strong> foi criada com sucesso.</p>"
        f"<p><strong>Seus dados de cadastro:</strong></p>"
        f"<ul>"
        f"<li>Apelido: <strong>{apelido}</strong></li>"
        f"<li>E-mail: <strong>{email}</strong></li>"
        f"<li>Saldo inicial de treino: <strong>{saldo_fmt}</strong></li>"
        f"</ul>"
        f"<p><a href='{link}' style='background:#ffcf33;color:#1a1400;padding:10px 18px;"
        f"border-radius:8px;text-decoration:none;font-weight:bold'>Entrar na plataforma</a></p>"
        f"<p style='color:#888;font-size:13px'>Por segurança, sua senha não é enviada por "
        f"e-mail. Guarde-a com você.</p>"
        f"<p>Bom jogo!<br>— Equipe Poker Acessível</p>"
        f"</div>"
    )

    def _job():
        try:
            _enviar(email, assunto, txt, html)
        except Exception:
            pass  # e-mail é best-effort; nunca quebra o cadastro

    threading.Thread(target=_job, daemon=True).start()
    return True


def enviar_codigo_verificacao(email: str, apelido: str, codigo: str) -> bool:
    """Envia o código de verificação. O código fica SOZINHO em uma linha, sem mais
    nada, para o leitor de tela ler com clareza. Retorna False se SMTP não está on."""
    if not configurado():
        return False

    assunto = "Seu código de verificação — Poker Acessível"
    # ATENÇÃO: a linha do código contém APENAS o código, sem prefixo nem sufixo.
    txt = (
        f"Olá, {apelido}!\n\n"
        f"Seu código de verificação é:\n\n"
        f"{codigo}\n\n"
        f"Digite este código na plataforma para ativar sua conta. "
        f"Ele expira em 15 minutos.\n\n"
        f"Se não foi você que se cadastrou, ignore este e-mail.\n"
        f"— Equipe Poker Acessível"
    )
    html = (
        f"<div style='font-family:Arial,sans-serif;font-size:15px;color:#16233f'>"
        f"<p>Olá, {apelido}!</p>"
        f"<p>Seu código de verificação é:</p>"
        # o código isolado, sozinho em sua própria linha/parágrafo
        f"<p style='font-size:30px;font-weight:bold;letter-spacing:4px;margin:16px 0'>"
        f"{codigo}</p>"
        f"<p>Digite este código na plataforma para ativar sua conta. "
        f"Ele expira em 15 minutos.</p>"
        f"<p style='color:#888;font-size:13px'>Se não foi você que se cadastrou, "
        f"ignore este e-mail.</p>"
        f"<p>— Equipe Poker Acessível</p>"
        f"</div>"
    )

    def _job():
        try:
            _enviar(email, assunto, txt, html)
        except Exception:
            pass

    threading.Thread(target=_job, daemon=True).start()
    return True
