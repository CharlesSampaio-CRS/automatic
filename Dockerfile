FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV MONGODB_URI=mongodb+srv://automatic_user:NFRgE3pUXr2Wuaf2@clusterdbmongoatlas.mc74nzn.mongodb.net/?appName=ClusterDbMongoAtlas
ENV MONGODB_DATABASE=MultExchange
ENV FLASK_ENV=production
ENV FLASK_DEBUG=False
ENV FLASK_HOST=0.0.0.0
ENV FLASK_PORT=5000
ENV ENCRYPTION_KEY=iGga1jJmU7cIK7cQlIKY7Hw533ZXXtd-ibba3TxwGR0=

EXPOSE 8085
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8085/health || exit 1
CMD ["gunicorn", "--workers=2", "--timeout=120", "--bind", "0.0.0.0:8085", "src.api.main:app"]
