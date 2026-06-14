"""Данные для демо-аккаунтов и миграция с заполнением фиксированных пользователей."""
from django.contrib.auth.hashers import make_password
from django.db import migrations


SEED_USERS = [
    {
        "email": "admin@example.com",
        "username": "admin",
        "password": "admin12345",
        "role": "admin",
        "is_staff": True,
        "is_superuser": True,
    },
    {
        "email": "landlord@example.com",
        "username": "landlord",
        "password": "landlord12345",
        "role": "landlord",
        "is_staff": False,
        "is_superuser": False,
    },
    {
        "email": "tenant@example.com",
        "username": "tenant",
        "password": "tenant12345",
        "role": "tenant",
        "is_staff": False,
        "is_superuser": False,
    },
]


def seed_users(apps, schema_editor):
    """Создаёт или обновляет тестовых пользователей из SEED_USERS с заданными паролями."""
    User = apps.get_model("users", "User")

    for account in SEED_USERS:
        user, _ = User.objects.get_or_create(
            email=account["email"],
            defaults={
                "username": account["username"],
                "role": account["role"],
                "is_staff": account["is_staff"],
                "is_superuser": account["is_superuser"],
                "is_active": True,
            },
        )
        user.username = account["username"]
        user.role = account["role"]
        user.is_staff = account["is_staff"]
        user.is_superuser = account["is_superuser"]
        user.is_active = True
        user.password = make_password(account["password"])
        user.save(
            update_fields=[
                "username",
                "role",
                "is_staff",
                "is_superuser",
                "is_active",
                "password",
            ]
        )


def unseed_users(apps, schema_editor):
    """Удаляет пользователей с email из SEED_USERS при откате миграции."""
    User = apps.get_model("users", "User")
    User.objects.filter(email__in=[account["email"] for account in SEED_USERS]).delete()


class Migration(migrations.Migration):
    """Запускает Python-код для засева демо-пользователей после создания таблицы User."""

    dependencies = [
        ("users", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_users, unseed_users),
    ]
