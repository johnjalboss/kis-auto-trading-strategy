"""
Notification System Redirection Wrapper
========================================
Redirects all legacy imports from notification.py to notifier.py to unify alerting channels
and take advantage of advanced notifier features (Korean translations, dual platforms, etc.)
"""

from notifier import get_notifier, TelegramNotifier

class NotificationManager(TelegramNotifier):
    """Subclass of TelegramNotifier to act as drop-in replacement for legacy NotificationManager"""
    pass
