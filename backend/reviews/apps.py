"""Конфигурация приложения отзывов."""
from django.apps import AppConfig


class ReviewsConfig(AppConfig):
    """Регистрирует приложение reviews."""
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'reviews'
