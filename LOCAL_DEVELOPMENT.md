# 🚀 Desenvolvimento Local - Guia Rápido

## ✅ Setup Completo e Funcionando!

**Data**: 27 de dezembro de 2025  
**Status**: ✅ Backend rodando localmente com JWT funcional

---

## 🎯 O Que Foi Configurado

### **Arquivos Criados**
- ✅ `Dockerfile` - Imagem Python 3.11-slim otimizada
- ✅ `docker-compose.yml` - Orquestração do backend
- ✅ `.dockerignore` - Otimização do build Docker
- ✅ `.env.example` - Template de variáveis de ambiente
- ✅ `.env` - Variáveis configuradas (não versionado)
- ✅ `DOCKER_SETUP.md` - Documentação completa Docker
- ✅ `LOCAL_DEVELOPMENT.md` - Este guia rápido

### **Configuração do Ambiente**
```bash
# .env já configurado com:
✅ MONGO_URI (MongoDB Atlas remoto)
✅ JWT_SECRET (nQv?J/&dNnB*qni@@KonG)
✅ ENCRYPTION_KEY (Fernet key existente)
✅ FLASK_ENV=production
✅ FLASK_PORT=5000
```

---

## 🏃‍♂️ Como Rodar

### **Opção 1: Direto com Python** (Recomendado para desenvolvimento)

```bash
# 1. Instalar dependências (primeira vez)
cd /Users/charles.roberto/Documents/projects/crs-saturno/automatic
pip3 install -r requirements.txt

# 2. Rodar backend
python3 run.py

# Backend rodando em:
# http://localhost:5000
# http://127.0.0.1:5000
```

### **Opção 2: Com Docker** (se Rancher Desktop permitir)

```bash
# 1. Build e start
docker-compose up --build

# 2. Em background
docker-compose up -d

# 3. Ver logs
docker-compose logs -f backend

# 4. Parar
docker-compose down
```

---

## 🧪 Testes Realizados

### **1. Health Check** ✅
```bash
curl http://localhost:5000/health
```

**Resposta**:
```json
{
  "database": "connected",
  "message": "API rodando",
  "scheduler": {
    "next_snapshot": "2025-12-28T00:00:00-03:00",
    "running": true
  },
  "status": "ok",
  "strategy_worker": {
    "check_interval_minutes": 5,
    "dry_run_mode": false,
    "running": true
  }
}
```

### **2. JWT - Endpoint Sem Token** ✅ (401)
```bash
curl 'http://localhost:5000/api/v1/balances?user_id=test123'
```

**Resposta**:
```json
{
  "error": "No authorization header",
  "message": "Authorization header is required",
  "success": false
}
```

### **3. JWT - Login** ✅
```bash
curl -X POST http://localhost:5000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "google",
    "email": "test@example.com",
    "name": "Test User",
    "provider_user_id": "google_123"
  }'
```

**Resposta**:
```json
{
  "access_token": "eyJhbGci...",
  "refresh_token": "eyJhbGci...",
  "success": true,
  "user": {
    "email": "test@example.com",
    "id": "google_test_1766867048.953765",
    "name": "Test User",
    "provider": "google"
  }
}
```

### **4. JWT - Endpoint COM Token** ✅ (200)
```bash
TOKEN="eyJhbGci..."
curl 'http://localhost:5000/api/v1/balances?user_id=google_test_1766867048.953765' \
  -H "Authorization: Bearer $TOKEN"
```

**Resposta**:
```json
{
  "exchanges": [],
  "fetch_time": 0,
  "from_cache": false,
  "success": true,
  "timestamp": "2025-12-27T17:24:19.665147",
  "tokens_summary": {},
  "total_brl": 0.0,
  "total_exchanges": 0,
  "total_usd": 0.0,
  "user_id": "google_test_1766867048.953765"
}
```

---

## 🔧 Comandos Úteis

### **Backend Management**

```bash
# Ver processos rodando na porta 5000
lsof -i :5000

# Matar processo na porta 5000
kill -9 $(lsof -t -i:5000)

# Rodar em background
nohup python3 run.py > backend.log 2>&1 &

# Ver logs em tempo real
tail -f backend.log

# Parar backend em background
ps aux | grep "python.*run" | grep -v grep | awk '{print $2}' | xargs kill -9
```

### **MongoDB Atlas**

```bash
# Testar conexão
python3 -c "
from pymongo import MongoClient
client = MongoClient('mongodb+srv://automatic_user:NFRgE3pUXr2Wuaf2@clusterdbmongoatlas.mc74nzn.mongodb.net/')
print('✅ MongoDB conectado:', client.admin.command('ping'))
"
```

### **JWT Testing**

```bash
# Script completo de teste
# 1. Fazer login
RESPONSE=$(curl -s -X POST http://localhost:5000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"provider": "google", "email": "dev@test.com", "name": "Dev User"}')

# 2. Extrair token
TOKEN=$(echo $RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])")

# 3. Extrair user_id
USER_ID=$(echo $RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin)['user']['id'])")

# 4. Testar endpoint protegido
curl "http://localhost:5000/api/v1/balances?user_id=$USER_ID" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
```

---

## 📊 Status dos Serviços

### **Backend Flask** ✅
- **Status**: Rodando em http://localhost:5000
- **MongoDB**: Conectado ao Atlas (remoto)
- **JWT**: Funcionando perfeitamente
- **Scheduler**: Ativo (snapshots diários)
- **Strategy Worker**: Ativo (check a cada 5 min)

### **Funcionalidades Testadas** ✅
- ✅ Health check funcionando
- ✅ CORS habilitado
- ✅ MongoDB Atlas conectado
- ✅ JWT authentication (login, tokens, verificação)
- ✅ Endpoint protegido com JWT
- ✅ Validação de user_id
- ✅ Retorno 401 sem token
- ✅ Retorno 200 com token válido

---

## 🐛 Troubleshooting

### **Porta 5000 em uso**
```bash
# Verificar processo
lsof -i :5000

# Matar processo
kill -9 $(lsof -t -i:5000)
```

### **urllib3 Warning** (não afeta funcionamento)
```
NotOpenSSLWarning: urllib3 v2 only supports OpenSSL 1.1.1+
```
**Solução**: Ignorar warning ou downgrade urllib3:
```bash
pip3 install urllib3==1.26.20
```

### **Docker - Rancher Desktop blocked**
```
denied: image is not covered by allowed-images list
```
**Solução**: Usar Python direto (Opção 1) ou configurar Rancher Desktop

### **Module not found**
```bash
# Reinstalar dependências
pip3 install -r requirements.txt
```

---

## 📝 Variáveis de Ambiente Importantes

```bash
# MongoDB (Atlas remoto)
MONGO_URI=mongodb+srv://automatic_user:NFRgE3pUXr2Wuaf2@...

# JWT
JWT_SECRET=nQv?J/&dNnB*qni@@KonG
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRES=86400  # 24 horas
JWT_REFRESH_TOKEN_EXPIRES=2592000  # 30 dias

# Flask
FLASK_ENV=production
FLASK_DEBUG=False
FLASK_HOST=0.0.0.0
FLASK_PORT=5000

# Encryption (Fernet)
ENCRYPTION_KEY=iGga1jJmU7cIK7cQlIKY7Hw533ZXXtd-ibba3TxwGR0=
```

---

## 🚀 Próximos Passos

### **1. Frontend Integration**
- Implementar `AuthContext` seguindo `JWT_INTEGRATION_GUIDE.md`
- Configurar interceptor JWT no `api.ts`
- Criar `LoginScreen` (OAuth Google + Apple)
- Testar fluxo completo de autenticação

### **2. Deploy Production**
- Configurar `JWT_SECRET` como env var no Render.com
- Verificar MongoDB Atlas whitelist
- Configurar domínio e HTTPS
- Setup CI/CD (GitHub Actions)

### **3. Monitoring**
- Configurar logs estruturados
- Adicionar métricas (Prometheus?)
- Setup alertas (errors, performance)
- Dashboard de monitoring

---

## 📖 Documentação Relacionada

- **`JWT_INTEGRATION_GUIDE.md`** - Guia completo de integração JWT (frontend)
- **`JWT_IMPLEMENTATION_COMPLETE.md`** - Resumo da implementação backend
- **`DOCKER_SETUP.md`** - Documentação detalhada Docker
- **`API_VALIDATION_GUIDE.md`** - Lista completa de endpoints

---

## ✅ Checklist de Desenvolvimento

- [x] Backend rodando localmente
- [x] MongoDB Atlas conectado
- [x] JWT authentication funcionando
- [x] 30+ endpoints protegidos
- [x] Health check configurado
- [x] Scheduler ativo
- [x] Strategy worker rodando
- [x] Testes manuais realizados
- [ ] Frontend AuthContext implementado
- [ ] OAuth Google + Apple configurado
- [ ] Testes E2E
- [ ] Deploy production

---

**Última Atualização**: 27/12/2025  
**Versão**: 1.0.0  
**Status**: ✅ Backend Local FUNCIONANDO!

**Commits Criados**:
- `2d4d453` - feat: adiciona setup Docker completo
- `66bfddd` - chore: atualiza .gitignore

**Backend Testado**:
- ✅ Health: http://localhost:5000/health
- ✅ Login: POST /api/v1/auth/login
- ✅ Protected: GET /api/v1/balances (com JWT)
