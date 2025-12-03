"""
Script para ajustar configurações de segurança no MongoDB
Corrige os 3 avisos detectados na validação
"""

from src.database.mongodb_connection import get_database

def adjust_min_profit():
    """Aumenta lucro mínimo de 1% para 5%"""
    db = get_database()
    
    result = db['BotConfigs'].update_one(
        {'pair': 'REKTCOIN/USDT'},
        {'$set': {'strategy_4h.sell_strategy.min_profit': 5}}
    )
    
    if result.modified_count > 0:
        print('   ✅ Lucro mínimo atualizado: 1% → 5%')
        return True
    else:
        print('   ⚠️  Nenhuma alteração (valor já era 5%)')
        return False

def fix_threshold_overlap():
    """Remove sobreposição mudando threshold 24h de -10% para -12%"""
    db = get_database()
    
    # Busca o threshold atual
    config = db['BotConfigs'].find_one({'pair': 'REKTCOIN/USDT'})
    thresholds = config.get('trading_strategy', {}).get('buy_on_dip', {}).get('thresholds', [])
    
    # Encontra o threshold -10
    updated = False
    new_thresholds = []
    for t in thresholds:
        if t.get('variation_max') == -10:
            t['variation_max'] = -12
            t['variation_min'] = -15  # Ajusta o range
            updated = True
        new_thresholds.append(t)
    
    if updated:
        result = db['BotConfigs'].update_one(
            {'pair': 'REKTCOIN/USDT'},
            {'$set': {'trading_strategy.buy_on_dip.thresholds': new_thresholds}}
        )
        
        if result.modified_count > 0:
            print('   ✅ Threshold 24h ajustado: -10% → -12%')
            print('   ℹ️  Agora: 4h usa -10%, 24h usa -12% (sem sobreposição)')
            return True
    
    print('   ⚠️  Nenhuma alteração necessária')
    return False

def reduce_exposure():
    """Reduz percentuais de investimento para diminuir exposição"""
    db = get_database()
    
    # Valores atuais: [10, 20, 30]
    # Valores novos: [8, 15, 20]
    
    config = db['BotConfigs'].find_one({'pair': 'REKTCOIN/USDT'})
    levels = config.get('strategy_4h', {}).get('buy_strategy', {}).get('levels', [])
    
    # Ajusta percentuais
    new_levels = []
    for i, level in enumerate(levels):
        new_level = level.copy()
        if i == 0:  # -3%
            new_level['percentage_of_balance'] = 8
        elif i == 1:  # -5%
            new_level['percentage_of_balance'] = 15
        elif i == 2:  # -10%
            new_level['percentage_of_balance'] = 20
        new_levels.append(new_level)
    
    result = db['BotConfigs'].update_one(
        {'pair': 'REKTCOIN/USDT'},
        {'$set': {'strategy_4h.buy_strategy.levels': new_levels}}
    )
    
    if result.modified_count > 0:
        print('   ✅ Percentuais ajustados:')
        print('      -3%: 10% → 8%')
        print('      -5%: 20% → 15%')
        print('     -10%: 30% → 20%')
        print('   ℹ️  Exposição em crash -50%: 64.7% → ~50%')
        return True
    else:
        print('   ⚠️  Nenhuma alteração')
        return False

def show_menu():
    """Mostra menu interativo"""
    print('='*80)
    print('🔧 AJUSTES DE SEGURANÇA')
    print('='*80)
    print()
    print('Escolha o que deseja ajustar:')
    print()
    print('1️⃣  Aumentar lucro mínimo (1% → 5%)')
    print('     Impacto: Vendas só com lucro maior, mais seguro')
    print()
    print('2️⃣  Remover sobreposição de thresholds (-10%)')
    print('     Impacto: Evita comprar duas vezes no mesmo nível')
    print()
    print('3️⃣  Reduzir exposição em crash (64.7% → ~50%)')
    print('     Impacto: Investe menos em quedas grandes, mais conservador')
    print()
    print('4️⃣  Aplicar TODOS os ajustes (RECOMENDADO)')
    print()
    print('0️⃣  Cancelar (não alterar nada)')
    print()
    print('='*80)
    
    choice = input('\nSua escolha (0-4): ').strip()
    return choice

def main():
    """Executa ajustes escolhidos pelo usuário"""
    choice = show_menu()
    
    if choice == '0':
        print('\n❌ Cancelado. Nenhuma alteração feita.')
        return
    
    print('\n' + '='*80)
    print('⚙️  EXECUTANDO AJUSTES')
    print('='*80)
    print()
    
    changes_made = False
    
    if choice in ['1', '4']:
        print('1️⃣  Ajustando lucro mínimo...')
        if adjust_min_profit():
            changes_made = True
        print()
    
    if choice in ['2', '4']:
        print('2️⃣  Removendo sobreposição de thresholds...')
        if fix_threshold_overlap():
            changes_made = True
        print()
    
    if choice in ['3', '4']:
        print('3️⃣  Reduzindo exposição em crash...')
        if reduce_exposure():
            changes_made = True
        print()
    
    if choice not in ['1', '2', '3', '4']:
        print('❌ Opção inválida!')
        return
    
    print('='*80)
    if changes_made:
        print('✅ AJUSTES CONCLUÍDOS!')
        print()
        print('⚠️  IMPORTANTE: Reinicie o scheduler para aplicar as mudanças:')
        print('   1. Pare o processo atual (Ctrl+C)')
        print('   2. Execute: python3 app.py')
        print()
        print('💡 Execute novamente validate_safety.py para confirmar:')
        print('   python3 validate_safety.py')
    else:
        print('ℹ️  Nenhuma alteração foi necessária (valores já estavam corretos)')
    print('='*80)

if __name__ == "__main__":
    main()
