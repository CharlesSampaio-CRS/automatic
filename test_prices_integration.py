"""
Testa integração do endpoint /prices com exchange.py
Valida que dados são obtidos corretamente e fallback funciona
"""

import sys
import os
from dotenv import load_dotenv

# Adiciona o diretório raiz ao path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

from src.clients.exchange import MexcClient

# Carrega variáveis do .env
load_dotenv()

def test_get_price_data():
    """Testa método get_price_data()"""
    print("\n" + "="*80)
    print("🧪 TESTE 1: get_price_data()")
    print("="*80)
    
    api_key = os.getenv('MEXC_API_KEY')
    api_secret = os.getenv('MEXC_API_SECRET')
    
    client = MexcClient(api_key, api_secret)
    
    # Testa com BTC/USDT
    symbol = "BTC/USDT"
    print(f"\n📊 Buscando dados de {symbol}...")
    
    price_data = client.get_price_data(symbol)
    
    if price_data:
        print(f"✅ Dados obtidos do endpoint /prices:")
        print(f"   Symbol: {price_data['symbol']}")
        print(f"   Current: ${price_data['current']:,.2f}")
        print(f"   Ask (compra): ${price_data['ask']:,.2f}")
        print(f"   Bid (venda): ${price_data['bid']:,.2f}")
        print(f"   Variação 1h: {price_data['change_1h_percent']:+.2f}%")
        print(f"   Variação 4h: {price_data['change_4h_percent']:+.2f}%")
        print(f"   Variação 24h: {price_data['change_24h_percent']:+.2f}%")
        print(f"   Volume 24h: ${price_data['volume_24h']:,.0f}")
        print(f"   Fonte: {price_data['source']}")
        return True
    else:
        print("❌ Falha ao obter dados do endpoint")
        return False

def test_get_variation_4h():
    """Testa get_variation_4h() com endpoint"""
    print("\n" + "="*80)
    print("🧪 TESTE 2: get_variation_4h()")
    print("="*80)
    
    api_key = os.getenv('MEXC_API_KEY')
    api_secret = os.getenv('MEXC_API_SECRET')
    
    client = MexcClient(api_key, api_secret)
    
    symbol = "BTC/USDT"
    print(f"\n📊 Buscando variação 4h de {symbol}...")
    
    variation = client.get_variation_4h(symbol)
    
    if variation is not None:
        print(f"✅ Variação 4h: {variation:+.2f}%")
        return True
    else:
        print("❌ Falha ao obter variação 4h")
        return False

def test_get_variation_1h():
    """Testa get_variation_1h() com endpoint"""
    print("\n" + "="*80)
    print("🧪 TESTE 3: get_variation_1h()")
    print("="*80)
    
    api_key = os.getenv('MEXC_API_KEY')
    api_secret = os.getenv('MEXC_API_SECRET')
    
    client = MexcClient(api_key, api_secret)
    
    symbol = "BTC/USDT"
    print(f"\n📊 Buscando variação 1h de {symbol}...")
    
    variation = client.get_variation_1h(symbol)
    
    if variation is not None:
        print(f"✅ Variação 1h: {variation:+.2f}%")
        return True
    else:
        print("❌ Falha ao obter variação 1h")
        return False

def test_multiple_symbols():
    """Testa múltiplos símbolos"""
    print("\n" + "="*80)
    print("🧪 TESTE 4: Múltiplos Símbolos")
    print("="*80)
    
    api_key = os.getenv('MEXC_API_KEY')
    api_secret = os.getenv('MEXC_API_SECRET')
    
    client = MexcClient(api_key, api_secret)
    
    symbols = ["BTC/USDT", "ETH/USDT", "SOL/USDT", "DOGE/USDT"]
    
    results = []
    
    for symbol in symbols:
        print(f"\n📊 {symbol}:")
        price_data = client.get_price_data(symbol)
        
        if price_data:
            print(f"   ✅ Current: ${price_data['current']:,.4f}")
            print(f"   ✅ 4h: {price_data['change_4h_percent']:+.2f}%")
            print(f"   ✅ 24h: {price_data['change_24h_percent']:+.2f}%")
            results.append(True)
        else:
            print(f"   ❌ Falha")
            results.append(False)
    
    success_rate = (sum(results) / len(results)) * 100
    print(f"\n📊 Taxa de sucesso: {success_rate:.0f}% ({sum(results)}/{len(results)})")
    
    return success_rate == 100

def test_fallback():
    """Testa fallback quando endpoint não está disponível"""
    print("\n" + "="*80)
    print("🧪 TESTE 5: Fallback (endpoint indisponível)")
    print("="*80)
    
    api_key = os.getenv('MEXC_API_KEY')
    api_secret = os.getenv('MEXC_API_SECRET')
    
    client = MexcClient(api_key, api_secret)
    
    # Força URL inválida para testar fallback
    client.API_BASE_URL = "http://localhost:99999"
    
    symbol = "BTC/USDT"
    print(f"\n📊 Forçando fallback para {symbol}...")
    print("   (endpoint configurado para URL inválida)")
    
    variation = client.get_variation_4h(symbol)
    
    if variation is not None:
        print(f"✅ Fallback funcionou! Variação 4h: {variation:+.2f}%")
        print("   (Calculado via candles CCXT)")
        return True
    else:
        print("❌ Fallback falhou")
        return False

def run_all_tests():
    """Executa todos os testes"""
    print("\n")
    print("="*80)
    print("🚀 INICIANDO TESTES DE INTEGRAÇÃO /prices")
    print("="*80)
    
    tests = [
        ("get_price_data()", test_get_price_data),
        ("get_variation_4h()", test_get_variation_4h),
        ("get_variation_1h()", test_get_variation_1h),
        ("Múltiplos Símbolos", test_multiple_symbols),
        ("Fallback CCXT", test_fallback),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n❌ ERRO no teste {test_name}: {e}")
            results.append((test_name, False))
    
    # Resumo final
    print("\n" + "="*80)
    print("📊 RESUMO DOS TESTES")
    print("="*80)
    
    for test_name, result in results:
        status = "✅ PASSOU" if result else "❌ FALHOU"
        print(f"{status}: {test_name}")
    
    success_count = sum(1 for _, result in results if result)
    total = len(results)
    success_rate = (success_count / total) * 100
    
    print(f"\n{'='*80}")
    print(f"RESULTADO FINAL: {success_count}/{total} testes passaram ({success_rate:.0f}%)")
    print(f"{'='*80}\n")
    
    return success_rate == 100

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
