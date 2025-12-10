"""
Position Service - Track user token positions and average entry prices
Manages buy/sell history and calculates average cost basis
"""

from datetime import datetime
from typing import Dict, List, Optional
from bson import ObjectId
from src.utils.logger import get_logger
from src.utils.formatting import format_amount, format_price, format_usd


# Initialize logger
logger = get_logger(__name__)


class PositionService:
    """Service to manage user token positions"""
    
    def __init__(self, db):
        """Initialize with database connection"""
        self.db = db
        self.collection = db.user_positions
        
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
            
            # Index for querying user positions
            self.collection.create_index([
                ('user_id', 1),
                ('is_active', 1)
            ])
            
        except Exception as e:
            logger.warning(f"Could not create indexes: {e}")
    
    def record_buy(
        self,
        user_id: str,
        exchange_id: str,
        token: str,
        amount: float,
        price: float,
        total_cost: float,
        order_id: Optional[str] = None
    ) -> Dict:
        """
        Record a buy transaction and update position
        
        Args:
            user_id: User ID
            exchange_id: Exchange MongoDB ObjectId
            token: Token symbol
            amount: Amount bought
            price: Price per token
            total_cost: Total cost (amount * price + fees)
            order_id: Optional exchange order ID
            
        Returns:
            Dict with updated position
        """
        try:
            # Find or create position
            position = self.collection.find_one({
                'user_id': user_id,
                'exchange_id': exchange_id,
                'token': token.upper()
            })
            
            if position:
                # Update existing position
                old_amount = position['amount']
                old_total_cost = position['total_invested']
                
                new_amount = old_amount + amount
                new_total_cost = old_total_cost + total_cost
                new_avg_price = new_total_cost / new_amount if new_amount > 0 else 0
                
                # Add to purchase history
                purchase = {
                    'date': datetime.utcnow(),
                    'amount': amount,
                    'price': price,
                    'total_cost': total_cost,
                    'order_id': order_id
                }
                
                self.collection.update_one(
                    {'_id': position['_id']},
                    {
                        '$set': {
                            'amount': new_amount,
                            'entry_price': new_avg_price,
                            'total_invested': new_total_cost,
                            'updated_at': datetime.utcnow()
                        },
                        '$push': {
                            'purchases': purchase
                        }
                    }
                )
                
                logger.info(f"Position updated: {token} - New avg price: ${new_avg_price:.2f}")
            else:
                # Create new position
                exchange = self.db.exchanges.find_one({'_id': ObjectId(exchange_id)})
                
                new_position = {
                    'user_id': user_id,
                    'exchange_id': exchange_id,
                    'exchange_name': exchange['nome'] if exchange else 'Unknown',
                    'token': token.upper(),
                    'amount': amount,
                    'entry_price': price,
                    'total_invested': total_cost,
                    'is_active': True,
                    'created_at': datetime.utcnow(),
                    'updated_at': datetime.utcnow(),
                    'purchases': [{
                        'date': datetime.utcnow(),
                        'amount': amount,
                        'price': price,
                        'total_cost': total_cost,
                        'order_id': order_id
                    }],
                    'sales': []
                }
                
                result = self.collection.insert_one(new_position)
                position = new_position
                position['_id'] = result.inserted_id
                
                logger.info(f"New position created: {token} - Entry price: ${price:.2f}")
            
            return {
                'success': True,
                'position': self._format_position(self.collection.find_one({'_id': position['_id']}))
            }
            
        except Exception as e:
            logger.error(f"Error recording buy: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def record_sell(
        self,
        user_id: str,
        exchange_id: str,
        token: str,
        amount: float,
        price: float,
        total_received: float,
        order_id: Optional[str] = None
    ) -> Dict:
        """
        Record a sell transaction and update position
        
        Args:
            user_id: User ID
            exchange_id: Exchange MongoDB ObjectId
            token: Token symbol
            amount: Amount sold
            price: Price per token
            total_received: Total received (amount * price - fees)
            order_id: Optional exchange order ID
            
        Returns:
            Dict with updated position and P&L
        """
        try:
            # Find position
            position = self.collection.find_one({
                'user_id': user_id,
                'exchange_id': exchange_id,
                'token': token.upper()
            })
            
            if not position:
                return {
                    'success': False,
                    'error': f'No position found for {token}'
                }
            
            if position['amount'] < amount:
                return {
                    'success': False,
                    'error': f'Insufficient balance. Has {position["amount"]}, trying to sell {amount}'
                }
            
            # Calculate P&L
            entry_price = position['entry_price']
            cost_basis = amount * entry_price
            profit_loss = total_received - cost_basis
            profit_loss_percent = (profit_loss / cost_basis) * 100 if cost_basis > 0 else 0
            
            # Update position
            new_amount = position['amount'] - amount
            
            # Proportionally reduce total_invested
            if position['amount'] > 0:
                remaining_ratio = new_amount / position['amount']
                new_total_invested = position['total_invested'] * remaining_ratio
            else:
                new_total_invested = 0
            
            # Add to sales history
            sale = {
                'date': datetime.utcnow(),
                'amount': amount,
                'price': price,
                'total_received': total_received,
                'entry_price': entry_price,
                'profit_loss': profit_loss,
                'profit_loss_percent': profit_loss_percent,
                'order_id': order_id
            }
            
            update_data = {
                '$set': {
                    'amount': new_amount,
                    'total_invested': new_total_invested,
                    'updated_at': datetime.utcnow()
                },
                '$push': {
                    'sales': sale
                }
            }
            
            # If sold everything, mark as inactive
            if new_amount <= 0:
                update_data['$set']['is_active'] = False
            
            self.collection.update_one(
                {'_id': position['_id']},
                update_data
            )
            
            logger.info(f"Position updated: Sold {amount} {token} - P&L: ${profit_loss:.2f} ({profit_loss_percent:.2f}%)")
            
            return {
                'success': True,
                'position': self._format_position(self.collection.find_one({'_id': position['_id']})),
                'profit_loss': {
                    'amount': profit_loss,
                    'percent': profit_loss_percent,
                    'entry_price': entry_price,
                    'exit_price': price
                }
            }
            
        except Exception as e:
            logger.error(f"Error recording sell: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_position(
        self,
        user_id: str,
        exchange_id: str,
        token: str
    ) -> Optional[Dict]:
        """
        Get a specific position
        
        Args:
            user_id: User ID
            exchange_id: Exchange MongoDB ObjectId
            token: Token symbol
            
        Returns:
            Position dict or None
        """
        try:
            position = self.collection.find_one({
                'user_id': user_id,
                'exchange_id': exchange_id,
                'token': token.upper()
            })
            
            if position:
                return self._format_position(position)
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting position: {e}")
            return None
    
    def get_user_positions(
        self,
        user_id: str,
        exchange_id: Optional[str] = None,
        is_active: bool = True
    ) -> List[Dict]:
        """
        Get all positions for a user
        
        Args:
            user_id: User ID
            exchange_id: Filter by exchange (optional)
            is_active: Filter by active status
            
        Returns:
            List of positions
        """
        try:
            query = {
                'user_id': user_id,
                'is_active': is_active
            }
            
            if exchange_id:
                query['exchange_id'] = exchange_id
            
            positions = list(self.collection.find(query).sort('created_at', -1))
            
            return [self._format_position(p) for p in positions]
            
        except Exception as e:
            logger.error(f"Error getting user positions: {e}")
            return []
    
    def sync_from_balance(
        self,
        user_id: str,
        exchange_id: str,
        token: str,
        current_amount: float,
        current_price: float
    ) -> Dict:
        """
        Sync position from current balance (for tokens without tracked purchases)
        Creates a position with current price as entry price
        
        Args:
            user_id: User ID
            exchange_id: Exchange MongoDB ObjectId
            token: Token symbol
            current_amount: Current amount from balance
            current_price: Current market price
            
        Returns:
            Dict with synced position
        """
        try:
            position = self.collection.find_one({
                'user_id': user_id,
                'exchange_id': exchange_id,
                'token': token.upper()
            })
            
            if position:
                # Position already exists, just update amount if needed
                if abs(position['amount'] - current_amount) > 0.00000001:
                    self.collection.update_one(
                        {'_id': position['_id']},
                        {
                            '$set': {
                                'amount': current_amount,
                                'updated_at': datetime.utcnow()
                            }
                        }
                    )
                    logger.info(f"Position amount synced: {token} = {current_amount}")
            else:
                # Create new position with current price as entry
                return self.record_buy(
                    user_id=user_id,
                    exchange_id=exchange_id,
                    token=token,
                    amount=current_amount,
                    price=current_price,
                    total_cost=current_amount * current_price,
                    order_id='SYNC'
                )
            
            return {
                'success': True,
                'position': self._format_position(self.collection.find_one({
                    'user_id': user_id,
                    'exchange_id': exchange_id,
                    'token': token.upper()
                }))
            }
            
        except Exception as e:
            logger.error(f"Error syncing position: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _format_position(self, position: Dict) -> Dict:
        """Format position for API response"""
        if not position:
            return None
        
        return {
            'id': str(position['_id']),
            'user_id': position['user_id'],
            'exchange_id': position['exchange_id'],
            'exchange_name': position['exchange_name'],
            'token': position['token'],
            'amount': format_amount(position['amount']),
            'entry_price': format_price(position['entry_price']),
            'total_invested': format_usd(position['total_invested']),
            'is_active': position['is_active'],
            'created_at': position['created_at'].isoformat(),
            'updated_at': position['updated_at'].isoformat(),
            'purchases_count': len(position.get('purchases', [])),
            'sales_count': len(position.get('sales', []))
        }


def get_position_service(db):
    """Factory function to create PositionService instance"""
    return PositionService(db)
