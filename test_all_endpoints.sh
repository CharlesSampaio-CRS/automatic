#!/bin/bash

# Script para testar todos os endpoints GET da API
BASE_URL="http://localhost:8000"
API_URL="${BASE_URL}/api/v1"

# Cores para output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "=========================================="
echo "  Testando Endpoints GET da API"
echo "=========================================="
echo ""

# Função para testar endpoint
test_endpoint() {
    local method=$1
    local endpoint=$2
    local description=$3
    
    echo -e "${YELLOW}Testando:${NC} ${method} ${endpoint}"
    echo -e "${YELLOW}Descrição:${NC} ${description}"
    
    response=$(curl -s -w "\n%{http_code}" "${endpoint}")
    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | sed '$d')
    
    if [ "$http_code" -eq 200 ]; then
        echo -e "${GREEN}✓ Status: ${http_code}${NC}"
        echo "$body" | python3 -m json.tool 2>/dev/null | head -20
    else
        echo -e "${RED}✗ Status: ${http_code}${NC}"
        echo "$body" | python3 -m json.tool 2>/dev/null || echo "$body"
    fi
    echo ""
    echo "----------------------------------------"
    echo ""
}

# 1. Health & Metrics
echo "=== 1. HEALTH & METRICS ==="
test_endpoint "GET" "${BASE_URL}/health" "Health check básico"
test_endpoint "GET" "${BASE_URL}/" "Informações da API"
test_endpoint "GET" "${API_URL}/metrics" "Métricas do sistema"

# 2. Exchanges
echo "=== 2. EXCHANGES ==="
test_endpoint "GET" "${API_URL}/exchanges/available" "Lista exchanges disponíveis"
test_endpoint "GET" "${API_URL}/exchanges/linked?user_id=charles_test_user" "Exchanges linkadas do usuário"

# 3. Tokens (requer exchange_id)
echo "=== 3. TOKENS ==="
test_endpoint "GET" "${API_URL}/tokens/693481148b0a41e8b6acb073/BTC" "Informações de token BTC na Binance"
test_endpoint "GET" "${API_URL}/tokens/693481148b0a41e8b6acb073/search?query=bitcoin" "Buscar tokens na Binance"
test_endpoint "GET" "${API_URL}/tokens/693481148b0a41e8b6acb073/list?limit=5" "Listar tokens da Binance"

# 4. Balances
echo "=== 4. BALANCES ==="
test_endpoint "GET" "${API_URL}/balances/charles_test_user" "Saldos do usuário"
test_endpoint "GET" "${API_URL}/balances/charles_test_user?exchange_id=693481148b0a41e8b6acb073" "Saldos do usuário na Binance"

# 5. Strategies
echo "=== 5. STRATEGIES ==="
test_endpoint "GET" "${API_URL}/strategies?user_id=charles_test_user" "Lista estratégias do usuário"
test_endpoint "GET" "${API_URL}/strategies/templates/list" "Templates de estratégias"

# 6. Positions
echo "=== 6. POSITIONS ==="
test_endpoint "GET" "${API_URL}/positions?user_id=charles_test_user" "Lista posições do usuário"

# 7. Notifications
echo "=== 7. NOTIFICATIONS ==="
test_endpoint "GET" "${API_URL}/notifications?user_id=charles_test_user" "Lista notificações"

# 8. Jobs
echo "=== 8. JOBS ==="
test_endpoint "GET" "${API_URL}/jobs/status" "Status de todos os jobs"
test_endpoint "GET" "${API_URL}/jobs/scheduler/status" "Status do scheduler"

echo ""
echo "=========================================="
echo "  Teste Completo!"
echo "=========================================="
