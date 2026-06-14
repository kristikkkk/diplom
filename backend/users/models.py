"""Модель пользователя с ролью и контактами для доски объявлений."""
from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Пользователь с входом по email, ролью (арендатор/арендодатель/админ) и профилем."""
    
    ROLE_CHOICES = [
        ('tenant', 'Арендатор'),
        ('landlord', 'Арендодатель'),
        ('admin', 'Администратор'),
    ]
    
    email = models.EmailField(unique=True)
    role = models.CharField(
        max_length=20, 
        choices=ROLE_CHOICES, 
        default='tenant',
        verbose_name='Роль'
    )
    avatar = models.ImageField(
        upload_to='avatars/', 
        null=True, 
        blank=True,
        verbose_name='Аватар'
    )
    phone_number = models.CharField(
        max_length=20, 
        null=True, 
        blank=True,
        verbose_name='Номер телефона'
    )
    is_verified = models.BooleanField(
        default=False,
        verbose_name='Верифицирован'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'

    def __str__(self):
        """Строковое представление: имя пользователя и локализованная роль."""
        return f"{self.username} ({self.get_role_display()})"