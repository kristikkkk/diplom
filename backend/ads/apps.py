"""Конфигурация приложения объявлений, чатов и избранного."""
from django.apps import AppConfig


class AdsConfig(AppConfig):
    """Регистрирует приложение доменной логики объявлений."""
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'ads'
