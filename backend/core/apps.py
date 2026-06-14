"""Конфигурация приложения core (общие модели и админка)."""
from django.apps import AppConfig


class CoreConfig(AppConfig):
    """Регистрирует приложение глобальных настроек сайта."""
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'
