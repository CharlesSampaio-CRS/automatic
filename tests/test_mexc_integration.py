#!/usr/bin/env python3
"""
Script de teste para verificar a integração com MEXC
Execute este script para testar a conexão sem executar ordens reais
"""

import os
import sys
from dotenv import load_dotenv

# Adiciona o diretório raiz ao path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Carrega variáveis do .env
load_dotenv()

from src.clients.exchange import MexcClient

def test_connection():
    """Testa a conexão com a API MEXC"""
    print("=" * 60)
    print("TESTE DE CONEXÃO - MEXC EXCHANGE")
    print("=" * 60)
    
    # Verifica se as credenciais estão configuradas
    api_key = os.getenv('API_KEY')
    api_secret = os.getenv('API_SECRET')
    
    if not api_key or not api_secret or api_key == 'sua_api_key_da_mexc_aqui':
        print("\n❌ ERRO: Credenciais não configuradas!")
        print("\nPara configurar, edite o arquivo .env:")
        print("API_KEY='sua_api_key_real'")
        print("API_SECRET='seu_api_secret_real'")
        return False
    
    print("\n✓ Credenciais encontradas")
    print(f"  API Key: {api_key[:8]}...{api_key[-4:]}")
    
    try:
        # Inicializa o cliente
        print("\n→ Inicializando cliente MEXC...")
        client = MexcClient(api_key, api_secret)
        print("✓ Cliente inicializado com sucesso")
        
        # Testa buscar saldo
        print("\n→ Buscando saldo disponível...")
        balance = client.get_usdt_available()
        print(f"✓ Saldo USDT disponível: ${balance:.2f}")
        
        # Testa buscar ativos
        print("\n→ Buscando ativos...")
        assets = client.get_non_zero_sorted_assets()
        print(f"✓ Encontrados {len(assets)} ativos com saldo > 1")
        
        if assets:
            print("\n  Top 5 ativos:")
            for asset in assets[:5]:
                print(f"    • {asset['currency']}: {asset['balance']}")
        
        # Testa buscar total de ativos
        print("\n→ Calculando total de ativos em USDT...")
        total_assets = client.get_total_assets_in_usdt()
        
        if 'error' not in total_assets:
            print(f"✓ Total em ativos: ${total_assets['total_assets_usdt']:.2f}")
            print(f"✓ USDT disponível: ${total_assets['available_usdt']:.2f}")
            print(f"✓ Total geral: ${total_assets['total_usdt']:.2f}")
        else:
            print(f"⚠ Erro ao calcular: {total_assets['error']}")
        
        # Testa buscar variações
        print("\n→ Buscando variações de 24h dos símbolos configurados...")
        variations = client.get_symbol_variations()
        
        if variations:
            print(f"✓ {len(variations)} símbolos encontrados:")
            for var in variations:
                emoji = "📈" if var['variation_24h'] > 0 else "📉"
                print(f"    {emoji} {var['symbol']}: {var['variation_24h']:+.2f}%")
        else:
            print("⚠ Nenhuma variação encontrada (verifique os símbolos em config.py)")
        
        print("\n" + "=" * 60)
        print("✅ TESTE CONCLUÍDO COM SUCESSO!")
        print("=" * 60)
        print("\n💡 Para executar a aplicação:")
        print("   python3 app.py")
        print("\n⚠️  NOTA: Este teste NÃO executa ordens reais")
        print("=" * 60)
        
        return True
        
    except Exception as e:
        print(f"\n❌ ERRO durante o teste:")
        print(f"   {str(e)}")
        print("\n🔍 Verifique:")
        print("   1. Suas credenciais estão corretas no .env")
        print("   2. A API Key tem permissões de leitura e trading")
        print("   3. Sua conexão com a internet está funcionando")
        print("   4. Os símbolos em config.py existem na MEXC")
        return False

if __name__ == "__main__":
    success = test_connection()
    sys.exit(0 if success else 1)
