"""
Validação de Segurança - Garantir que você NÃO VAI PERDER dinheiro
Foca em: Stop loss, Thresholds, Limites de investimento, Proteções
"""

from src.database.mongodb_connection import get_database
from src.clients.buy_strategy_4h import BuyStrategy4h
from src.clients.buy_strategy import BuyStrategy
import json

def validate_safety_rules():
    """
    Valida APENAS regras de segurança para evitar perdas
    """
    db = get_database()
    config = db['BotConfigs'].find_one({'pair': 'REKTCOIN/USDT'})
    
    print('='*80)
    print('🛡️  VALIDAÇÃO DE SEGURANÇA - PROTEÇÃO CONTRA PERDAS')
    print('='*80)
    
    issues = []
    warnings = []
    
    # 1. VALIDAR STOP LOSS
    print('\n1️⃣  STOP LOSS:')
    print('-'*80)
    
    risk_mgmt_4h = config.get('strategy_4h', {}).get('risk_management', {})
    stop_loss = risk_mgmt_4h.get('stop_loss_percent', None)
    
    if stop_loss is None:
        issues.append('❌ CRÍTICO: Stop loss NÃO configurado!')
        print('   ❌ Stop loss NÃO existe - RISCO ALTO!')
    elif stop_loss >= 0:
        issues.append(f'❌ CRÍTICO: Stop loss está POSITIVO ({stop_loss}%)!')
        print(f'   ❌ Stop loss: {stop_loss}% (DEVE SER NEGATIVO!)')
    elif stop_loss < -50:
        warnings.append(f'⚠️  Stop loss muito permissivo: {stop_loss}%')
        print(f'   ⚠️  Stop loss: {stop_loss}% (muito permissivo, recomendado: -25%)')
    else:
        print(f'   ✅ Stop loss: {stop_loss}% (adequado)')
    
    # 2. VALIDAR THRESHOLDS - Garantir que não compra demais no topo
    print('\n2️⃣  THRESHOLDS DE COMPRA (Proteção contra comprar caro):')
    print('-'*80)
    
    # Strategy 4h
    strategy_4h_config = config.get('strategy_4h')
    if not strategy_4h_config:
        print('   ❌ ERRO: strategy_4h não encontrada na configuração!')
        return False
    
    strategy_4h = BuyStrategy4h(strategy_4h_config)
    print('\n   Strategy 4h:')
    for level in strategy_4h.buy_levels:
        threshold = level['variation_threshold']
        percentage = level['percentage_of_balance']
        
        if threshold >= 0:
            issues.append(f'❌ CRÍTICO: 4h comprando em ALTA ({threshold}%)!')
            print(f'      ❌ {threshold}%: {percentage}% do saldo - COMPRA EM ALTA!')
        elif threshold > -2:
            warnings.append(f'⚠️  4h threshold muito próximo de zero: {threshold}%')
            print(f'      ⚠️  {threshold}%: {percentage}% - Queda pequena, risco moderado')
        else:
            print(f'      ✅ {threshold}%: {percentage}% do saldo')
    
    # Strategy 24h
    strategy_24h = BuyStrategy(config.get('trading_strategy'))
    print('\n   Strategy 24h:')
    for level in strategy_24h.buy_levels:
        threshold = level['variation_threshold']
        percentage = level['percentage_of_balance']
        
        if threshold >= 0:
            issues.append(f'❌ CRÍTICO: 24h comprando em ALTA ({threshold}%)!')
            print(f'      ❌ {threshold}%: {percentage}% do saldo - COMPRA EM ALTA!')
        elif threshold > -5:
            warnings.append(f'⚠️  24h threshold muito próximo de zero: {threshold}%')
            print(f'      ⚠️  {threshold}%: {percentage}% - Queda pequena, risco moderado')
        else:
            print(f'      ✅ {threshold}%: {percentage}% do saldo')
    
    # 3. VALIDAR LIMITES DE INVESTIMENTO
    print('\n3️⃣  LIMITES DE INVESTIMENTO (Proteção contra all-in):')
    print('-'*80)
    
    max_per_trade_4h = risk_mgmt_4h.get('max_percentage_per_trade', 100)
    
    if max_per_trade_4h >= 50:
        warnings.append(f'⚠️  Limite por trade 4h muito alto: {max_per_trade_4h}%')
        print(f'   ⚠️  Max por trade 4h: {max_per_trade_4h}% (recomendado: ≤30%)')
    else:
        print(f'   ✅ Max por trade 4h: {max_per_trade_4h}%')
    
    # Verifica se algum threshold excede o máximo
    print('\n   Verificando se thresholds respeitam o máximo:')
    for level in strategy_4h.buy_levels:
        if level['percentage_of_balance'] > max_per_trade_4h:
            issues.append(f'❌ CRÍTICO: Threshold 4h {level["variation_threshold"]}% tenta investir {level["percentage_of_balance"]}% mas máximo é {max_per_trade_4h}%!')
            print(f'      ❌ {level["variation_threshold"]}%: {level["percentage_of_balance"]}% > max {max_per_trade_4h}%')
        else:
            print(f'      ✅ {level["variation_threshold"]}%: {level["percentage_of_balance"]}% ≤ max {max_per_trade_4h}%')
    
    for level in strategy_24h.buy_levels:
        if level['percentage_of_balance'] > 50:
            warnings.append(f'⚠️  Threshold 24h {level["variation_threshold"]}% investe {level["percentage_of_balance"]}% (alto)')
            print(f'      ⚠️  {level["variation_threshold"]}%: {level["percentage_of_balance"]}% (alto)')
        else:
            print(f'      ✅ {level["variation_threshold"]}%: {level["percentage_of_balance"]}%')
    
    # 4. VALIDAR LUCRO MÍNIMO
    print('\n4️⃣  LUCRO MÍNIMO PARA VENDA (Proteção contra vender com prejuízo):')
    print('-'*80)
    
    sell_strategy = config.get('strategy_4h', {}).get('sell_strategy', {})
    min_profit = sell_strategy.get('min_profit', None)
    
    if min_profit is None:
        warnings.append('⚠️  Lucro mínimo não configurado')
        print('   ⚠️  Lucro mínimo: NÃO configurado (usando 5% padrão)')
    elif min_profit < 0:
        issues.append(f'❌ CRÍTICO: Lucro mínimo NEGATIVO ({min_profit}%) - VAI VENDER COM PREJUÍZO!')
        print(f'   ❌ Lucro mínimo: {min_profit}% - VENDE COM PREJUÍZO!')
    elif min_profit == 0:
        warnings.append('⚠️  Lucro mínimo 0% - Pode vender no zero a zero')
        print(f'   ⚠️  Lucro mínimo: {min_profit}% (recomendado: ≥3%)')
    elif min_profit < 2:
        warnings.append(f'⚠️  Lucro mínimo muito baixo: {min_profit}%')
        print(f'   ⚠️  Lucro mínimo: {min_profit}% (baixo, recomendado: ≥3%)')
    else:
        print(f'   ✅ Lucro mínimo: {min_profit}%')
    
    # 5. VALIDAR COOLDOWN (Proteção contra overtrading)
    print('\n5️⃣  COOLDOWN (Proteção contra overtrading):')
    print('-'*80)
    
    cooldown = risk_mgmt_4h.get('cooldown_minutes', None)
    max_trades_per_hour = risk_mgmt_4h.get('max_orders_per_hour', None)
    
    if cooldown is None or cooldown == 0:
        warnings.append('⚠️  Sem cooldown - Risco de overtrading')
        print('   ⚠️  Cooldown: NÃO configurado')
    elif cooldown < 5:
        warnings.append(f'⚠️  Cooldown muito curto: {cooldown} minutos')
        print(f'   ⚠️  Cooldown: {cooldown} minutos (recomendado: ≥10 min)')
    else:
        print(f'   ✅ Cooldown: {cooldown} minutos')
    
    if max_trades_per_hour is None:
        warnings.append('⚠️  Sem limite de trades por hora')
        print('   ⚠️  Max trades/hora: NÃO configurado')
    elif max_trades_per_hour > 6:
        warnings.append(f'⚠️  Muitos trades por hora: {max_trades_per_hour}')
        print(f'   ⚠️  Max trades/hora: {max_trades_per_hour} (recomendado: ≤6)')
    else:
        print(f'   ✅ Max trades/hora: {max_trades_per_hour}')
    
    # 6. VALIDAR SOBREPOSIÇÃO DE THRESHOLDS
    print('\n6️⃣  SOBREPOSIÇÃO DE THRESHOLDS (Evitar compra dupla):')
    print('-'*80)
    
    thresholds_4h = [level['variation_threshold'] for level in strategy_4h.buy_levels]
    thresholds_24h = [level['variation_threshold'] for level in strategy_24h.buy_levels]
    
    overlap = False
    for t4 in thresholds_4h:
        for t24 in thresholds_24h:
            if abs(t4 - t24) < 2:  # Menos de 2% de diferença
                overlap = True
                warnings.append(f'⚠️  Sobreposição: 4h({t4}%) e 24h({t24}%)')
                print(f'   ⚠️  Sobreposição: 4h {t4}% próximo de 24h {t24}%')
    
    if not overlap:
        print('   ✅ Sem sobreposição entre thresholds 4h e 24h')
    
    # 7. TESTE DE CENÁRIO RUIM
    print('\n7️⃣  SIMULAÇÃO DE CENÁRIO RUIM (Token cai 50%):')
    print('-'*80)
    
    balance = 100.0
    total_invested = 0
    
    # Simula quedas progressivas
    scenarios = [
        {'price_change': -3, 'strategy': '4h'},
        {'price_change': -5, 'strategy': '4h'},
        {'price_change': -10, 'strategy': '4h'},
        {'price_change': -15, 'strategy': '24h'},
        {'price_change': -25, 'strategy': '24h'},
        {'price_change': -50, 'strategy': '24h'},
    ]
    
    print('   Simulando quedas progressivas:')
    for scenario in scenarios:
        change = scenario['price_change']
        strategy = scenario['strategy']
        
        if strategy == '4h':
            should_buy, info = strategy_4h.should_buy(change, 'TEST/USDT')
        else:
            should_buy, info = strategy_24h.should_buy(change)
        
        if should_buy:
            percentage = info.get('buy_percentage', 0)
            investment = balance * (percentage / 100)
            total_invested += investment
            balance -= investment
            
            print(f'   📉 {change:>4}%: Compra {percentage}% (${investment:.2f}) | Saldo: ${balance:.2f} | Total investido: ${total_invested:.2f}')
        else:
            print(f'   ⏭️  {change:>4}%: Não compra | Saldo: ${balance:.2f}')
    
    final_exposure = (total_invested / 100) * 100
    print(f'\n   Exposição total: {final_exposure:.1f}% do capital inicial')
    
    if final_exposure > 80:
        issues.append(f'❌ CRÍTICO: Exposição de {final_exposure:.1f}% em queda de 50%!')
        print(f'   ❌ RISCO ALTO: {final_exposure:.1f}% investido em cenário de crash!')
    elif final_exposure > 60:
        warnings.append(f'⚠️  Exposição alta: {final_exposure:.1f}% em queda de 50%')
        print(f'   ⚠️  Exposição moderada: {final_exposure:.1f}% investido')
    else:
        print(f'   ✅ Exposição controlada: {final_exposure:.1f}% investido')
    
    # RESULTADO FINAL
    print('\n' + '='*80)
    print('🎯 RESULTADO DA VALIDAÇÃO DE SEGURANÇA:')
    print('='*80)
    
    if issues:
        print(f'\n❌ PROBLEMAS CRÍTICOS DETECTADOS ({len(issues)}):')
        for issue in issues:
            print(f'   {issue}')
        print('\n🚨 NÃO DEPLOY ATÉ CORRIGIR OS PROBLEMAS CRÍTICOS!')
        return False
    
    if warnings:
        print(f'\n⚠️  AVISOS ({len(warnings)}):')
        for warning in warnings:
            print(f'   {warning}')
        print('\n💡 Considere revisar os avisos, mas sistema pode ser usado com cuidado')
    
    if not issues and not warnings:
        print('\n✅ SISTEMA SEGURO!')
        print('   Todas as proteções estão configuradas corretamente')
        print('   Risco de perda minimizado')
        return True
    
    if not issues:
        print(f'\n✅ SISTEMA APROVADO COM RESSALVAS')
        print(f'   {len(warnings)} avisos detectados, mas nenhum problema crítico')
        print('   Você pode usar em produção, mas monitore os avisos')
        return True
    
    print('='*80 + '\n')
    return False

if __name__ == "__main__":
    is_safe = validate_safety_rules()
    exit(0 if is_safe else 1)
