import sys
import os

# Adiciona o diretório da aplicação ao PATH do Python
sys.path.insert(0, os.path.dirname(__file__))

from app.main import app as fastapi_app

# Este host usa um Passenger que só suporta WSGI clássico (confirmado pelo
# erro "missing 1 required positional argument: 'send'"), então o app
# ASGI do FastAPI precisa ser convertido via a2wsgi.
from a2wsgi import ASGIMiddleware
application = ASGIMiddleware(fastapi_app)
