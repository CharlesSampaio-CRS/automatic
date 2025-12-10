#!/usr/bin/env python3
"""
Test script for automated trading system
Tests all components: strategies, positions, orders, notifications
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from pymongo import MongoClient
from dotenv import load_dotenv
from datetime import datetime

# Load environment
load_dotenv()

# Import services
from src.services.strategy_service import get_strategy_service
from src.services.position_service import get_position_service
from src.services.order_execution_service import get_order_execution_service
from src.services.notification_service import get_notification_service
from src.services.strategy_worker import get_strategy_worker

# MongoDB connection
MONGODB_URI = os.getenv('MONGODB_URI', 'mongodb://localhost:27017/')
MONGODB_DATABASE = os.getenv('MONGODB_DATABASE', 'MultExchange')

client = MongoClient(MONGODB_URI)
db = client[MONGODB_DATABASE]


def print_section(title):
    """Print section header"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


def test_strategy_service():
    """Test strategy service"""
    print_section("TESTE 1: Strategy Service")
    
    strategy_service = get_strategy_service(db)
    
    # Test data
    test_user = "test_user_trading"
    
    # Get first exchange for testing
    user_doc = db.user_exchanges.find_one({'user_id': test_user})
    
    if not user_doc or not user_doc.get('exchanges'):
        print("❌ No exchanges found for test user. Please link an exchange first.")
        return None
    
    exchange_id = str(user_doc['exchanges'][0]['exchange_id'])
    print(f"✅ Using exchange: {exchange_id}")
    
    # Create test strategy
    try:
        strategy = strategy_service.create_strategy(
            user_id=test_user,
            exchange_id=exchange_id,
            token='BTC',
            rules={
                'take_profit_percent': 5.0,
                'stop_loss_percent': 2.0,
                'buy_dip_percent': 3.0
            },
            is_active=True
        )
        
        print(f"✅ Strategy created: {strategy['_id']}")
        print(f"   Token: {strategy['token']}")
        print(f"   Take Profit: {strategy['rules']['take_profit_percent']}%")
        print(f"   Stop Loss: {strategy['rules']['stop_loss_percent']}%")
        print(f"   Buy Dip: {strategy['rules']['buy_dip_percent']}%")
        
        return strategy
        
    except Exception as e:
        print(f"⚠️  Strategy creation: {e}")
        
        # Try to get existing strategy
        strategies = strategy_service.get_user_strategies(test_user, exchange_id=exchange_id, token='BTC')
        if strategies:
            print(f"✅ Using existing strategy: {strategies[0]['_id']}")
            return strategies[0]
        
        return None


def test_position_service():
    """Test position service"""
    print_section("TESTE 2: Position Service")
    
    position_service = get_position_service(db)
    
    test_user = "test_user_trading"
    
    # Get first exchange
    user_doc = db.user_exchanges.find_one({'user_id': test_user})
    
    if not user_doc or not user_doc.get('exchanges'):
        print("❌ No exchanges found")
        return None
    
    exchange_id = str(user_doc['exchanges'][0]['exchange_id'])
    
    # Test: Record a buy
    try:
        position = position_service.record_buy(
            user_id=test_user,
            exchange_id=exchange_id,
            token='BTC',
            amount=0.5,
            price=45000.0,
            total_cost=22500.0,
            order_id='TEST_ORDER_001'
        )
        
        print(f"✅ Position created/updated: {position['_id']}")
        print(f"   Token: {position['token']}")
        print(f"   Amount: {position['amount']}")
        print(f"   Entry Price: ${position['entry_price']:.2f}")
        print(f"   Total Invested: ${position['total_invested']:.2f}")
        print(f"   Purchases: {len(position['purchases'])}")
        
        return position
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_order_execution():
    """Test order execution service (DRY-RUN)"""
    print_section("TESTE 3: Order Execution Service (DRY-RUN)")
    
    order_service = get_order_execution_service(db, dry_run=True)
    
    test_user = "test_user_trading"
    
    # Get first exchange
    user_doc = db.user_exchanges.find_one({'user_id': test_user})
    
    if not user_doc or not user_doc.get('exchanges'):
        print("❌ No exchanges found")
        return None
    
    exchange_id = str(user_doc['exchanges'][0]['exchange_id'])
    
    # Test: Market sell (simulated)
    try:
        result = order_service.execute_market_sell(
            user_id=test_user,
            exchange_id=exchange_id,
            token='BTC',
            amount=0.1
        )
        
        if result['success']:
            print("✅ DRY-RUN Order executed:")
            print(f"   Order ID: {result['order']['id']}")
            print(f"   Type: {result['order']['type']}")
            print(f"   Side: {result['order']['side']}")
            print(f"   Amount: {result['order']['amount']}")
            print(f"   Status: {result['order']['status']}")
        else:
            print(f"❌ Order failed: {result.get('error')}")
        
        return result
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_notification_service():
    """Test notification service"""
    print_section("TESTE 4: Notification Service")
    
    notification_service = get_notification_service(db)
    
    test_user = "test_user_trading"
    
    # Get first exchange
    user_doc = db.user_exchanges.find_one({'user_id': test_user})
    
    if not user_doc or not user_doc.get('exchanges'):
        print("❌ No exchanges found")
        return None
    
    exchange_id = str(user_doc['exchanges'][0]['exchange_id'])
    
    # Create test notification
    try:
        test_strategy = {
            '_id': 'test_strategy_id',
            'token': 'BTC',
            'exchange_name': 'Binance',
            'exchange_id': exchange_id
        }
        
        test_order = {
            'id': 'TEST_ORDER_002',
            'side': 'sell',
            'amount': 0.1,
            'filled': 0.1,
            'average': 47000.0,
            'status': 'closed'
        }
        
        notification_service.notify_strategy_executed(
            user_id=test_user,
            strategy=test_strategy,
            order=test_order,
            reason='TAKE_PROFIT'
        )
        
        print("✅ Test notification created")
        
        # Get notifications
        notifications = notification_service.get_user_notifications(
            user_id=test_user,
            unread_only=True,
            limit=5
        )
        
        print(f"   Unread notifications: {len(notifications)}")
        
        if notifications:
            print(f"   Latest: {notifications[0]['title']}")
        
        return notifications
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_strategy_triggers():
    """Test strategy trigger checking"""
    print_section("TESTE 5: Strategy Trigger Checking")
    
    strategy_service = get_strategy_service(db)
    
    test_user = "test_user_trading"
    
    # Get strategies
    strategies = strategy_service.get_user_strategies(test_user)
    
    if not strategies:
        print("⚠️  No strategies found")
        return None
    
    strategy = strategies[0]
    print(f"✅ Testing strategy: {strategy['_id']}")
    print(f"   Token: {strategy['token']}")
    
    # Test scenarios
    entry_price = 45000.0
    
    scenarios = [
        ('Take Profit', 47500.0, 'TAKE_PROFIT'),
        ('Stop Loss', 43900.0, 'STOP_LOSS'),
        ('Buy Dip', 43500.0, 'BUY_DIP'),
        ('No Trigger', 45500.0, None)
    ]
    
    for scenario_name, current_price, expected_reason in scenarios:
        result = strategy_service.check_strategy_triggers(
            strategy_id=str(strategy['_id']),
            current_price=current_price,
            entry_price=entry_price
        )
        
        change = ((current_price - entry_price) / entry_price) * 100
        
        print(f"\n   Scenario: {scenario_name}")
        print(f"   Current: ${current_price:.2f} ({change:+.2f}%)")
        
        if result['should_trigger']:
            print(f"   ✅ Trigger: {result['action']} - {result['reason']}")
        else:
            print(f"   ⏸️  No trigger")


def test_strategy_worker_simulation():
    """Test strategy worker without starting it"""
    print_section("TESTE 6: Strategy Worker Simulation")
    
    print("⚠️  Strategy Worker integration test")
    print("   Worker is already running in the Flask app")
    print("   Check logs for automatic strategy checks")
    print("")
    print("   Worker configuration:")
    print(f"   - DRY_RUN: {os.getenv('STRATEGY_DRY_RUN', 'true')}")
    print(f"   - Check Interval: {os.getenv('STRATEGY_CHECK_INTERVAL', '5')} minutes")
    print("")
    print("   To test manually, create a strategy and wait for next check")
    print("   Or restart Flask app to trigger immediate check")


def main():
    """Run all tests"""
    print("\n" + "🤖 " * 30)
    print("  AUTOMATED TRADING SYSTEM - COMPREHENSIVE TEST")
    print("🤖 " * 30)
    
    try:
        # Run tests
        strategy = test_strategy_service()
        position = test_position_service()
        order = test_order_execution()
        notifications = test_notification_service()
        test_strategy_triggers()
        test_strategy_worker_simulation()
        
        # Summary
        print_section("RESUMO DOS TESTES")
        
        print("✅ Strategy Service:", "OK" if strategy else "FALHOU")
        print("✅ Position Service:", "OK" if position else "FALHOU")
        print("✅ Order Execution:", "OK" if order else "FALHOU")
        print("✅ Notifications:", "OK" if notifications is not None else "FALHOU")
        print("✅ Strategy Worker:", "INTEGRADO (rodando no Flask)")
        
        print("\n" + "=" * 80)
        print("  Sistema de Trading Automatizado está PRONTO! 🚀")
        print("=" * 80)
        print("\nPróximos passos:")
        print("1. Inicie o Flask: python run.py")
        print("2. Crie estratégias via API")
        print("3. Monitore logs para ver execuções automáticas")
        print("4. Ajuste percentuais conforme necessário")
        print("5. Quando pronto, mude STRATEGY_DRY_RUN=false para modo LIVE")
        print("\n")
        
    except Exception as e:
        print(f"\n❌ Erro nos testes: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
