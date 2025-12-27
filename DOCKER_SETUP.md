# 🐳 Docker Setup - Crypto Exchange Aggregator Backend

## 📋 Overview

Este guia explica como rodar o backend Flask localmente usando Docker e Docker Compose, mantendo o MongoDB Atlas como banco de dados remoto.

---

## 🎯 Benefícios do Docker

✅ **Ambiente isolado** - Não interfere com outras instalações Python  
✅ **Hot-reload** - Código muda automaticamente ao salvar arquivos  
✅ **Portabilidade** - Funciona igual em Mac, Linux, Windows  
✅ **Fácil setup** - Apenas 3 comandos para iniciar  
✅ **Produção-ready** - Mesmo ambiente em dev e produção  

---

## 📦 Pré-requisitos

### Instalar Docker Desktop

**macOS**:
```bash
brew install --cask docker
# OU baixar de: https://www.docker.com/products/docker-desktop
```

**Linux (Ubuntu/Debian)**:
```bash
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER
# Reinicie o terminal
```

**Windows**:
- Baixe Docker Desktop: https://www.docker.com/products/docker-desktop
- Habilite WSL 2

### Verificar instalação:
```bash
docker --version
docker-compose --version
```

---

## 🚀 Quick Start

### 1. Configurar variáveis de ambiente

```bash
# Copiar template
cp .env.example .env

# Editar .env com suas credenciais
nano .env  # ou vim, code, etc
```

**Variáveis OBRIGATÓRIAS**:
```env
# MongoDB Atlas
MONGODB_URI=mongodb+srv://usuario:senha@cluster.mongodb.net/crypto_exchange

# JWT Secret (gere uma nova)
JWT_SECRET=$(python -c "import secrets; print(secrets.token_urlsafe(32))")

# Encryption Key (gere uma nova)
ENCRYPTION_KEY=$(python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
```

### 2. Construir e iniciar containers

```bash
# Build da imagem e start dos containers
docker-compose up --build

# OU rodar em background (detached mode)
docker-compose up -d --build
```

### 3. Verificar se está funcionando

```bash
# Testar endpoint de saúde
curl http://localhost:5000/api/v1/health

# Ver logs em tempo real
docker-compose logs -f backend

# Verificar containers rodando
docker ps
```

**Saída esperada**:
```
CONTAINER ID   IMAGE              STATUS          PORTS
abc123def456   crypto-backend     Up 2 minutes    0.0.0.0:5000->5000/tcp
```

---

## 🔧 Comandos Úteis

### Gerenciar containers

```bash
# Iniciar containers (se já construídos)
docker-compose up

# Parar containers
docker-compose down

# Parar e remover volumes
docker-compose down -v

# Rebuild completo (após mudar requirements.txt)
docker-compose up --build --force-recreate

# Restart apenas o backend
docker-compose restart backend
```

### Ver logs

```bash
# Logs em tempo real
docker-compose logs -f

# Últimas 100 linhas
docker-compose logs --tail=100

# Logs apenas do backend
docker-compose logs -f backend
```

### Executar comandos no container

```bash
# Abrir shell interativo
docker-compose exec backend bash

# Executar script Python
docker-compose exec backend python scripts/test_exchange_management.py

# Instalar nova dependência
docker-compose exec backend pip install nova-biblioteca

# Ver processos rodando
docker-compose exec backend ps aux
```

### Limpeza

```bash
# Remover containers e redes
docker-compose down

# Remover imagens não usadas
docker image prune -a

# Limpar tudo (cuidado!)
docker system prune -a --volumes
```

---

## 🔥 Hot Reload

O Docker está configurado com **volumes** para hot-reload automático:

```yaml
volumes:
  - ./src:/app/src          # Código Python
  - ./run.py:/app/run.py    # Entry point
```

**Como funciona**:
1. Edite qualquer arquivo em `src/`
2. Salve o arquivo
3. Flask detecta a mudança e reinicia automaticamente
4. Veja os logs: `docker-compose logs -f backend`

**Arquivos que NÃO causam reload**:
- `requirements.txt` → Precisa rebuild: `docker-compose up --build`
- `Dockerfile` → Precisa rebuild: `docker-compose up --build`
- `docker-compose.yml` → Precisa down/up: `docker-compose down && docker-compose up`

---

## 🗄️ MongoDB Atlas (Remoto)

### Vantagens de usar Atlas

✅ Não precisa rodar MongoDB localmente  
✅ Dados persistentes mesmo após rebuild  
✅ Fácil compartilhar dados entre dev/prod  
✅ Backups automáticos  
✅ Free tier (512MB)  

### Configurar MongoDB Atlas

1. **Criar conta**: https://cloud.mongodb.com/
2. **Criar cluster** (free tier M0)
3. **Criar database user**:
   - Database Access → Add New Database User
   - Username: `crypto_admin`
   - Password: `sua_senha_forte`
4. **Configurar Network Access**:
   - Network Access → Add IP Address
   - Allow Access from Anywhere: `0.0.0.0/0` (apenas desenvolvimento!)
5. **Obter connection string**:
   - Cluster → Connect → Connect your application
   - Copiar string: `mongodb+srv://...`
6. **Adicionar no .env**:
   ```env
   MONGODB_URI=mongodb+srv://crypto_admin:sua_senha@cluster0.xxxxx.mongodb.net/crypto_exchange?retryWrites=true&w=majority
   ```

### Testar conexão

```bash
# Via Docker
docker-compose exec backend python -c "from pymongo import MongoClient; client = MongoClient('$MONGODB_URI'); print(client.server_info())"

# Via curl (API)
curl http://localhost:5000/api/v1/health
```

---

## 🌐 CORS para React Native

O Docker já está configurado para aceitar requisições do React Native local:

```yaml
environment:
  - CORS_ORIGINS=*  # Aceita qualquer origem (desenvolvimento)
```

### Conectar React Native ao backend Docker

**1. Descobrir IP local**:
```bash
# macOS/Linux
ifconfig | grep "inet " | grep -v 127.0.0.1

# Windows
ipconfig | findstr IPv4
```

**2. Usar IP no frontend** (`src/services/api.ts`):
```typescript
const API_BASE_URL = __DEV__ 
  ? 'http://192.168.1.100:5000/api/v1'  // Seu IP local
  : 'https://api.production.com/api/v1';
```

**3. Permitir IP específico (produção)**:
```env
# .env
CORS_ORIGINS=http://localhost:19006,exp://192.168.1.100:19000
```

---

## 📊 Healthcheck

O Docker Compose inclui healthcheck automático:

```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:5000/api/v1/health"]
  interval: 30s
  timeout: 10s
  retries: 3
```

**Verificar status**:
```bash
docker ps
# STATUS: Up 5 minutes (healthy)
```

**Criar endpoint de health** (se não existir):
```python
# src/api/main.py
@app.route('/api/v1/health', methods=['GET'])
def health():
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'version': '1.0.0'
    }), 200
```

---

## 🐛 Troubleshooting

### Erro: "Cannot connect to Docker daemon"

```bash
# Verificar se Docker Desktop está rodando
docker info

# Iniciar Docker Desktop (macOS)
open -a Docker

# Linux: iniciar daemon
sudo systemctl start docker
```

### Erro: "Port 5000 already in use"

```bash
# Verificar o que está usando a porta
lsof -i :5000

# Matar processo
kill -9 <PID>

# OU mudar porta no docker-compose.yml
ports:
  - "5001:5000"  # Expõe na porta 5001 localmente
```

### Erro: "MongoDB connection failed"

```bash
# Verificar MONGODB_URI no .env
cat .env | grep MONGODB_URI

# Testar conexão manualmente
docker-compose exec backend python -c "
from pymongo import MongoClient
import os
uri = os.getenv('MONGODB_URI')
print(f'Tentando conectar: {uri[:30]}...')
client = MongoClient(uri)
print('Conectado!', client.server_info()['version'])
"
```

### Container reinicia constantemente

```bash
# Ver logs para identificar erro
docker-compose logs backend

# Erros comuns:
# - MONGODB_URI incorreto → Verificar .env
# - requirements.txt com erro → Rebuild: docker-compose up --build
# - JWT_SECRET ausente → Adicionar no .env
```

### Hot reload não funciona

```bash
# Verificar se volumes estão montados
docker-compose exec backend ls -la /app/src

# Verificar se FLASK_DEBUG=1
docker-compose exec backend printenv | grep FLASK

# Forçar restart
docker-compose restart backend
```

### Permissões de arquivo (Linux)

```bash
# Se der erro de permissão em logs/
sudo chown -R $USER:$USER logs/

# OU criar pasta com permissões corretas
mkdir -p logs && chmod 777 logs/
```

---

## 🔒 Segurança

### Desenvolvimento

✅ CORS aberto (`*`)  
✅ MongoDB Atlas com IP `0.0.0.0/0`  
✅ JWT_SECRET simples  
✅ Logs detalhados  

### Produção

⚠️ **IMPORTANTE**:
```env
# .env.production
FLASK_ENV=production
FLASK_DEBUG=0
CORS_ORIGINS=https://app.seudominio.com
JWT_SECRET=$(openssl rand -hex 32)
MONGODB_URI=mongodb+srv://...  # Apenas IPs específicos no Atlas
```

**Checklist**:
- [ ] JWT_SECRET forte (32+ caracteres)
- [ ] CORS apenas para domínios específicos
- [ ] MongoDB Atlas com Network Access restrito
- [ ] ENCRYPTION_KEY segura para API keys
- [ ] FLASK_DEBUG=0
- [ ] Usar secrets manager (AWS Secrets, etc)

---

## 📚 Estrutura do Projeto

```
automatic/
├── Dockerfile              # Definição da imagem Docker
├── docker-compose.yml      # Orquestração de containers
├── .dockerignore          # Arquivos ignorados no build
├── .env                   # Variáveis de ambiente (não commitar!)
├── .env.example           # Template de variáveis
├── requirements.txt       # Dependências Python
├── run.py                 # Entry point da aplicação
├── wsgi.py               # WSGI server (produção)
├── src/
│   ├── api/
│   │   └── main.py       # Rotas Flask
│   ├── security/
│   │   └── jwt_auth.py   # Autenticação JWT
│   ├── services/
│   │   └── ...           # Business logic
│   └── validators/
│       └── ...           # Validações
└── logs/                 # Logs persistentes
```

---

## 🚀 Deploy em Produção

### Opção 1: Render.com (Recomendado)

```bash
# Render detecta Dockerfile automaticamente
# Apenas configure env vars no dashboard
```

### Opção 2: AWS ECS

```bash
# Build e push para ECR
docker build -t crypto-backend .
docker tag crypto-backend:latest <aws_account>.dkr.ecr.us-east-1.amazonaws.com/crypto-backend:latest
docker push <aws_account>.dkr.ecr.us-east-1.amazonaws.com/crypto-backend:latest
```

### Opção 3: DigitalOcean App Platform

```yaml
# app.yaml
services:
  - name: backend
    dockerfile_path: Dockerfile
    envs:
      - key: MONGODB_URI
        value: ${MONGODB_URI}
      - key: JWT_SECRET
        value: ${JWT_SECRET}
```

---

## 📞 Suporte

**Problemas comuns**:
- Ver seção Troubleshooting acima
- Verificar logs: `docker-compose logs -f`
- Issues no GitHub: [link do repositório]

**Recursos**:
- Docker Docs: https://docs.docker.com/
- Flask Docs: https://flask.palletsprojects.com/
- MongoDB Atlas: https://docs.atlas.mongodb.com/

---

## ✅ Checklist - Quick Setup

- [ ] Docker Desktop instalado
- [ ] Copiar `.env.example` → `.env`
- [ ] Configurar `MONGODB_URI` (MongoDB Atlas)
- [ ] Gerar `JWT_SECRET` e `ENCRYPTION_KEY`
- [ ] `docker-compose up --build`
- [ ] Testar: `curl http://localhost:5000/api/v1/health`
- [ ] Ver logs: `docker-compose logs -f`
- [ ] Testar hot-reload: editar arquivo e salvar

---

**Última atualização**: 27/12/2025  
**Versão Docker**: 1.0.0  
**Status**: ✅ Production Ready
