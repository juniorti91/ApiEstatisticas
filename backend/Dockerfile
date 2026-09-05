# Imagem enxuta o suficiente pra rodar bem no free tier da Koyeb (0.1 vCPU / 512MB RAM)
FROM python:3.12-slim

WORKDIR /app

# Dependencias do sistema minimas (aiosqlite/greenlet nao precisam de nada
# alem do compilador C basico em algumas plataformas - manter cache leve)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

# A Koyeb injeta a variavel PORT automaticamente e espera que o serviço
# escute nela - por isso o CMD le $PORT em vez de fixar 8000. O valor
# "8000" depois do ":-" e so um fallback pra rodar local com "docker run"
# sem passar PORT.
ENV PORT=8000
EXPOSE 8000

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
