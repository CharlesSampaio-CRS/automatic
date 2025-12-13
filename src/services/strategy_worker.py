"""
Strategy Worker Bot - Monitors active strategies and triggers orders
Runs as background scheduler checking all active strategies periodically
"""

from typing import Dict, List
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from src.utils.logger import get_logger


# Initialize logger
logger = get_logger(__name__)


class StrategyWorker:
    """Background worker to monitor strategies and execute trades"""
    
    def __init__(
        self,
        db,
        strategy_service,
        position_service,
        order_execution_service,
        notification_service=None,
        dry_run: bool = False,
        check_interval_minutes: int = 5
    ):
        """
        Initialize strategy worker
        
        Args:
            db: MongoDB database connection
            strategy_service: StrategyService instance
            position_service: PositionService instance
            order_execution_service: OrderExecutionService instance
            notification_service: NotificationService instance (optional)
            dry_run: If True, simulates orders without executing
            check_interval_minutes: How often to check strategies (default: 5 min)
        """
        self.db = db
        self.strategy_service = strategy_service
        self.position_service = position_service
        self.order_execution_service = order_execution_service
        self.notification_service = notification_service
        self.dry_run = dry_run
        self.check_interval = check_interval_minutes
        
        # Initialize scheduler
        self.scheduler = BackgroundScheduler()
        self.is_running = False
        
        if dry_run:
            logger.warning("⚠️  STRATEGY WORKER DRY-RUN MODE - Orders will be simulated")
    
    def start(self):
        """Start the strategy worker scheduler"""
        if self.is_running:
            logger.warning("Strategy worker is already running")
            return
        
        # Schedule strategy checks
        self.scheduler.add_job(
            self._check_all_strategies,
            'interval',
            minutes=self.check_interval,
            id='strategy_worker',
            name='Strategy Worker - Check and Execute',
            replace_existing=True
        )
        
        self.scheduler.start()
        self.is_running = True
        
        logger.info(f"✅ Strategy worker started (checking every {self.check_interval} minutes)")
        
        # Run first check immediately
        self._check_all_strategies()
    
    def stop(self):
        """Stop the strategy worker scheduler"""
        if not self.is_running:
            logger.warning("Strategy worker is not running")
            return
        
        self.scheduler.shutdown()
        self.is_running = False
        
        logger.info("Strategy worker stopped")
    
    def _check_all_strategies(self):
        """Check all active strategies and trigger orders if conditions met"""
        try:
            logger.info("🔍 Checking all active strategies...")
            
            # Get all active strategies
            strategies = list(self.db.strategies.find({'is_active': True}))
            
            if not strategies:
                logger.info("No active strategies found")
                return
            
            logger.info(f"Found {len(strategies)} active strategies to check")
            
            # Check each strategy
            triggered_count = 0
            error_count = 0
            
            for strategy in strategies:
                try:
                    result = self._check_and_execute_strategy(strategy)
                    if result['triggered']:
                        triggered_count += 1
                except Exception as e:
                    error_count += 1
                    logger.error(f"Error checking strategy {strategy['_id']}: {e}")
            
            logger.info(
                f"✅ Strategy check completed - "
                f"Triggered: {triggered_count}, "
                f"Errors: {error_count}, "
                f"Total: {len(strategies)}"
            )
            
        except Exception as e:
            logger.error(f"Error in strategy worker: {e}")
    
    def _check_and_execute_strategy(self, strategy: Dict) -> Dict:
        """
        Check if strategy should trigger and execute order
        
        Args:
            strategy: Strategy document from MongoDB
            
        Returns:
            Dict with execution result
        """
        try:
            user_id = strategy['user_id']
            exchange_id = str(strategy['exchange_id'])
            token = strategy['token']
            
            # Get position to check entry price
            position = self.position_service.get_position(user_id, exchange_id, token)
            
            if not position:
                # No position yet - sync from current balance
                logger.info(f"No position found for {token} on {exchange_id}, syncing from balance...")
                self.position_service.sync_from_balance(user_id, exchange_id, token)
                position = self.position_service.get_position(user_id, exchange_id, token)
                
                if not position:
                    logger.warning(f"Could not create position for {token} on {exchange_id}")
                    return {'triggered': False, 'reason': 'no_position'}
            
            # Get current price from balance service
            from src.services.balance_service import get_balance_service
            balance_service = get_balance_service(self.db)
            
            # Fetch current balance with price
            balances = balance_service.fetch_all_balances(
                user_id=user_id,
                exchange_ids=[exchange_id],
                include_changes=False
            )
            
            # Find token in balances
            current_price = None
            current_amount = None
            
            for balance in balances:
                if balance['exchange_id'] == exchange_id:
                    for asset in balance['balances']:
                        if asset['asset'] == token:
                            current_price = asset.get('price_usd')
                            current_amount = asset.get('free', 0)
                            break
            
            if not current_price:
                logger.warning(f"Could not fetch current price for {token} on {exchange_id}")
                return {'triggered': False, 'reason': 'no_price'}
            
            # Check if strategy should trigger
            trigger_result = self.strategy_service.check_strategy_triggers(
                strategy_id=str(strategy['_id']),
                current_price=current_price,
                entry_price=position['entry_price']
            )
            
            if not trigger_result['should_trigger']:
                # No trigger - all good
                return {'triggered': False, 'reason': 'no_trigger'}
            
            # Strategy triggered! Execute order
            action = trigger_result['action']
            reason = trigger_result['reason']
            quantity_percent = trigger_result.get('quantity_percent', 100)  # Default to 100%
            
            logger.warning(
                f"🎯 STRATEGY TRIGGERED! "
                f"User: {user_id}, "
                f"Exchange: {exchange_id}, "
                f"Token: {token}, "
                f"Action: {action}, "
                f"Reason: {reason}, "
                f"Quantity: {quantity_percent}%, "
                f"Entry: ${position['entry_price']:.4f}, "
                f"Current: ${current_price:.4f}"
            )
            
            # Calculate actual amount based on quantity_percent
            order_result = None
            actual_amount = 0
            
            if action == 'SELL':
                # Calculate amount to sell based on quantity_percent
                total_amount = current_amount if current_amount else position['amount']
                actual_amount = total_amount * (quantity_percent / 100.0)
                
                if actual_amount <= 0:
                    logger.warning(f"Invalid sell amount: {actual_amount}")
                    return {'triggered': True, 'executed': False, 'reason': 'invalid_amount'}
                
                # Execute sell order (market order for immediate execution)
                order_result = self.order_execution_service.execute_market_sell(
                    user_id=user_id,
                    exchange_id=exchange_id,
                    token=token,
                    amount=actual_amount
                )
            
            elif action == 'BUY':
                # Calculate buy amount based on quantity_percent
                # For DCA: quantity_percent is the percentage of initial position to buy
                # For simple buy_dip: use quantity_percent of position amount
                base_amount = position['amount']
                actual_amount = base_amount * (quantity_percent / 100.0)
                
                if actual_amount <= 0:
                    logger.warning(f"Invalid buy amount: {actual_amount}")
                    return {'triggered': True, 'executed': False, 'reason': 'invalid_amount'}
                
                order_result = self.order_execution_service.execute_market_buy(
                    user_id=user_id,
                    exchange_id=exchange_id,
                    token=token,
                    amount=actual_amount
                )
            
            # Check order result
            if not order_result or not order_result.get('success'):
                error = order_result.get('error', 'Unknown error') if order_result else 'No result'
                logger.error(f"Order execution failed: {error}")
                
                # Send notification about failure
                if self.notification_service:
                    self.notification_service.notify_order_failed(
                        user_id=user_id,
                        strategy=strategy,
                        error=error
                    )
                
                return {
                    'triggered': True,
                    'executed': False,
                    'error': error
                }
            
            # Order executed successfully!
            order = order_result['order']
            
            logger.info(
                f"✅ Order executed successfully! "
                f"Order ID: {order['id']}, "
                f"Type: {order['type']}, "
                f"Side: {order['side']}, "
                f"Amount: {order['amount']}, "
                f"Status: {order['status']}"
            )
            
            # Calculate PnL for sells
            pnl_usd = None
            if action == 'SELL':
                filled_amount = order.get('filled', actual_amount)
                avg_price = order.get('average', current_price)
                entry_price = position['entry_price']
                pnl_usd = filled_amount * (avg_price - entry_price)
            
            # Record execution in strategy with full tracking
            self.strategy_service.record_execution(
                strategy_id=str(strategy['_id']),
                action=action,
                reason=reason,
                price=order.get('average', current_price),
                amount=order.get('filled', actual_amount),
                pnl_usd=pnl_usd
            )
            
            # Mark TP/DCA levels as executed
            if 'tp_level' in trigger_result:
                self.strategy_service.mark_tp_level_executed(
                    str(strategy['_id']), 
                    trigger_result['tp_level']
                )
            elif 'dca_level' in trigger_result:
                self.strategy_service.mark_dca_level_executed(
                    str(strategy['_id']), 
                    trigger_result['dca_level']
                )
            
            # Update position based on order
            if action == 'SELL' and order.get('filled'):
                # Record sell in position
                self.position_service.record_sell(
                    user_id=user_id,
                    exchange_id=exchange_id,
                    token=token,
                    amount=order['filled'],
                    price=order.get('average', current_price),
                    total_received=order.get('cost', order['filled'] * current_price),
                    order_id=order['id']
                )
            
            elif action == 'BUY' and order.get('filled'):
                # Record buy in position
                self.position_service.record_buy(
                    user_id=user_id,
                    exchange_id=exchange_id,
                    token=token,
                    amount=order['filled'],
                    price=order.get('average', current_price),
                    total_cost=order.get('cost', order['filled'] * current_price),
                    order_id=order['id']
                )
            
            # Send notification
            if self.notification_service:
                self.notification_service.notify_strategy_executed(
                    user_id=user_id,
                    strategy=strategy,
                    order=order,
                    reason=reason
                )
            
            return {
                'triggered': True,
                'executed': True,
                'order_id': order['id'],
                'action': action,
                'reason': reason
            }
            
        except Exception as e:
            logger.error(f"Error checking/executing strategy: {e}")
            return {
                'triggered': False,
                'error': str(e)
            }


def get_strategy_worker(
    db,
    strategy_service,
    position_service,
    order_execution_service,
    notification_service=None,
    dry_run: bool = False,
    check_interval_minutes: int = 5
):
    """Factory function to create StrategyWorker instance"""
    return StrategyWorker(
        db=db,
        strategy_service=strategy_service,
        position_service=position_service,
        order_execution_service=order_execution_service,
        notification_service=notification_service,
        dry_run=dry_run,
        check_interval_minutes=check_interval_minutes
    )
