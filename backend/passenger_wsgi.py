import sys
import os

# Adiciona o diretório da aplicação ao PATH do Python
sys.path.insert(0, os.path.dirname(__file__))

from app.main import app as application