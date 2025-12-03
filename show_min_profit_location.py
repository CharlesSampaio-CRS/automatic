"""
Mostra onde fica a configuração de lucro mínimo
"""

from src.database.mongodb_connection import get_database
import json

db = get_database()
config = db['BotConfigs'].find_one({'pair': 'REKTCOIN/USDT'})

print('='*80)
print('📍 ONDE FICA O LUCRO MÍNIMO')
print('='*80)

print('\n🗄️  NO MONGODB:')
print('-'*80)
print('   • Database: AutomaticInvest')
print('   • Collection: BotConfigs')
print('   • Document: pair = "REKTCOIN/USDT"')
print('   • Campo: strategy_4h → sell_strategy → min_profit')

print('\n📦 ESTRUTURA DO DOCUMENTO:')
print('-'*80)
sell_strategy = config.get('strategy_4h', {}).get('sell_strategy', {})
print(json.dumps({'sell_strategy': sell_strategy}, indent=2))

print('\n💻 NO CÓDIGO (onde é usado):')
print('-'*80)
print('   📄 src/clients/sell_strategy.py')
print('      Usa min_profit para decidir quando vender')
print()
print('   📄 src/clients/exchange.py')
print('      Verifica lucro antes de executar venda')

print('\n🔧 COMO ALTERAR:')
print('-'*80)
print('   ✅ OPÇÃO 1 - Via Script (RECOMENDADO):')
print('      $ python3 adjust_safety_config.py')
print('      Escolha opção: 1')
print()
print('   🔵 OPÇÃO 2 - Via MongoDB Compass (GUI):')
print('      1. Abra MongoDB Compass')
print('      2. Cole a connection string do .env')
print('      3. Navegue: AutomaticInvest → BotConfigs')
print('      4. Encontre documento com pair="REKTCOIN/USDT"')
print('      5. Clique em "Edit Document"')
print('      6. Navegue: strategy_4h → sell_strategy → min_profit')
print('      7. Altere o valor')
print('      8. Clique em "Update"')
print()
print('   🐍 OPÇÃO 3 - Via Python Console:')
print('      python3 -c "')
print('      from src.database.mongodb_connection import get_database')
print('      db = get_database()')
print('      db[\\"BotConfigs\\"].update_one(')
print('          {\\"pair\\": \\"REKTCOIN/USDT\\"},')
print('          {\\"$set\\": {\\"strategy_4h.sell_strategy.min_profit\\": 5}}')
print('      )')
print('      print(\\"✅ Atualizado!\\")')
print('      "')

print('\n📊 VALOR ATUAL:')
print('-'*80)
current = sell_strategy.get('min_profit')
print(f'   Lucro mínimo: {current}%')

if current >= 5:
    print(f'   ✅ JÁ está em {current}% (ótimo!)')
elif current >= 3:
    print(f'   ⚠️  Está em {current}% (aceitável, mas recomendado 5%)')
else:
    print(f'   ❌ Está em {current}% (muito baixo, ajuste para 5%)')

print('\n💡 RECOMENDAÇÃO:')
print('-'*80)
if current < 5:
    print('   Execute: python3 adjust_safety_config.py')
    print('   É a forma mais fácil e segura!')
else:
    print('   Configuração já está ótima! ✅')

print('='*80)
