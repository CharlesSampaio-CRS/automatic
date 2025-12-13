"""
Notification Service - Alert users about strategy executions and order events
Supports database notifications, webhooks, and email (extensible)
"""

from typing import Dict, Optional
from datetime import datetime
from src.utils.logger import get_logger


# Initialize logger
logger = get_logger(__name__)


class NotificationService:
    """Service to send notifications about trading events"""
    
    def __init__(self, db, enable_webhooks: bool = False, enable_email: bool = False):
        """
        Initialize notification service
        
        Args:
            db: MongoDB database connection
            enable_webhooks: Enable webhook notifications
            enable_email: Enable email notifications
        """
        self.db = db
        self.enable_webhooks = enable_webhooks
        self.enable_email = enable_email
        
        # Create notifications collection indexes
        self._ensure_indexes()
    
    def _ensure_indexes(self):
        """Create MongoDB indexes for notifications collection"""
        try:
            # Index for querying user notifications
            self.db.notifications.create_index([
                ('user_id', 1),
                ('is_read', 1),
                ('created_at', -1)
            ])
            
            # Index for notification type filtering
            self.db.notifications.create_index([
                ('user_id', 1),
                ('type', 1),
                ('created_at', -1)
            ])
            
        except Exception as e:
            logger.error(f"Error creating notification indexes: {e}")
    
    def _create_notification(
        self,
        user_id: str,
        notification_type: str,
        title: str,
        message: str,
        data: Optional[Dict] = None
    ) -> str:
        """
        Create notification in database
        
        Args:
            user_id: User ID
            notification_type: Type of notification
            title: Notification title
            message: Notification message
            data: Additional data (optional)
            
        Returns:
            Notification ID
        """
        try:
            notification = {
                'user_id': user_id,
                'type': notification_type,
                'title': title,
                'message': message,
                'data': data or {},
                'is_read': False,
                'created_at': datetime.utcnow()
            }
            
            result = self.db.notifications.insert_one(notification)
            
            logger.info(f"📬 Notification created: {notification_type} for user {user_id}")
            
            return str(result.inserted_id)
            
        except Exception as e:
            logger.error(f"Error creating notification: {e}")
            return None
    
    def notify_strategy_executed(
        self,
        user_id: str,
        strategy: Dict,
        order: Dict,
        reason: str
    ):
        """
        Notify user that a strategy was executed
        
        Args:
            user_id: User ID
            strategy: Strategy document
            order: Order result
            reason: Trigger reason (TAKE_PROFIT, STOP_LOSS, BUY_DIP)
        """
        try:
            # Format reason
            reason_text = {
                'TAKE_PROFIT': 'Take Profit atingido! 🎯',
                'STOP_LOSS': 'Stop Loss acionado ⚠️',
                'BUY_DIP': 'Oportunidade de compra detectada 📉'
            }.get(reason, reason)
            
            # Format action
            action = order['side'].upper()
            action_emoji = '🔴' if action == 'SELL' else '🟢'
            
            # Create title
            title = f"{action_emoji} Estratégia Executada - {strategy['token']}"
            
            # Create message
            message = (
                f"{reason_text}\n\n"
                f"Token: {strategy['token']}\n"
                f"Exchange: {strategy.get('exchange_name', 'N/A')}\n"
                f"Ação: {action}\n"
                f"Quantidade: {order.get('filled', order['amount'])}\n"
                f"Preço: ${order.get('average', order.get('price', 'N/A'))}\n"
                f"Ordem ID: {order['id']}\n"
                f"Status: {order['status']}"
            )
            
            # Additional data
            data = {
                'strategy_id': str(strategy['_id']),
                'order_id': order['id'],
                'token': strategy['token'],
                'exchange_id': str(strategy['exchange_id']),
                'action': action,
                'reason': reason,
                'amount': order.get('filled', order['amount']),
                'price': order.get('average', order.get('price')),
                'status': order['status']
            }
            
            # Create database notification
            self._create_notification(
                user_id=user_id,
                notification_type='strategy_executed',
                title=title,
                message=message,
                data=data
            )
            
            # TODO: Send webhook if enabled
            if self.enable_webhooks:
                self._send_webhook(user_id, 'strategy_executed', data)
            
            # TODO: Send email if enabled
            if self.enable_email:
                self._send_email(user_id, title, message)
            
        except Exception as e:
            logger.error(f"Error sending strategy execution notification: {e}")
    
    def notify_order_failed(
        self,
        user_id: str,
        strategy: Dict,
        error: str
    ):
        """
        Notify user that an order execution failed
        
        Args:
            user_id: User ID
            strategy: Strategy document
            error: Error message
        """
        try:
            title = f"❌ Erro na Execução - {strategy['token']}"
            
            message = (
                f"A estratégia não pôde ser executada.\n\n"
                f"Token: {strategy['token']}\n"
                f"Exchange: {strategy.get('exchange_name', 'N/A')}\n"
                f"Erro: {error}\n\n"
                f"Por favor, verifique sua exchange e tente novamente."
            )
            
            data = {
                'strategy_id': str(strategy['_id']),
                'token': strategy['token'],
                'exchange_id': str(strategy['exchange_id']),
                'error': error
            }
            
            # Create database notification
            self._create_notification(
                user_id=user_id,
                notification_type='order_failed',
                title=title,
                message=message,
                data=data
            )
            
        except Exception as e:
            logger.error(f"Error sending order failure notification: {e}")
    
    def notify_strategy_created(
        self,
        user_id: str,
        strategy: Dict
    ):
        """
        Notify user that a new strategy was created
        
        Args:
            user_id: User ID
            strategy: Strategy document
        """
        try:
            title = f"✅ Nova Estratégia Criada - {strategy['token']}"
            
            rules = strategy['rules']
            message = (
                f"Estratégia configurada com sucesso!\n\n"
                f"Token: {strategy['token']}\n"
                f"Exchange: {strategy.get('exchange_name', 'N/A')}\n"
                f"Take Profit: {rules.get('take_profit_percent', 0)}%\n"
                f"Stop Loss: {rules.get('stop_loss_percent', 0)}%\n"
                f"Buy Dip: {rules.get('buy_dip_percent', 0)}%"
            )
            
            data = {
                'strategy_id': str(strategy['_id']),
                'token': strategy['token'],
                'exchange_id': str(strategy['exchange_id']),
                'rules': rules
            }
            
            # Create database notification
            self._create_notification(
                user_id=user_id,
                notification_type='strategy_created',
                title=title,
                message=message,
                data=data
            )
            
        except Exception as e:
            logger.error(f"Error sending strategy creation notification: {e}")
    
    def get_user_notifications(
        self,
        user_id: str,
        unread_only: bool = False,
        notification_type: Optional[str] = None,
        limit: int = 50
    ) -> list:
        """
        Get user notifications
        
        Args:
            user_id: User ID
            unread_only: Only return unread notifications
            notification_type: Filter by notification type
            limit: Maximum number of notifications to return
            
        Returns:
            List of notifications
        """
        try:
            query = {'user_id': user_id}
            
            if unread_only:
                query['is_read'] = False
            
            if notification_type:
                query['type'] = notification_type
            
            notifications = list(
                self.db.notifications
                .find(query)
                .sort('created_at', -1)
                .limit(limit)
            )
            
            # Convert ObjectId to string
            for notif in notifications:
                notif['_id'] = str(notif['_id'])
            
            return notifications
            
        except Exception as e:
            logger.error(f"Error fetching notifications: {e}")
            return []
    
    def mark_as_read(self, notification_id: str) -> bool:
        """
        Mark notification as read
        
        Args:
            notification_id: Notification ID
            
        Returns:
            True if successful
        """
        try:
            from bson import ObjectId
            
            result = self.db.notifications.update_one(
                {'_id': ObjectId(notification_id)},
                {'$set': {'is_read': True, 'read_at': datetime.utcnow()}}
            )
            
            return result.modified_count > 0
            
        except Exception as e:
            logger.error(f"Error marking notification as read: {e}")
            return False
    
    def mark_all_as_read(self, user_id: str) -> int:
        """
        Mark all user notifications as read
        
        Args:
            user_id: User ID
            
        Returns:
            Number of notifications marked as read
        """
        try:
            result = self.db.notifications.update_many(
                {'user_id': user_id, 'is_read': False},
                {'$set': {'is_read': True, 'read_at': datetime.utcnow()}}
            )
            
            return result.modified_count
            
        except Exception as e:
            logger.error(f"Error marking all notifications as read: {e}")
            return 0
    
    def delete_notification(self, notification_id: str) -> bool:
        """
        Delete notification
        
        Args:
            notification_id: Notification ID
            
        Returns:
            True if successful
        """
        try:
            from bson import ObjectId
            
            result = self.db.notifications.delete_one(
                {'_id': ObjectId(notification_id)}
            )
            
            return result.deleted_count > 0
            
        except Exception as e:
            logger.error(f"Error deleting notification: {e}")
            return False
    
    def _send_webhook(self, user_id: str, event_type: str, data: Dict):
        """
        Send webhook notification (placeholder for future implementation)
        
        Args:
            user_id: User ID
            event_type: Event type
            data: Event data
        """
        # TODO: Implement webhook sending
        logger.info(f"📡 Webhook would be sent: {event_type} for user {user_id}")
    
    def _send_email(self, user_id: str, subject: str, body: str):
        """
        Send email notification (placeholder for future implementation)
        
        Args:
            user_id: User ID
            subject: Email subject
            body: Email body
        """
        # TODO: Implement email sending
        logger.info(f"📧 Email would be sent: {subject} to user {user_id}")


def get_notification_service(
    db,
    enable_webhooks: bool = False,
    enable_email: bool = False
):
    """Factory function to create NotificationService instance"""
    return NotificationService(
        db=db,
        enable_webhooks=enable_webhooks,
        enable_email=enable_email
    )
