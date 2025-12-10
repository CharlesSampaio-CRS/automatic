#!/bin/bash
# 🚀 EXEMPLOS DE CURL - Estratégias com Templates
# Execute estes comandos para criar estratégias facilmente!

echo "============================================"
echo "📋 TESTANDO TEMPLATES DE ESTRATÉGIA"
echo "============================================"

# Primeiro, pegue o ID da exchange MEXC
echo ""
echo "1️⃣ Buscando ID da MEXC..."
MEXC_ID=$(curl -s http://localhost:5000/api/v1/exchanges | jq -r '.exchanges[] | select(.nome=="MEXC") | ._id')

if [ -z "$MEXC_ID" ]; then
    echo "❌ MEXC não encontrada!"
    echo "📋 Listando exchanges disponíveis:"
    curl -s http://localhost:5000/api/v1/exchanges | jq -r '.exchanges[] | "  - \(.nome): \(._id)"'
    exit 1
fi

echo "✅ MEXC ID: $MEXC_ID"

# ===========================================
# TEMPLATE: SIMPLE
# ===========================================
echo ""
echo "============================================"
echo "2️⃣ Criando estratégia SIMPLE para REKTCOIN"
echo "============================================"
echo "Configuração:"
echo "  - Take Profit: 5% (vende 100%)"
echo "  - Stop Loss: 2%"
echo "  - Buy Dip: 3%"
echo "  - Trailing Stop: NÃO"
echo "  - DCA: NÃO"
echo ""

curl -X POST http://localhost:5000/api/v1/strategies \
  -H "Content-Type: application/json" \
  -d "{
    \"user_id\": \"user123\",
    \"exchange_id\": \"$MEXC_ID\",
    \"token\": \"REKTCOIN\",
    \"template\": \"simple\"
  }" | jq '.'

echo ""
read -p "Pressione ENTER para testar CONSERVATIVE..."

# ===========================================
# TEMPLATE: CONSERVATIVE
# ===========================================
echo ""
echo "============================================"
echo "3️⃣ Criando estratégia CONSERVATIVE para BTC"
echo "============================================"
echo "Configuração:"
echo "  - Take Profit: 2% (50%) + 4% (50%)"
echo "  - Stop Loss: 1% + Trailing 0.5%"
echo "  - Buy Dip: 2%"
echo "  - Max Loss: \$200/dia, \$500/semana"
echo "  - Cooldown: 60min após venda"
echo "  - Volume mínimo: \$50M/dia"
echo ""

curl -X POST http://localhost:5000/api/v1/strategies \
  -H "Content-Type: application/json" \
  -d "{
    \"user_id\": \"user123\",
    \"exchange_id\": \"$MEXC_ID\",
    \"token\": \"BTC\",
    \"template\": \"conservative\"
  }" | jq '.'

echo ""
read -p "Pressione ENTER para testar AGGRESSIVE..."

# ===========================================
# TEMPLATE: AGGRESSIVE
# ===========================================
echo ""
echo "============================================"
echo "4️⃣ Criando estratégia AGGRESSIVE para ETH"
echo "============================================"
echo "Configuração:"
echo "  - Take Profit: 5% (30%) + 10% (40%) + 20% (30%)"
echo "  - Stop Loss: 3% + Trailing 2%"
echo "  - Buy Dip: 5% com DCA em 2 níveis"
echo "  - Max Loss: \$1000/dia, \$3000/semana"
echo "  - Cooldown: 15min após venda"
echo "  - Volume mínimo: \$100M/dia"
echo ""

curl -X POST http://localhost:5000/api/v1/strategies \
  -H "Content-Type: application/json" \
  -d "{
    \"user_id\": \"user123\",
    \"exchange_id\": \"$MEXC_ID\",
    \"token\": \"ETH\",
    \"template\": \"aggressive\"
  }" | jq '.'

# ===========================================
# LISTAR ESTRATÉGIAS CRIADAS
# ===========================================
echo ""
echo "============================================"
echo "5️⃣ Listando todas as estratégias criadas"
echo "============================================"
echo ""

curl -s "http://localhost:5000/api/v1/strategies?user_id=user123" | jq '.strategies[] | {
  token: .token,
  exchange: .exchange_name,
  template: (
    if .rules.take_profit_levels | length == 1 then "SIMPLE"
    elif .rules.take_profit_levels | length == 2 then "CONSERVATIVE"
    elif .rules.take_profit_levels | length == 3 then "AGGRESSIVE"
    else "CUSTOM"
    end
  ),
  is_active: .is_active,
  trailing: .rules.stop_loss.trailing_enabled,
  dca: .rules.buy_dip.dca_enabled
}'

echo ""
echo "============================================"
echo "✅ TESTES COMPLETOS!"
echo "============================================"
