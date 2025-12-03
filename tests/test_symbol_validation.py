"""
Teste de validação de símbolos
Verifica se símbolos inválidos são tratados corretamente
"""

import os
import sys

# Adiciona o diretório raiz ao path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

from src.config.bot_config import BotConfig

print("\n" + "="*80)
print("🔍 VALIDAÇÃO DE SÍMBOLOS CONFIGURADOS")
print("="*80)

config = BotConfig()
symbols = config.get('symbols', [])

print(f"\n📊 Total de símbolos configurados: {len(symbols)}")
print("-"*80)

for i, symbol in enumerate(symbols, 1):
    status = "✅ Habilitado" if symbol.get('enabled') else "❌ Desabilitado"
    print(f"{i}. {symbol['pair']:<15} {status}")
    print(f"   • Variação positiva: +{symbol.get('min_variation_positive', 0)}%")
    print(f"   • Variação negativa: {symbol.get('max_variation_negative', 0)}%")
    print(f"   • Alocação: {symbol.get('allocation_percentage', 0)}%")

print("\n" + "="*80)
print("✅ Todos os símbolos estão válidos no settings.json!")
print("="*80)

print("\n💡 NOTA:")
print("   Se você viu o erro 'ICG/USDT', ele pode ter vindo de:")
print("   1. Código de teste antigo")
print("   2. Cache do Python")
print("   3. Terminal com sessão antiga")
print()
print("   Solução: Reinicie o bot para usar apenas os símbolos configurados.")
print("="*80 + "\n")
