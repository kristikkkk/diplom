"""Модель отзыва на объявление с рейтингом и статусом модерации."""
from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator

User = get_user_model()


class Review(models.Model):
    """Отзыв пользователя об объявлении; не более одного отзыва автора на объявление."""
    
    STATUS_CHOICES = [
        ('pending', 'На модерации'),
        ('approved', 'Одобрено'),
        ('rejected', 'Отклонено'),
    ]

    text = models.TextField(verbose_name='Текст отзыва')
    rating = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        verbose_name='Рейтинг'
    )
    author = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='reviews',
        verbose_name='Автор'
    )
    ad = models.ForeignKey(
        'ads.Ad', 
        on_delete=models.CASCADE, 
        related_name='reviews',
        verbose_name='Объявление'
    )
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='pending',
        verbose_name='Статус'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Отзыв'
        verbose_name_plural = 'Отзывы'
        ordering = ['-created_at']
        unique_together = ['author', 'ad']  # Один отзыв от пользователя на объявление

    def __str__(self):
        """Краткое описание связки автор–объявление."""
        return f"Отзыв от {self.author.username} на {self.ad.title}"