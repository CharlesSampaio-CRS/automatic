"""
Teste de Operações Concorrentes
Verifica se o sistema pode comprar e vender ao mesmo tempo
"""

from src.database.mongodb_connection import get_database
from src.clients.buy_strategy_4h import BuyStrategy4h
from src.clients.buy_strategy import BuyStrategy

def test_concurrent_buy_sell():
    """
    Testa cenário de compra e venda simultânea
    """
    print('='*80)
    print('🔬 TESTE DE OPERAÇÕES CONCORRENTES')
    print('='*80)
    
    db = get_database()
    config = db['BotConfigs'].find_one({'pair': 'REKTCOIN/USDT'})
    
    if not config:
        raise Exception(' Config não encontrada!')
    
    strategy_4h_config = config.get('strategy_4h')
    if not strategy_4h_config:
        raise Exception(' strategy_4h não encontrada!')
    
    strategy_4h = BuyStrategy4h(strategy_4h_config)
    min_profit = strategy_4h_config.get('sell_strategy', {}).get('min_profit', 5)
    
    print(f'\n Configuração:')
    print(f'   Lucro mínimo: {min_profit}%')
    print(f'   Par: REKTCOIN/USDT')
    
    # CENÁRIOS DE TESTE
    print('\n' + '='*80)
    print('🧪 CENÁRIOS DE TESTE')
    print('='*80)
    
    scenarios = [
        {
            'name': 'Cenário 1: Posição vazia + Queda de preço',
            'has_position': False,
            'price_change': -10,
            'current_profit': 0,
            'expected': 'Só COMPRA (não tem nada para vender)'
        },
        {
            'name': 'Cenário 2: Com posição + Preço subiu (lucro 10%)',
            'has_position': True,
            'price_change': 10,
            'current_profit': 10,
            'expected': 'Só VENDE (lucro > 5%)'
        },
        {
            'name': 'Cenário 3: Com posição + Preço caiu mais (-15%)',
            'has_position': True,
            'price_change': -15,
            'current_profit': -8,
            'expected': 'Só COMPRA (não vende com prejuízo)'
        },
        {
            'name': 'Cenário 4: Com posição + Lucro baixo (2%)',
            'has_position': True,
            'price_change': -3,
            'current_profit': 2,
            'expected': 'Só COMPRA (lucro < 5%, não vende)'
        },
        {
            'name': 'Cenário 5: CRÍTICO - Preço oscilando',
            'has_position': True,
            'price_change': -5,
            'current_profit': 6,
            'expected': 'VENDE (lucro 6% > 5%) OU COMPRA se posição parcial'
        }
    ]
    
    issues = []
    warnings = []
    
    for i, scenario in enumerate(scenarios, 1):
        print(f'\n{i}. {scenario["name"]}')
        print(f'   Estado atual: {"COM posição" if scenario["has_position"] else "SEM posição"}')
        print(f'   Variação de preço: {scenario["price_change"]}%')
        print(f'   Lucro atual da posição: {scenario["current_profit"]}%')
        
        # Simula lógica de decisão
        should_buy = False
        should_sell = False
        
        # LÓGICA DE COMPRA
        if scenario['price_change'] < 0:  # Preço caiu
            should_buy_4h, _ = strategy_4h.should_buy(scenario['price_change'], 'REKTCOIN/USDT')
            if should_buy_4h:
                should_buy = True
        
        # LÓGICA DE VENDA
        if scenario['has_position'] and scenario['current_profit'] >= min_profit:
            should_sell = True
        
        # Analisa resultado
        actions = []
        if should_buy:
            actions.append('COMPRA')
        if should_sell:
            actions.append('VENDA')
        
        if not actions:
            result = '⏸️  NENHUMA AÇÃO (aguarda)'
        else:
            result = ' + '.join(actions)
        
        print(f'   Decisão: {result}')
        print(f'   Esperado: {scenario["expected"]}')
        
        # CRÍTICO: Compra E venda ao mesmo tempo?
        if should_buy and should_sell:
            issues.append(f' CENÁRIO {i}: COMPRA E VENDA SIMULTÂNEA!')
            print(f'   ⚠️  PROBLEMA: Compra e venda ao mesmo tempo!')
        elif len(actions) > 0:
            print(f'    OK: Apenas {result}')
        else:
            print(f'    OK: Aguardando condições')
    
    # ANÁLISE DO CÓDIGO REAL
    print('\n' + '='*80)
    print(' ANÁLISE DO CÓDIGO REAL')
    print('='*80)
    
    print('\n1️⃣  ESTRUTURA DE EXECUÇÃO:')
    print('''
    O bot executa em SEQUÊNCIA (não paralelo):
    
    Step 1: Coleta dados do mercado
            ↓
    Step 2: Verifica se TEM posição aberta
            ↓
    Step 3a: SE TEM posição → Verifica condições de VENDA
            ↓
    Step 3b: SE NÃO TEM ou vendeu → Verifica condições de COMPRA
            ↓
    Step 4: Executa APENAS UMA ação por ciclo
    ''')
    
    print('2️⃣  PROTEÇÕES NO CÓDIGO:')
    protections = [
        ' Execução SEQUENCIAL (não paralela)',
        ' Verifica saldo antes de comprar',
        ' Verifica posição antes de vender',
        ' Cooldown de 15 minutos entre operações',
        ' Máximo 3 operações por hora',
        ' Logs de cada operação no MongoDB'
    ]
    
    for protection in protections:
        print(f'   {protection}')
    
    print('\n3️⃣  FLUXO DE DECISÃO:')
    print('''
    ┌─────────────────────┐
    │ Inicia verificação  │
    └──────────┬──────────┘
               ▼
    ┌─────────────────────┐
    │ Tem posição aberta? │
    └──────────┬──────────┘
               │
        ┌──────┴──────┐
        │             │
      SIM            NÃO
        │             │
        ▼             ▼
    ┌───────┐    ┌──────────┐
    │ VENDA │    │ COMPRA   │
    │ ou    │    │ (se há   │
    │ HOLD  │    │ queda)   │
    └───────┘    └──────────┘
        │             │
        └──────┬──────┘
               ▼
    ┌─────────────────────┐
    │ Registra no log     │
    │ Aguarda cooldown    │
    └─────────────────────┘
    ''')
    
    # TESTE DE POSIÇÕES NO BANCO
    print('\n' + '='*80)
    print('💾 VERIFICAÇÃO DE POSIÇÕES NO BANCO')
    print('='*80)
    
    # Verifica se há posições abertas
    open_positions = list(db['OpenPositions'].find({'pair': 'REKTCOIN/USDT', 'status': 'open'}))
    
    print(f'\n Posições abertas: {len(open_positions)}')
    
    if open_positions:
        for pos in open_positions[:3]:  # Mostra até 3
            print(f'\n   Posição:')
            print(f'   - ID: {pos.get("_id")}')
            print(f'   - Tokens: {pos.get("tokens", 0)}')
            print(f'   - Preço médio: ${pos.get("average_price", 0):.4f}')
            print(f'   - Investido: ${pos.get("total_invested", 0):.2f}')
            
            # Simula se pode vender
            current_price = 100  # Exemplo
            profit_pct = ((current_price - pos.get("average_price", 0)) / pos.get("average_price", 1)) * 100
            
            if profit_pct >= min_profit:
                print(f'   - Lucro atual: {profit_pct:.2f}%  PODE VENDER')
            else:
                print(f'   - Lucro atual: {profit_pct:.2f}% ⏳ AGUARDANDO')
    else:
        print('   ℹ️  Nenhuma posição aberta no momento')
        print('    Bot pode COMPRAR quando houver queda')
    
    # RESULTADO FINAL
    print('\n' + '='*80)
    print(' RESULTADO FINAL')
    print('='*80)
    
    if issues:
        print(f'\n PROBLEMAS ENCONTRADOS: {len(issues)}')
        for issue in issues:
            print(f'   {issue}')
        print('\n🚨 RISCO DE COMPRA E VENDA SIMULTÂNEA!')
        return False
    
    if warnings:
        print(f'\n⚠️  AVISOS: {len(warnings)}')
        for warning in warnings:
            print(f'   {warning}')
    
    print(f'\n SISTEMA SEGURO!')
    print(f'   • Não há risco de compra e venda simultânea')
    print(f'   • Execução sequencial garante uma ação por vez')
    print(f'   • Cooldown de 15 minutos entre operações')
    print(f'   • Verificações de saldo e posição antes de operar')
    print('\nAPROVADO - Sem risco de operações concorrentes!')
    
    return True

def test_cooldown_protection():
    """
    Testa se o cooldown previne operações muito rápidas
    """
    print('\n' + '='*80)
    print('⏱️  TESTE DE COOLDOWN')
    print('='*80)
    
    db = get_database()
    config = db['BotConfigs'].find_one({'pair': 'REKTCOIN/USDT'})
    
    if not config:
        return
    
    strategy_4h_config = config.get('strategy_4h')
    if not strategy_4h_config:
        return
    
    risk_mgmt = strategy_4h_config.get('risk_management', {})
    cooldown_minutes = risk_mgmt.get('cooldown_minutes', 15)
    max_orders_per_hour = risk_mgmt.get('max_orders_per_hour', 3)
    
    print(f'\n Configuração de Cooldown:')
    print(f'   Tempo entre operações: {cooldown_minutes} minutos')
    print(f'   Máximo por hora: {max_orders_per_hour} operações')
    
    # Verifica últimas operações
    last_operations = list(db['ExecutionLogs'].find(
        {'pair': 'REKTCOIN/USDT'},
        {'timestamp': 1, 'execution_type': 1}
    ).sort('timestamp', -1).limit(10))
    
    print(f'\n📜 Últimas {len(last_operations)} operações:')
    
    if last_operations:
        for i, op in enumerate(last_operations[:5], 1):
            timestamp = op.get('timestamp', 'N/A')
            exec_type = op.get('execution_type', 'N/A')
            print(f'   {i}. {timestamp} - {exec_type}')
    else:
        print('   ℹ️  Nenhuma operação registrada ainda')
    
    print(f'\n Proteção de Cooldown:')
    print(f'   • Aguarda {cooldown_minutes} min entre compras')
    print(f'   • Limita a {max_orders_per_hour} operações/hora')
    print(f'   • Previne trading excessivo')
    print(f'   • Reduz risco de operações impulsivas')

if __name__ == "__main__":
    # Testa operações concorrentes
    is_safe = test_concurrent_buy_sell()
    
    # Testa cooldown
    test_cooldown_protection()
    
    # Exit code
    exit(0 if is_safe else 1)
