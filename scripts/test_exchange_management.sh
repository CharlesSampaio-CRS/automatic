#!/bin/bash
# Script de teste para endpoints de gerenciamento de exchanges

BASE_URL="http://localhost:5000/api/v1"
USER_ID="charles_test_user"

# Cores para output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "========================================="
echo "🧪 TESTANDO ENDPOINTS DE EXCHANGE"
echo "========================================="
echo ""

# 1. Listar exchanges atuais
echo "1️⃣ Listando exchanges do usuário..."
RESPONSE=$(curl -s "${BASE_URL}/exchanges?user_id=${USER_ID}")
echo "$RESPONSE" | python3 -m json.tool

# Extrair primeiro exchange_id para testes
EXCHANGE_ID=$(echo "$RESPONSE" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data['exchanges'][0]['id']) if data.get('exchanges') else exit(1)" 2>/dev/null)

if [ -z "$EXCHANGE_ID" ]; then
    echo -e "${RED}❌ Nenhuma exchange encontrada. Execute o link primeiro!${NC}"
    exit 1
fi

EXCHANGE_NAME=$(echo "$RESPONSE" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data['exchanges'][0]['name'])")
echo -e "${GREEN}✅ Exchange encontrada: ${EXCHANGE_NAME} (ID: ${EXCHANGE_ID})${NC}"
echo ""
sleep 2

# 2. Testar DISCONNECT
echo "========================================="
echo "2️⃣ Testando DISCONNECT..."
echo "========================================="
curl -s -X POST "${BASE_URL}/exchanges/disconnect" \
  -H "Content-Type: application/json" \
  -d "{
    \"user_id\": \"${USER_ID}\",
    \"exchange_id\": \"${EXCHANGE_ID}\"
  }" | python3 -m json.tool

echo ""
sleep 2

# 3. Verificar se foi desconectada
echo "3️⃣ Verificando status após disconnect..."
curl -s "${BASE_URL}/exchanges?user_id=${USER_ID}" | \
  python3 -c "import sys, json; data=json.load(sys.stdin); ex=[e for e in data.get('exchanges', []) if e['id']=='${EXCHANGE_ID}']; print(f\"Status: {'✅ Ativa' if ex[0]['is_active'] else '⏸️  Desconectada'}\" if ex else 'Não encontrada')"
echo ""
sleep 2

# 4. Testar RECONNECT
echo "========================================="
echo "4️⃣ Testando RECONNECT..."
echo "========================================="
curl -s -X POST "${BASE_URL}/exchanges/reconnect" \
  -H "Content-Type: application/json" \
  -d "{
    \"user_id\": \"${USER_ID}\",
    \"exchange_id\": \"${EXCHANGE_ID}\"
  }" | python3 -m json.tool

echo ""
sleep 2

# 5. Verificar se foi reconectada
echo "5️⃣ Verificando status após reconnect..."
curl -s "${BASE_URL}/exchanges?user_id=${USER_ID}" | \
  python3 -c "import sys, json; data=json.load(sys.stdin); ex=[e for e in data.get('exchanges', []) if e['id']=='${EXCHANGE_ID}']; print(f\"Status: {'✅ Ativa' if ex[0]['is_active'] else '⏸️  Desconectada'}\" if ex else 'Não encontrada')"
echo ""
sleep 2

# 6. Testar DELETE (comentado por segurança - descomente para testar)
echo "========================================="
echo "6️⃣ Teste de DELETE (DESABILITADO)"
echo "========================================="
echo -e "${YELLOW}⚠️  O teste de DELETE está desabilitado por segurança.${NC}"
echo -e "${YELLOW}⚠️  Para testar, descomente a linha abaixo no script.${NC}"
echo ""

# Descomente as linhas abaixo para testar DELETE (IRREVERSÍVEL!)
# echo "Deletando exchange (IRREVERSÍVEL)..."
# curl -s -X DELETE "${BASE_URL}/exchanges/delete" \
#   -H "Content-Type: application/json" \
#   -d "{
#     \"user_id\": \"${USER_ID}\",
#     \"exchange_id\": \"${EXCHANGE_ID}\"
#   }" | python3 -m json.tool
# echo ""

echo "========================================="
echo "✅ TESTES CONCLUÍDOS!"
echo "========================================="
echo ""
echo "Endpoints testados:"
echo "  ✅ POST /exchanges/disconnect"
echo "  ✅ POST /exchanges/reconnect"
echo "  ⏸️  DELETE /exchanges/delete (desabilitado)"
echo ""
