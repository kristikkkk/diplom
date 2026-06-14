"""Конфигурация приложения ML: модели очередей и подключение сигналов."""
from django.apps import AppConfig


class MlServiceConfig(AppConfig):
    """Регистрирует ml_service и импортирует signals при старте Django."""
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'ml_service'
    
    def ready(self):
        """Подгружает модуль сигналов для регистрации receivers."""
        import ml_service.signals