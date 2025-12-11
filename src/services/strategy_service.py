"""
Strategy Service - Manage trading strategies per exchange and token

Advanced rule-based strategies with:
- Multiple take profit levels with quantity splits
- Trailing stop loss for dynamic protection
- DCA (Dollar Cost Average) on buy dips
- Trading hours and blackout periods
- Max daily/weekly loss limits (circuit breakers)
- Cooldown period to avoid over-trading
- Volume and liquidity validations
- RSI and technical indicators support
"""

from datetime import datetime
from typing import Dict, List, Optional, Union
from bson import ObjectId
from src.utils.logger import get_logger
from src.validators.strategy_rules_validator import StrategyRulesValidator


# Initialize logger
logger = get_logger(__name__)


class StrategyService:
    """Service to manage trading strategies"""
    
    def __init__(self, db):
        """Initialize with database connection"""
        self.db = db
        self.collection = db.strategies
        
        # Create indexes for efficient queries
        self._ensure_indexes()
    
    def _ensure_indexes(self):
        """Create indexes if they don't exist"""
        try:
            # Unique index for user_id + exchange_id + token
            self.collection.create_index([
                ('user_id', 1),
                ('exchange_id', 1),
                ('token', 1)
            ], unique=True)
            
            # Index for active strategies
            self.collection.create_index([
                ('user_id', 1),
                ('is_active', 1)
            ])
            
        except Exception as e:
            logger.warning(f"Could not create indexes: {e}")
    
    def create_strategy(
        self,
        user_id: str,
        exchange_id: str,
        token: str,
        rules: Union[Dict, float, int] = None,
        template: Optional[str] = None,
        is_active: bool = True,
        # Backward compatibility parameters
        take_profit_percent: Optional[float] = None,
        stop_loss_percent: Optional[float] = None,
        buy_dip_percent: Optional[float] = None
    ) -> Dict:
        """
        Create a new trading strategy for a specific token on an exchange
        
        Supports multiple creation modes:
        1. Template mode: Pass template='simple', 'conservative', or 'aggressive'
        2. Rules mode: Pass complete rules dict
        3. Legacy mode: Pass individual percentage parameters
        
        Args:
            user_id: User ID
            exchange_id: Exchange MongoDB ObjectId
            token: Token symbol (e.g., 'BTC', 'ETH')
            rules: Dict with advanced rules (optional if template is provided)
            template: Template name ('simple', 'conservative', 'aggressive')
            is_active: Whether strategy is active
            take_profit_percent: DEPRECATED - Use rules or template instead
            stop_loss_percent: DEPRECATED - Use rules or template instead
            buy_dip_percent: DEPRECATED - Use rules or template instead
            
        Returns:
            Dict with created strategy or error
        """
        try:
            # === PRIORITY 1: Template Mode ===
            if template:
                try:
                    rules = StrategyRulesValidator.get_template_rules(template)
                    logger.info(f"Using template: {template}")
                except ValueError as e:
                    return {
                        'success': False,
                        'error': str(e)
                    }
            
            # === PRIORITY 2: Backward Compatibility ===
            elif take_profit_percent is not None or stop_loss_percent is not None:
                logger.warning("Using deprecated parameters. Please use 'template' or 'rules' instead.")
                rules = {
                    'take_profit_percent': take_profit_percent or 5.0,
                    'stop_loss_percent': stop_loss_percent or 2.0,
                    'buy_dip_percent': buy_dip_percent
                }
            
            # === PRIORITY 3: Default Rules ===
            elif rules is None:
                rules = StrategyRulesValidator.get_default_rules()
            
            # Normalize rules (convert old format to new if needed)
            rules = StrategyRulesValidator.normalize_rules(rules)
            
            # Validate rules
            is_valid, error_msg = StrategyRulesValidator.validate_rules(rules)
            if not is_valid:
                logger.error(f"Rule validation failed: {error_msg}")
                logger.error(f"Rules received: {rules}")
                return {
                    'success': False,
                    'error': f'Invalid rules: {error_msg}'
                }
            
            # Validate exchange exists
            exchange = self.db.exchanges.find_one({'_id': ObjectId(exchange_id)})
            if not exchange:
                return {
                    'success': False,
                    'error': f'Exchange not found: {exchange_id}'
                }
            
            # Check if strategy already exists
            existing = self.collection.find_one({
                'user_id': user_id,
                'exchange_id': exchange_id,
                'token': token.upper()
            })
            
            if existing:
                return {
                    'success': False,
                    'error': f'Strategy already exists for {token} on {exchange["nome"]}. Use update instead.'
                }
            
            # Create strategy document with full tracking
            strategy = {
                'user_id': user_id,
                'exchange_id': exchange_id,
                'exchange_name': exchange['nome'],
                'token': token.upper(),
                'rules': rules,
                'is_active': is_active,
                
                # Execution tracking
                'execution_stats': {
                    'total_executions': 0,
                    'total_sells': 0,
                    'total_buys': 0,
                    'last_execution_at': None,
                    'last_execution_type': None,
                    'last_execution_reason': None
                },
                
                # Performance tracking
                'performance': {
                    'total_profit_usd': 0.0,
                    'total_loss_usd': 0.0,
                    'win_rate': 0.0,
                    'daily_pnl': 0.0,
                    'weekly_pnl': 0.0,
                    'monthly_pnl': 0.0
                },
                
                # Trailing stop state
                'trailing_stop_state': {
                    'is_active': False,
                    'highest_price': None,
                    'current_stop_price': None,
                    'activated_at': None
                },
                
                # Cooldown state
                'cooldown_state': {
                    'is_cooling': False,
                    'cooldown_until': None,
                    'last_action': None
                },
                
                # Timestamps
                'created_at': datetime.utcnow(),
                'updated_at': datetime.utcnow(),
                'last_checked_at': None
            }
            
            result = self.collection.insert_one(strategy)
            strategy['_id'] = str(result.inserted_id)
            
            # Log creation with summary
            tp_count = len(rules.get('take_profit_levels', []))
            sl_percent = rules.get('stop_loss', {}).get('percent', 0)
            trailing = rules.get('stop_loss', {}).get('trailing_enabled', False)
            
            logger.info(
                f"Strategy created: {token} on {exchange['nome']} "
                f"(TP levels: {tp_count}, SL: -{sl_percent}%, Trailing: {trailing})"
            )
            
            return {
                'success': True,
                'strategy': self._format_strategy(strategy)
            }
            
        except Exception as e:
            import traceback
            logger.error(f"Error creating strategy: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def update_strategy(
        self,
        strategy_id: str,
        take_profit_percent: Optional[float] = None,
        stop_loss_percent: Optional[float] = None,
        buy_dip_percent: Optional[float] = None,
        is_active: Optional[bool] = None
    ) -> Dict:
        """
        Update an existing strategy
        
        Args:
            strategy_id: Strategy MongoDB ObjectId
            take_profit_percent: New take profit percentage (optional)
            stop_loss_percent: New stop loss percentage (optional)
            buy_dip_percent: New buy dip percentage (optional)
            is_active: New active status (optional)
            
        Returns:
            Dict with updated strategy or error
        """
        try:
            # Find strategy
            strategy = self.collection.find_one({'_id': ObjectId(strategy_id)})
            
            if not strategy:
                return {
                    'success': False,
                    'error': f'Strategy not found: {strategy_id}'
                }
            
            # Build update document
            update_fields = {
                'updated_at': datetime.utcnow()
            }
            
            if take_profit_percent is not None:
                if take_profit_percent <= 0:
                    return {
                        'success': False,
                        'error': 'take_profit_percent must be positive'
                    }
                update_fields['rules.take_profit_percent'] = float(take_profit_percent)
            
            if stop_loss_percent is not None:
                if stop_loss_percent <= 0:
                    return {
                        'success': False,
                        'error': 'stop_loss_percent must be positive'
                    }
                update_fields['rules.stop_loss_percent'] = float(stop_loss_percent)
            
            if buy_dip_percent is not None:
                if buy_dip_percent <= 0:
                    return {
                        'success': False,
                        'error': 'buy_dip_percent must be positive'
                    }
                update_fields['rules.buy_dip_percent'] = float(buy_dip_percent)
            
            if is_active is not None:
                update_fields['is_active'] = is_active
            
            # Update strategy
            self.collection.update_one(
                {'_id': ObjectId(strategy_id)},
                {'$set': update_fields}
            )
            
            # Get updated strategy
            updated_strategy = self.collection.find_one({'_id': ObjectId(strategy_id)})
            
            logger.info(f"Strategy updated: {strategy_id}")
            
            return {
                'success': True,
                'strategy': self._format_strategy(updated_strategy)
            }
            
        except Exception as e:
            logger.error(f"Error updating strategy: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def delete_strategy(self, strategy_id: str) -> Dict:
        """
        Delete a strategy
        
        Args:
            strategy_id: Strategy MongoDB ObjectId
            
        Returns:
            Dict with success status
        """
        try:
            result = self.collection.delete_one({'_id': ObjectId(strategy_id)})
            
            if result.deleted_count > 0:
                logger.info(f"Strategy deleted: {strategy_id}")
                return {
                    'success': True,
                    'message': 'Strategy deleted successfully'
                }
            else:
                return {
                    'success': False,
                    'error': f'Strategy not found: {strategy_id}'
                }
                
        except Exception as e:
            logger.error(f"Error deleting strategy: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_strategy(self, strategy_id: str) -> Optional[Dict]:
        """
        Get a single strategy by ID
        
        Args:
            strategy_id: Strategy MongoDB ObjectId
            
        Returns:
            Strategy dict or None
        """
        try:
            strategy = self.collection.find_one({'_id': ObjectId(strategy_id)})
            
            if strategy:
                return self._format_strategy(strategy)
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting strategy: {e}")
            return None
    
    def get_user_strategies(
        self,
        user_id: str,
        exchange_id: Optional[str] = None,
        token: Optional[str] = None,
        is_active: Optional[bool] = None
    ) -> List[Dict]:
        """
        Get all strategies for a user with optional filters
        
        Args:
            user_id: User ID
            exchange_id: Filter by exchange (optional)
            token: Filter by token (optional)
            is_active: Filter by active status (optional)
            
        Returns:
            List of strategies
        """
        try:
            # Build query
            query = {'user_id': user_id}
            
            if exchange_id:
                query['exchange_id'] = exchange_id
            
            if token:
                query['token'] = token.upper()
            
            if is_active is not None:
                query['is_active'] = is_active
            
            # Get strategies
            strategies = list(self.collection.find(query).sort('created_at', -1))
            
            return [self._format_strategy(s) for s in strategies]
            
        except Exception as e:
            logger.error(f"Error getting user strategies: {e}")
            return []
    
    def check_strategy_triggers(
        self,
        strategy_id: str,
        current_price: float,
        entry_price: float
    ) -> Dict:
        """
        Check if a strategy should trigger based on current price vs entry price
        
        Args:
            strategy_id: Strategy MongoDB ObjectId
            current_price: Current token price
            entry_price: Price when token was acquired
            
        Returns:
            Dict with trigger information
        """
        try:
            strategy = self.collection.find_one({'_id': ObjectId(strategy_id)})
            
            if not strategy or not strategy.get('is_active'):
                return {
                    'should_trigger': False,
                    'reason': 'Strategy not found or inactive'
                }
            
            # Calculate price change percentage
            price_change_percent = ((current_price - entry_price) / entry_price) * 100
            
            rules = strategy['rules']
            take_profit = rules['take_profit_percent']
            stop_loss = rules['stop_loss_percent']
            buy_dip = rules.get('buy_dip_percent')
            
            # Check take profit (positive change)
            if price_change_percent >= take_profit:
                return {
                    'should_trigger': True,
                    'action': 'SELL',
                    'reason': 'TAKE_PROFIT',
                    'trigger_percent': take_profit,
                    'current_change_percent': round(price_change_percent, 2),
                    'strategy': self._format_strategy(strategy)
                }
            
            # Check stop loss (negative change)
            if price_change_percent <= -stop_loss:
                return {
                    'should_trigger': True,
                    'action': 'SELL',
                    'reason': 'STOP_LOSS',
                    'trigger_percent': -stop_loss,
                    'current_change_percent': round(price_change_percent, 2),
                    'strategy': self._format_strategy(strategy)
                }
            
            # Check buy dip (negative change)
            if buy_dip and price_change_percent <= -buy_dip:
                return {
                    'should_trigger': True,
                    'action': 'BUY',
                    'reason': 'BUY_DIP',
                    'trigger_percent': -buy_dip,
                    'current_change_percent': round(price_change_percent, 2),
                    'strategy': self._format_strategy(strategy)
                }
            
            # No trigger
            return {
                'should_trigger': False,
                'reason': 'No trigger conditions met',
                'current_change_percent': round(price_change_percent, 2),
                'next_triggers': {
                    'take_profit_at': round(take_profit - price_change_percent, 2),
                    'stop_loss_at': round(-stop_loss - price_change_percent, 2),
                    'buy_dip_at': round(-buy_dip - price_change_percent, 2) if buy_dip else None
                }
            }
            
        except Exception as e:
            logger.error(f"Error checking strategy triggers: {e}")
            return {
                'should_trigger': False,
                'reason': f'Error: {str(e)}'
            }
    
    def record_execution(self, strategy_id: str) -> bool:
        """
        Record that a strategy was executed
        
        Args:
            strategy_id: Strategy MongoDB ObjectId
            
        Returns:
            True if recorded successfully
        """
        try:
            result = self.collection.update_one(
                {'_id': ObjectId(strategy_id)},
                {
                    '$set': {
                        'last_executed_at': datetime.utcnow()
                    },
                    '$inc': {
                        'execution_count': 1
                    }
                }
            )
            
            return result.modified_count > 0
            
        except Exception as e:
            logger.error(f"Error recording execution: {e}")
            return False
    
    def _format_strategy(self, strategy: Dict) -> Dict:
        """Format strategy for API response"""
        return {
            'id': str(strategy['_id']),
            'user_id': strategy['user_id'],
            'exchange_id': strategy['exchange_id'],
            'exchange_name': strategy['exchange_name'],
            'token': strategy['token'],
            'rules': strategy['rules'],  # Return complete rules object
            'is_active': strategy['is_active'],
            'execution_stats': strategy.get('execution_stats', {
                'total_executions': 0,
                'total_sells': 0,
                'total_buys': 0,
                'last_execution_at': None,
                'last_execution_type': None,
                'last_execution_reason': None
            }),
            'performance': strategy.get('performance', {
                'total_profit_usd': 0.0,
                'total_loss_usd': 0.0,
                'win_rate': 0.0,
                'daily_pnl': 0.0,
                'weekly_pnl': 0.0,
                'monthly_pnl': 0.0
            }),
            'trailing_stop_state': strategy.get('trailing_stop_state', {
                'is_active': False,
                'highest_price': None,
                'current_stop_price': None,
                'activated_at': None
            }),
            'cooldown_state': strategy.get('cooldown_state', {
                'is_cooling': False,
                'cooldown_until': None,
                'last_action': None
            }),
            'created_at': strategy['created_at'].isoformat() if strategy.get('created_at') else None,
            'updated_at': strategy['updated_at'].isoformat() if strategy.get('updated_at') else None,
            'last_checked_at': strategy.get('last_checked_at').isoformat() if strategy.get('last_checked_at') else None,
            'execution_count': strategy.get('execution_count', 0)
        }


def get_strategy_service(db):
    """Factory function to create StrategyService instance"""
    return StrategyService(db)
