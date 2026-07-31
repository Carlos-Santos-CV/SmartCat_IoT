FROM python:3.10-slim

WORKDIR /app

# Instala dependências de sistema necessárias para o PostgreSQL
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Comando para iniciar o FastAPI e o Worker em paralelo no mesmo contêiner
CMD ["sh", "-c", "python -m app.worker & uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"]