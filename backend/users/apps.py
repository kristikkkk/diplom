"""Конфигурация приложения пользователей и кастомной модели User."""
from django.apps import AppConfig


class UsersConfig(AppConfig):
    """Регистрирует приложение аутентификации и профилей."""
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'users'
