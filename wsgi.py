"""Ponto de entrada para servidores de produção (gunicorn).

Faz o monkey-patch do gevent ANTES de importar o app, para que WebSockets e o
timer (thread de fundo) funcionem de forma cooperativa.

Rodar em produção:
    gunicorn -k gevent -w 1 wsgi:app --bind 0.0.0.0:$PORT

Importante: use -w 1 (um worker). O estado das mesas fica em memória; múltiplos
workers não compartilhariam as mesas. Para escalar, seria preciso mover o estado
para um serviço externo (ex.: Redis) — fora do escopo atual.
"""
from gevent import monkey

monkey.patch_all()

from server.app import criar_app  # noqa: E402

app = criar_app()
