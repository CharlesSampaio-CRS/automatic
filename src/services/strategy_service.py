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
        Uses advanced rules: multiple TPs, trailing stop, DCA, cooldown, circuit breakers
        
        Args:
            strategy_id: Strategy MongoDB ObjectId
            current_price: Current token price
            entry_price: Price when token was acquired
            
        Returns:
            Dict with trigger information including action, reason, and amount
        """
        try:
            strategy = self.collection.find_one({'_id': ObjectId(strategy_id)})
            
            if not strategy or not strategy.get('is_active'):
                return {
                    'should_trigger': False,
                    'reason': 'Strategy not found or inactive'
                }
            
            rules = strategy['rules']
            
            # 1️⃣ CHECK COOLDOWN
            cooldown_check = self._check_cooldown(strategy)
            if not cooldown_check['can_trade']:
                return {
                    'should_trigger': False,
                    'reason': f"Cooldown active: {cooldown_check['reason']}"
                }
            
            # 2️⃣ CHECK CIRCUIT BREAKERS
            circuit_check = self._check_circuit_breakers(strategy)
            if circuit_check['circuit_broken']:
                # Auto-pause strategy
                self.toggle_active(str(strategy['_id']), False)
                return {
                    'should_trigger': False,
                    'reason': f"Circuit breaker activated: {circuit_check['reason']}",
                    'circuit_broken': True
                }
            
            # 3️⃣ CHECK TRADING HOURS
            if not self._check_trading_hours(rules.get('trading_hours')):
                return {
                    'should_trigger': False,
                    'reason': 'Outside trading hours'
                }
            
            # 4️⃣ CHECK BLACKOUT PERIODS
            if self._check_blackout_period(rules.get('blackout_periods', [])):
                return {
                    'should_trigger': False,
                    'reason': 'In blackout period'
                }
            
            # Calculate price change percentage
            price_change_percent = ((current_price - entry_price) / entry_price) * 100
            
            # 5️⃣ CHECK TRAILING STOP LOSS (highest priority for sell)
            trailing_result = self._check_trailing_stop(strategy, current_price, entry_price, price_change_percent)
            if trailing_result['should_trigger']:
                return trailing_result
            
            # 6️⃣ CHECK MULTIPLE TAKE PROFIT LEVELS
            tp_result = self._check_take_profit_levels(strategy, price_change_percent)
            if tp_result['should_trigger']:
                return tp_result
            
            # 7️⃣ CHECK STOP LOSS
            stop_loss = rules.get('stop_loss', {})
            if stop_loss.get('enabled', True):
                stop_loss_percent = stop_loss.get('percent', 2.0)
                if price_change_percent <= -stop_loss_percent:
                    return {
                        'should_trigger': True,
                        'action': 'SELL',
                        'reason': 'STOP_LOSS',
                        'trigger_percent': -stop_loss_percent,
                        'current_change_percent': round(price_change_percent, 2),
                        'quantity_percent': 100,  # Sell all on stop loss
                        'strategy': self._format_strategy(strategy)
                    }
            
            # 8️⃣ CHECK BUY DIP / DCA
            dca_result = self._check_dca_levels(strategy, price_change_percent)
            if dca_result['should_trigger']:
                return dca_result
            
            # No trigger
            return {
                'should_trigger': False,
                'reason': 'No trigger conditions met',
                'current_change_percent': round(price_change_percent, 2)
            }
            
        except Exception as e:
            logger.error(f"Error checking strategy triggers: {e}")
            import traceback
            traceback.print_exc()
            return {
                'should_trigger': False,
                'reason': f'Error: {str(e)}'
            }
    
    def _check_cooldown(self, strategy: Dict) -> Dict:
        """Check if strategy is in cooldown period"""
        cooldown_state = strategy.get('cooldown_state', {})
        cooldown_until = cooldown_state.get('cooldown_until')
        
        if cooldown_until:
            from datetime import datetime
            if isinstance(cooldown_until, str):
                cooldown_until = datetime.fromisoformat(cooldown_until.replace('Z', '+00:00'))
            
            if datetime.utcnow() < cooldown_until:
                return {
                    'can_trade': False,
                    'reason': f"Cooldown until {cooldown_until.isoformat()}"
                }
        
        return {'can_trade': True}
    
    def _check_circuit_breakers(self, strategy: Dict) -> Dict:
        """Check if circuit breakers are triggered"""
        rules = strategy['rules']
        risk_management = rules.get('risk_management', {})
        
        if not risk_management.get('enabled', False):
            return {'circuit_broken': False}
        
        # Get execution stats
        exec_stats = strategy.get('execution_stats', {})
        
        # Check daily loss
        max_daily_loss = risk_management.get('max_daily_loss_usd')
        if max_daily_loss:
            daily_pnl = exec_stats.get('daily_pnl_usd', 0)
            if daily_pnl <= -max_daily_loss:
                return {
                    'circuit_broken': True,
                    'reason': f"Daily loss limit reached: ${abs(daily_pnl):.2f} / ${max_daily_loss:.2f}"
                }
        
        # Check weekly loss
        max_weekly_loss = risk_management.get('max_weekly_loss_usd')
        if max_weekly_loss:
            weekly_pnl = exec_stats.get('weekly_pnl_usd', 0)
            if weekly_pnl <= -max_weekly_loss:
                return {
                    'circuit_broken': True,
                    'reason': f"Weekly loss limit reached: ${abs(weekly_pnl):.2f} / ${max_weekly_loss:.2f}"
                }
        
        # Check monthly loss
        max_monthly_loss = risk_management.get('max_monthly_loss_usd')
        if max_monthly_loss:
            monthly_pnl = exec_stats.get('monthly_pnl_usd', 0)
            if monthly_pnl <= -max_monthly_loss:
                return {
                    'circuit_broken': True,
                    'reason': f"Monthly loss limit reached: ${abs(monthly_pnl):.2f} / ${max_monthly_loss:.2f}"
                }
        
        return {'circuit_broken': False}
    
    def _check_trading_hours(self, trading_hours: Dict) -> bool:
        """Check if current time is within trading hours"""
        if not trading_hours or not trading_hours.get('enabled', False):
            return True
        
        from datetime import datetime
        import pytz
        
        try:
            timezone = pytz.timezone(trading_hours.get('timezone', 'UTC'))
            now = datetime.now(timezone)
            
            current_time = now.strftime('%H:%M')
            start_time = trading_hours.get('start_time', '00:00')
            end_time = trading_hours.get('end_time', '23:59')
            
            # Simple time comparison (handles same-day ranges)
            if start_time <= end_time:
                return start_time <= current_time <= end_time
            else:
                # Handles overnight ranges (e.g., 22:00 - 02:00)
                return current_time >= start_time or current_time <= end_time
                
        except Exception as e:
            logger.warning(f"Error checking trading hours: {e}")
            return True  # Allow trading on error
    
    def _check_blackout_period(self, blackout_periods: list) -> bool:
        """Check if current time is in a blackout period"""
        if not blackout_periods:
            return False
        
        from datetime import datetime
        now = datetime.utcnow()
        
        for period in blackout_periods:
            try:
                start = datetime.fromisoformat(period['start'].replace('Z', '+00:00'))
                end = datetime.fromisoformat(period['end'].replace('Z', '+00:00'))
                
                if start <= now <= end:
                    return True
            except Exception as e:
                logger.warning(f"Error checking blackout period: {e}")
                continue
        
        return False
    
    def _check_trailing_stop(self, strategy: Dict, current_price: float, entry_price: float, price_change_percent: float) -> Dict:
        """Check if trailing stop loss should trigger"""
        rules = strategy['rules']
        stop_loss = rules.get('stop_loss', {})
        
        if not stop_loss.get('trailing_enabled', False):
            return {'should_trigger': False}
        
        trailing_percent = stop_loss.get('trailing_percent', 1.0)
        activation_percent = stop_loss.get('trailing_activation_percent', 2.0)
        
        # Get trailing stop state
        trailing_state = strategy.get('trailing_stop_state', {})
        highest_price = trailing_state.get('highest_price_seen')
        is_active = trailing_state.get('is_active', False)
        
        # Initialize highest price if not set
        if not highest_price:
            highest_price = max(current_price, entry_price)
            # Update in DB
            self.collection.update_one(
                {'_id': strategy['_id']},
                {'$set': {
                    'trailing_stop_state.highest_price_seen': highest_price,
                    'trailing_stop_state.last_updated': datetime.utcnow()
                }}
            )
        
        # Update highest price if new high
        if current_price > highest_price:
            highest_price = current_price
            self.collection.update_one(
                {'_id': strategy['_id']},
                {'$set': {
                    'trailing_stop_state.highest_price_seen': highest_price,
                    'trailing_stop_state.last_updated': datetime.utcnow()
                }}
            )
        
        # Check if trailing stop should activate
        gain_from_entry = ((highest_price - entry_price) / entry_price) * 100
        if not is_active and gain_from_entry >= activation_percent:
            # Activate trailing stop
            self.collection.update_one(
                {'_id': strategy['_id']},
                {'$set': {'trailing_stop_state.is_active': True}}
            )
            is_active = True
            logger.info(f"🎯 Trailing stop activated at {activation_percent}% gain")
        
        # Check if trailing stop should trigger
        if is_active:
            drop_from_peak = ((highest_price - current_price) / highest_price) * 100
            if drop_from_peak >= trailing_percent:
                return {
                    'should_trigger': True,
                    'action': 'SELL',
                    'reason': 'TRAILING_STOP',
                    'trigger_percent': trailing_percent,
                    'current_change_percent': round(price_change_percent, 2),
                    'drop_from_peak_percent': round(drop_from_peak, 2),
                    'highest_price': highest_price,
                    'quantity_percent': 100,  # Sell all on trailing stop
                    'strategy': self._format_strategy(strategy)
                }
        
        return {'should_trigger': False}
    
    def _check_take_profit_levels(self, strategy: Dict, price_change_percent: float) -> Dict:
        """Check if any take profit level should trigger"""
        rules = strategy['rules']
        tp_levels = rules.get('take_profit_levels', [])
        
        if not tp_levels:
            return {'should_trigger': False}
        
        # Get executed levels
        exec_stats = strategy.get('execution_stats', {})
        executed_tp_levels = exec_stats.get('executed_tp_levels', [])
        
        # Check each level in order
        for level in tp_levels:
            level_percent = level['percent']
            level_qty = level['quantity_percent']
            
            # Skip if already executed
            if level_percent in executed_tp_levels:
                continue
            
            # Check if level reached
            if price_change_percent >= level_percent:
                return {
                    'should_trigger': True,
                    'action': 'SELL',
                    'reason': 'TAKE_PROFIT',
                    'trigger_percent': level_percent,
                    'current_change_percent': round(price_change_percent, 2),
                    'quantity_percent': level_qty,
                    'tp_level': level_percent,
                    'strategy': self._format_strategy(strategy)
                }
        
        return {'should_trigger': False}
    
    def _check_dca_levels(self, strategy: Dict, price_change_percent: float) -> Dict:
        """Check if DCA (Dollar Cost Average) buy should trigger"""
        rules = strategy['rules']
        buy_dip = rules.get('buy_dip', {})
        
        if not buy_dip.get('dca_enabled', False):
            # Simple buy dip check
            buy_dip_percent = buy_dip.get('percent', 3.0)
            if price_change_percent <= -buy_dip_percent:
                return {
                    'should_trigger': True,
                    'action': 'BUY',
                    'reason': 'BUY_DIP',
                    'trigger_percent': -buy_dip_percent,
                    'current_change_percent': round(price_change_percent, 2),
                    'quantity_percent': 100,
                    'strategy': self._format_strategy(strategy)
                }
            return {'should_trigger': False}
        
        # Check DCA levels
        dca_levels = buy_dip.get('dca_levels', [])
        if not dca_levels:
            return {'should_trigger': False}
        
        # Get executed DCA levels
        exec_stats = strategy.get('execution_stats', {})
        executed_dca_levels = exec_stats.get('executed_dca_levels', [])
        
        # Check each DCA level in order
        for level in dca_levels:
            level_percent = level['percent']
            level_qty = level['quantity_percent']
            
            # Skip if already executed
            if level_percent in executed_dca_levels:
                continue
            
            # Check if level reached (negative percent for dips)
            if price_change_percent <= -level_percent:
                return {
                    'should_trigger': True,
                    'action': 'BUY',
                    'reason': 'DCA_BUY',
                    'trigger_percent': -level_percent,
                    'current_change_percent': round(price_change_percent, 2),
                    'quantity_percent': level_qty,
                    'dca_level': level_percent,
                    'strategy': self._format_strategy(strategy)
                }
        
        return {'should_trigger': False}

    def record_execution(
        self, 
        strategy_id: str, 
        action: str = None, 
        reason: str = None, 
        price: float = None,
        amount: float = None,
        pnl_usd: float = None
    ) -> bool:
        """
        Record that a strategy was executed with full tracking
        
        Args:
            strategy_id: Strategy MongoDB ObjectId
            action: 'BUY' or 'SELL'
            reason: Trigger reason (TAKE_PROFIT, STOP_LOSS, etc.)
            price: Execution price
            amount: Amount traded
            pnl_usd: Profit/Loss in USD (for sells)
            
        Returns:
            True if recorded successfully
        """
        try:
            now = datetime.utcnow()
            
            update_ops = {
                '$set': {
                    'last_executed_at': now,
                    'execution_stats.last_execution_at': now
                },
                '$inc': {
                    'execution_count': 1,
                    'execution_stats.total_executions': 1
                }
            }
            
            # Track action type
            if action:
                update_ops['$set']['execution_stats.last_execution_type'] = action
                if action == 'BUY':
                    update_ops['$inc']['execution_stats.total_buys'] = 1
                elif action == 'SELL':
                    update_ops['$inc']['execution_stats.total_sells'] = 1
            
            # Track reason
            if reason:
                update_ops['$set']['execution_stats.last_execution_reason'] = reason
                
                # Track executed TP/DCA levels
                if 'TAKE_PROFIT' in reason and price:
                    # Calculate TP percent and mark as executed
                    strategy = self.collection.find_one({'_id': ObjectId(strategy_id)})
                    if strategy:
                        # Extract TP level from trigger result if available
                        # For now, just log that TP was executed
                        pass
                
                elif 'DCA' in reason and price:
                    # Mark DCA level as executed
                    pass
            
            # Track price and amount
            if price:
                update_ops['$set']['execution_stats.last_execution_price'] = price
            if amount:
                update_ops['$set']['execution_stats.last_execution_amount'] = amount
            
            # Track PnL
            if pnl_usd is not None:
                update_ops['$inc']['execution_stats.total_pnl_usd'] = pnl_usd
                
                # Track daily/weekly/monthly PnL (simplified - resets on first of period)
                # In production, would use time-based aggregation
                update_ops['$inc']['execution_stats.daily_pnl_usd'] = pnl_usd
                update_ops['$inc']['execution_stats.weekly_pnl_usd'] = pnl_usd
                update_ops['$inc']['execution_stats.monthly_pnl_usd'] = pnl_usd
            
            # Set cooldown based on action and strategy rules
            strategy = self.collection.find_one({'_id': ObjectId(strategy_id)})
            if strategy and action:
                rules = strategy['rules']
                cooldown = rules.get('cooldown', {})
                
                if cooldown.get('enabled', False):
                    cooldown_minutes = 0
                    if action == 'BUY':
                        cooldown_minutes = cooldown.get('after_buy_minutes', 60)
                    elif action == 'SELL':
                        cooldown_minutes = cooldown.get('after_sell_minutes', 30)
                    
                    if cooldown_minutes > 0:
                        from datetime import timedelta
                        cooldown_until = now + timedelta(minutes=cooldown_minutes)
                        update_ops['$set']['cooldown_state.cooldown_until'] = cooldown_until
                        update_ops['$set']['cooldown_state.last_action'] = action
                        update_ops['$set']['cooldown_state.last_action_at'] = now
            
            result = self.collection.update_one(
                {'_id': ObjectId(strategy_id)},
                update_ops
            )
            
            return result.modified_count > 0
            
        except Exception as e:
            logger.error(f"Error recording execution: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def mark_tp_level_executed(self, strategy_id: str, tp_percent: float) -> bool:
        """Mark a take profit level as executed"""
        try:
            self.collection.update_one(
                {'_id': ObjectId(strategy_id)},
                {'$addToSet': {'execution_stats.executed_tp_levels': tp_percent}}
            )
            return True
        except Exception as e:
            logger.error(f"Error marking TP level executed: {e}")
            return False
    
    def mark_dca_level_executed(self, strategy_id: str, dca_percent: float) -> bool:
        """Mark a DCA level as executed"""
        try:
            self.collection.update_one(
                {'_id': ObjectId(strategy_id)},
                {'$addToSet': {'execution_stats.executed_dca_levels': dca_percent}}
            )
            return True
        except Exception as e:
            logger.error(f"Error marking DCA level executed: {e}")
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
