"""
Balance History Service - Track balance changes over time
Stores snapshots in MongoDB for historical analysis
"""

from datetime import datetime
from typing import Dict
from bson import ObjectId
from src.utils.formatting import format_usd, format_brl, format_percent
from src.utils.logger import get_logger


# Initialize logger
logger = get_logger(__name__)


class BalanceHistoryService:
    """Service to store and retrieve balance history"""
    
    def __init__(self, db):
        """Initialize with database connection"""
        self.db = db
        self.collection = db.balance_history
        
        # Create indexes for efficient queries
        self._ensure_indexes()
    
    def _ensure_indexes(self):
        """Create indexes if they don't exist"""
        try:
            # Index for querying by user and timestamp
            self.collection.create_index([
                ('user_id', 1),
                ('timestamp', -1)
            ])
            
            # Index for querying specific tokens
            self.collection.create_index([
                ('user_id', 1),
                ('tokens_summary', 1)
            ])
            
            # TTL index to auto-delete old records (optional: keep 90 days)
            # Uncomment to enable auto-deletion:
            # self.collection.create_index(
            #     'timestamp',
            #     expireAfterSeconds=7776000  # 90 days
            # )
            
        except Exception as e:
            logger.warning(f"Could not create indexes: {e}")
    
    def save_snapshot(self, balance_data: Dict) -> str:
        """
        Save a simplified balance snapshot to history (ESTRUTURA OTIMIZADA)
        Mantém apenas valores totais e por exchange
        
        Args:
            balance_data: Balance data from BalanceService
            
        Returns:
            Inserted document ID
        """
        # Verifica se há dados válidos
        if not balance_data.get('user_id'):
            return None
        
        try:
            # Convert string values back to float for storage
            summary_usd = float(balance_data.get('summary', {}).get('total_usd', '0.0'))
            summary_brl = float(balance_data.get('summary', {}).get('total_brl', '0.0'))
            
            # Prepare simplified snapshot document
            snapshot = {
                'user_id': balance_data['user_id'],
                'timestamp': datetime.utcnow(),
                
                # Valores totais do summary
                'total_usd': format_usd(summary_usd),
                'total_brl': format_brl(summary_brl),
                
                # Resumo por exchange (apenas valores essenciais)
                'exchanges': [
                    {
                        'exchange_id': ex.get('exchange_id', ''),
                        'exchange_name': ex.get('name', ''),
                        'total_usd': format_usd(float(ex.get('total_usd', '0.0'))),
                        'total_brl': format_brl(float(ex.get('total_brl', '0.0'))),
                        'success': ex.get('success', False)
                    }
                    for ex in balance_data.get('exchanges', [])
                    if ex.get('success', False)  # Salva apenas exchanges com sucesso
                ]
            }
            
            result = self.collection.insert_one(snapshot)
            
            logger.info(f"Balance snapshot saved: {result.inserted_id}")
            return str(result.inserted_id)
            
        except Exception as e:
            logger.error(f"Error saving balance snapshot: {e}")
            return None
    
    def get_latest_snapshot(self, user_id: str) -> Dict:
        """
        Get the most recent balance snapshot for a user
        
        Args:
            user_id: User ID
            
        Returns:
            Latest snapshot document or None
        """
        try:
            snapshot = self.collection.find_one(
                {'user_id': user_id},
                sort=[('timestamp', -1)]
            )
            
            if snapshot:
                snapshot['_id'] = str(snapshot['_id'])
                snapshot['timestamp'] = snapshot['timestamp'].isoformat()
            
            return snapshot
            
        except Exception as e:
            logger.error(f"Error getting latest snapshot: {e}")
            return None
    
    def get_history(self, user_id: str, limit: int = 100, skip: int = 0) -> list:
        """
        Get balance history for a user
        
        Args:
            user_id: User ID
            limit: Maximum number of records to return
            skip: Number of records to skip (for pagination)
            
        Returns:
            List of balance snapshots
        """
        try:
            snapshots = list(self.collection.find(
                {'user_id': user_id},
                sort=[('timestamp', -1)],
                limit=limit,
                skip=skip
            ))
            
            # Convert ObjectId and datetime to strings
            for snapshot in snapshots:
                snapshot['_id'] = str(snapshot['_id'])
                snapshot['timestamp'] = snapshot['timestamp'].isoformat()
            
            return snapshots
            
        except Exception as e:
            logger.error(f"Error getting history: {e}")
            return []
    
    def get_token_history(self, user_id: str, token: str, limit: int = 100) -> list:
        """
        Get historical data for a specific token
        
        Args:
            user_id: User ID
            token: Token symbol (e.g., 'BTC', 'ETH')
            limit: Maximum number of records
            
        Returns:
            List of snapshots containing the token
        """
        try:
            snapshots = list(self.collection.find(
                {
                    'user_id': user_id,
                    f'tokens_summary.{token}': {'$exists': True}
                },
                {
                    '_id': 1,
                    'timestamp': 1,
                    'total_usd': 1,
                    'total_brl': 1,
                    f'tokens_summary.{token}': 1
                },
                sort=[('timestamp', -1)],
                limit=limit
            ))
            
            # Format response
            history = []
            for snapshot in snapshots:
                token_data = snapshot.get('tokens_summary', {}).get(token, {})
                history.append({
                    'timestamp': snapshot['timestamp'].isoformat(),
                    'amount': token_data.get('total', 0.0),
                    'price_usd': token_data.get('price_usd', 0.0),
                    'value_usd': token_data.get('value_usd', 0.0),
                    'value_brl': token_data.get('value_brl', 0.0)
                })
            
            return history
            
        except Exception as e:
            logger.error(f"Error getting token history: {e}")
            return []
    
    def get_portfolio_evolution(self, user_id: str, days: int = 30) -> Dict:
        """
        Get portfolio value evolution over time
        
        Args:
            user_id: User ID
            days: Number of days to look back
            
        Returns:
            Dict with time series data
        """
        try:
            from datetime import timedelta
            
            start_date = datetime.utcnow() - timedelta(days=days)
            
            snapshots = list(self.collection.find(
                {
                    'user_id': user_id,
                    'timestamp': {'$gte': start_date}
                },
                {
                    'timestamp': 1,
                    'total_usd': 1,
                    'total_brl': 1,
                    'total_unique_tokens': 1
                },
                sort=[('timestamp', 1)]
            ))
            
            time_series = {
                'timestamps': [],
                'values_usd': [],
                'values_brl': [],
                'token_counts': []
            }
            
            for snapshot in snapshots:
                time_series['timestamps'].append(snapshot['timestamp'].isoformat())
                time_series['values_usd'].append(snapshot.get('total_usd', 0.0))
                time_series['values_brl'].append(snapshot.get('total_brl', 0.0))
                time_series['token_counts'].append(snapshot.get('total_unique_tokens', 0))
            
            # Calculate summary stats
            if snapshots:
                first = snapshots[0]
                last = snapshots[-1]
                
                # Convert strings to float for calculations
                first_usd = float(first.get('total_usd', '0'))
                last_usd = float(last.get('total_usd', '0'))
                
                change_usd = last_usd - first_usd
                change_pct = (change_usd / first_usd) * 100 if first_usd > 0 else 0
                
                all_usd_values = [float(s.get('total_usd', '0')) for s in snapshots]
                
                time_series['summary'] = {
                    'period_days': days,
                    'data_points': len(snapshots),
                    'start_value_usd': format_usd(first_usd),
                    'end_value_usd': format_usd(last_usd),
                    'change_usd': format_usd(change_usd),
                    'change_percent': format_percent(change_pct),
                    'min_value_usd': format_usd(min(all_usd_values)),
                    'max_value_usd': format_usd(max(all_usd_values))
                }
            
            return time_series
            
        except Exception as e:
            logger.error(f"Error getting portfolio evolution: {e}")
            return {}


def get_balance_history_service(db):
    """Factory function to create BalanceHistoryService instance"""
    return BalanceHistoryService(db)
