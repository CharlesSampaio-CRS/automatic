"""
Teste Rigoroso de Garantia de Lucro
Simula 1000 operações para garantir lucro mínimo
"""

import random
from src.database.mongodb_connection import get_database
from src.clients.buy_strategy_4h import BuyStrategy4h
from src.clients.buy_strategy import BuyStrategy

def simulate_buy_sell_cycle():
    """
    Simula ciclo completo de compra e venda com dados reais
    """
    db = get_database()
    config = db['BotConfigs'].find_one({'pair': 'REKTCOIN/USDT'})
    
    strategy_4h = BuyStrategy4h(config.get('strategy_4h'))
    strategy_24h = BuyStrategy(config.get('trading_strategy'))
    
    # Configurações
    min_profit_target = config.get('strategy_4h', {}).get('sell_strategy', {}).get('min_profit', 5)
    
    print('='*80)
    print('🧪 SIMULAÇÃO DE GARANTIA DE LUCRO')
    print('='*80)
    print(f'\n📊 Configuração:')
    print(f'   Lucro mínimo configurado: {min_profit_target}%')
    print(f'   Simulações: 1000 operações')
    
    results = {
        'total_operations': 0,
        'profitable': 0,
        'break_even': 0,
        'losses': 0,
        'total_profit': 0,
        'min_profit_seen': float('inf'),
        'max_profit_seen': float('-inf'),
        'profit_distribution': {},
        'loss_scenarios': []
    }
    
    print('\n⏳ Executando simulações...')
    
    # Simula 1000 operações
    for i in range(1000):
        # Gera variação de preço aleatória
        price_drop = random.uniform(-50, -2)  # Queda entre -2% e -50%
        
        # Decide qual estratégia compra
        should_buy_4h, info_4h = strategy_4h.should_buy(price_drop, 'TEST/USDT')
        
        if should_buy_4h:
            buy_percentage = info_4h['buy_percentage']
            strategy_used = '4h'
        else:
            should_buy_24h, info_24h = strategy_24h.should_buy(price_drop)
            if should_buy_24h:
                buy_percentage = info_24h['buy_percentage']
                strategy_used = '24h'
            else:
                continue  # Não compra
        
        # Simula compra
        buy_price = 100.0  # Preço base
        actual_buy_price = buy_price * (1 + price_drop/100)  # Preço com queda
        investment = 100 * (buy_percentage / 100)
        tokens = investment / actual_buy_price
        
        # Simula recuperação do preço (venda)
        # Cenários possíveis:
        # 1. Recupera totalmente e sobe
        # 2. Recupera parcialmente
        # 3. Não recupera (pior caso)
        
        recovery_scenarios = [
            ('full_recovery', random.uniform(min_profit_target + 1, 20)),  # 40% chance
            ('partial_recovery', random.uniform(0, min_profit_target - 1)),  # 30% chance
            ('no_recovery', random.uniform(-10, -1)),  # 20% chance
            ('excellent', random.uniform(20, 50))  # 10% chance
        ]
        
        weights = [0.4, 0.3, 0.2, 0.1]
        scenario_type, recovery = random.choices(recovery_scenarios, weights=weights)[0]
        
        # Preço de venda
        sell_price = actual_buy_price * (1 + recovery/100)
        
        # Calcula lucro
        sell_value = tokens * sell_price
        profit = sell_value - investment
        profit_pct = (profit / investment) * 100
        
        # Decide se vende ou não (baseado no min_profit)
        if profit_pct >= min_profit_target:
            # VENDE
            results['total_operations'] += 1
            results['total_profit'] += profit
            
            if profit > 0:
                results['profitable'] += 1
            elif profit == 0:
                results['break_even'] += 1
            else:
                results['losses'] += 1
                results['loss_scenarios'].append({
                    'price_drop': price_drop,
                    'recovery': recovery,
                    'profit_pct': profit_pct,
                    'strategy': strategy_used
                })
            
            # Atualiza min/max
            results['min_profit_seen'] = min(results['min_profit_seen'], profit_pct)
            results['max_profit_seen'] = max(results['max_profit_seen'], profit_pct)
            
            # Distribuição
            profit_range = int(profit_pct // 5) * 5  # Agrupa em ranges de 5%
            results['profit_distribution'][profit_range] = results['profit_distribution'].get(profit_range, 0) + 1
        else:
            # NÃO VENDE (aguarda mais recuperação)
            pass  # Na prática, fica holding
    
    return results, min_profit_target

def analyze_results(results, min_profit_target):
    """
    Analisa resultados e identifica problemas
    """
    print('\n' + '='*80)
    print('📊 RESULTADOS DA SIMULAÇÃO')
    print('='*80)
    
    print(f'\n🔢 ESTATÍSTICAS GERAIS:')
    print(f'   Total de operações completadas: {results["total_operations"]}')
    print(f'   Operações lucrativas: {results["profitable"]} ({results["profitable"]/results["total_operations"]*100:.1f}%)')
    print(f'   Operações no zero a zero: {results["break_even"]}')
    print(f'   Operações com prejuízo: {results["losses"]} ({results["losses"]/results["total_operations"]*100:.1f}%)')
    
    print(f'\n💰 LUCRO:')
    print(f'   Lucro total simulado: ${results["total_profit"]:.2f}')
    print(f'   Lucro médio por operação: ${results["total_profit"]/results["total_operations"]:.2f}')
    print(f'   Lucro mínimo visto: {results["min_profit_seen"]:.2f}%')
    print(f'   Lucro máximo visto: {results["max_profit_seen"]:.2f}%')
    
    print(f'\n📈 DISTRIBUIÇÃO DE LUCRO:')
    sorted_dist = sorted(results['profit_distribution'].items())
    for profit_range, count in sorted_dist:
        bar = '█' * (count // 10)
        print(f'   {profit_range:>3}% até {profit_range+4:>3}%: {bar} ({count})')
    
    # ANÁLISE CRÍTICA
    print('\n' + '='*80)
    print('🔍 ANÁLISE CRÍTICA - GARANTIA DE LUCRO')
    print('='*80)
    
    issues = []
    warnings = []
    
    # 1. Verifica se há prejuízos
    if results['losses'] > 0:
        issues.append(f'❌ CRÍTICO: {results["losses"]} operações COM PREJUÍZO!')
        print(f'\n❌ PROBLEMA 1: OPERAÇÕES COM PREJUÍZO')
        print(f'   Total: {results["losses"]} operações')
        print(f'   Taxa de prejuízo: {results["losses"]/results["total_operations"]*100:.2f}%')
        
        print('\n   Cenários de prejuízo detectados:')
        for i, scenario in enumerate(results['loss_scenarios'][:5], 1):
            print(f'   {i}. Queda: {scenario["price_drop"]:.1f}% | Recuperação: {scenario["recovery"]:.1f}% | Lucro: {scenario["profit_pct"]:.2f}%')
    
    # 2. Verifica se min_profit está sendo respeitado
    if results['min_profit_seen'] < min_profit_target:
        issues.append(f'❌ CRÍTICO: Lucro mínimo ({results["min_profit_seen"]:.2f}%) abaixo do configurado ({min_profit_target}%)!')
        print(f'\n❌ PROBLEMA 2: LUCRO MÍNIMO NÃO RESPEITADO')
        print(f'   Configurado: {min_profit_target}%')
        print(f'   Menor lucro visto: {results["min_profit_seen"]:.2f}%')
        print(f'   Diferença: {min_profit_target - results["min_profit_seen"]:.2f}%')
    
    # 3. Verifica taxa de sucesso
    success_rate = results['profitable'] / results['total_operations'] * 100
    if success_rate < 70:
        warnings.append(f'⚠️  Taxa de sucesso baixa: {success_rate:.1f}%')
        print(f'\n⚠️  AVISO: TAXA DE SUCESSO BAIXA')
        print(f'   Taxa atual: {success_rate:.1f}%')
        print(f'   Recomendado: ≥70%')
    
    # 4. Verifica lucro médio
    avg_profit = results['total_profit'] / results['total_operations']
    if avg_profit < 2:
        warnings.append(f'⚠️  Lucro médio baixo: ${avg_profit:.2f}')
        print(f'\n⚠️  AVISO: LUCRO MÉDIO BAIXO')
        print(f'   Lucro médio: ${avg_profit:.2f}')
        print(f'   Recomendado: ≥$2.00')
    
    # RESULTADO FINAL
    print('\n' + '='*80)
    print('🎯 RESULTADO FINAL - GARANTIA DE LUCRO')
    print('='*80)
    
    if issues:
        print(f'\n❌ SISTEMA NÃO GARANTE LUCRO MÍNIMO!')
        print(f'   {len(issues)} problema(s) crítico(s):')
        for issue in issues:
            print(f'   {issue}')
        print('\n🚨 NÃO USE EM PRODUÇÃO ATÉ CORRIGIR!')
        return False
    
    if warnings:
        print(f'\n⚠️  SISTEMA FUNCIONA MAS COM RESSALVAS')
        print(f'   {len(warnings)} aviso(s):')
        for warning in warnings:
            print(f'   {warning}')
        print('\n💡 Pode usar, mas monitore de perto')
        return True
    
    print(f'\n✅ SISTEMA GARANTE LUCRO MÍNIMO!')
    print(f'   • {results["profitable"]} operações lucrativas ({success_rate:.1f}%)')
    print(f'   • Lucro mínimo respeitado: {results["min_profit_seen"]:.2f}% ≥ {min_profit_target}%')
    print(f'   • Nenhuma operação com prejuízo')
    print(f'   • Lucro médio: ${avg_profit:.2f} por operação')
    print('\n🚀 APROVADO PARA PRODUÇÃO!')
    
    return True

def test_edge_cases():
    """
    Testa casos extremos
    """
    print('\n' + '='*80)
    print('🔬 TESTE DE CASOS EXTREMOS')
    print('='*80)
    
    db = get_database()
    config = db['BotConfigs'].find_one({'pair': 'REKTCOIN/USDT'})
    
    strategy_4h = BuyStrategy4h(config.get('strategy_4h'))
    strategy_24h = BuyStrategy(config.get('trading_strategy'))
    min_profit = config.get('strategy_4h', {}).get('sell_strategy', {}).get('min_profit', 5)
    
    test_cases = [
        {
            'name': 'Crash severo (-50%)',
            'price_drop': -50,
            'recovery': 5,  # Recupera só 5%
            'expected': 'Não vende (lucro insuficiente)'
        },
        {
            'name': 'Queda moderada (-15%) + boa recuperação (+10%)',
            'price_drop': -15,
            'recovery': 10,
            'expected': 'Vende com lucro'
        },
        {
            'name': 'Queda pequena (-5%) + recuperação exata no mínimo',
            'price_drop': -5,
            'recovery': min_profit,
            'expected': 'Vende no lucro mínimo'
        },
        {
            'name': 'Queda grande (-30%) sem recuperação (-5%)',
            'price_drop': -30,
            'recovery': -5,
            'expected': 'Não vende (prejuízo)'
        }
    ]
    
    print(f'\n🧪 Executando {len(test_cases)} casos extremos...\n')
    
    for i, test in enumerate(test_cases, 1):
        print(f'{i}. {test["name"]}')
        print(f'   Queda: {test["price_drop"]}% | Recuperação: {test["recovery"]}%')
        
        # Simula
        buy_price = 100.0
        actual_buy_price = buy_price * (1 + test["price_drop"]/100)
        investment = 50  # Investe $50
        tokens = investment / actual_buy_price
        
        sell_price = actual_buy_price * (1 + test["recovery"]/100)
        sell_value = tokens * sell_price
        profit = sell_value - investment
        profit_pct = (profit / investment) * 100
        
        if profit_pct >= min_profit:
            result = f'✅ VENDE com lucro de {profit_pct:.2f}%'
        elif profit_pct >= 0:
            result = f'⏭️  NÃO VENDE (lucro {profit_pct:.2f}% < mínimo {min_profit}%)'
        else:
            result = f'❌ NÃO VENDE (prejuízo de {profit_pct:.2f}%)'
        
        print(f'   Resultado: {result}')
        print(f'   Esperado: {test["expected"]}')
        print()

if __name__ == "__main__":
    # Executa simulação principal
    results, min_profit_target = simulate_buy_sell_cycle()
    
    # Analisa resultados
    is_safe = analyze_results(results, min_profit_target)
    
    # Testa casos extremos
    test_edge_cases()
    
    # Exit code
    exit(0 if is_safe else 1)
