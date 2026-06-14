"""Общие фабрики данных для API-тестов backend."""
import uuid

from ads.models import Ad, Category
from users.models import User


def _suffix() -> str:
    return str(uuid.uuid4())[:8]


def create_user(role='tenant', **kwargs) -> User:
    """Создаёт пользователя с уникальным email/username."""
    su = _suffix()
    defaults = {
        'username': kwargs.pop('username', f'user_{su}'),
        'email': kwargs.pop('email', f'user_{su}@example.com'),
        'password': kwargs.pop('password', 'password123'),
        'role': role,
    }
    defaults.update(kwargs)
    password = defaults.pop('password')
    return User.objects.create_user(password=password, **defaults)


def create_landlord(**kwargs) -> User:
    return create_user(role='landlord', **kwargs)


def create_tenant(**kwargs) -> User:
    return create_user(role='tenant', **kwargs)


def create_admin(**kwargs) -> User:
    return create_user(role='admin', **kwargs)


def create_category(name=None, is_active=True, **kwargs) -> Category:
    su = _suffix()
    return Category.objects.create(
        name=name or f'Категория {su}',
        is_active=is_active,
        **kwargs,
    )


def create_ad(author, category=None, status='pending', **kwargs) -> Ad:
    if category is None:
        category = create_category()
    defaults = {
        'title': kwargs.pop('title', 'Тестовое объявление'),
        'description': kwargs.pop('description', 'Описание'),
        'price': kwargs.pop('price', '5000.00'),
        'location': kwargs.pop('location', 'Москва'),
        'category': category,
        'author': author,
        'status': status,
    }
    defaults.update(kwargs)
    return Ad.objects.create(**defaults)


def auth(client, user) -> None:
    """Аутентифицирует APIClient от имени пользователя."""
    client.force_authenticate(user=user)
