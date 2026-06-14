"""Модели объявлений, категорий, избранного, чатов и журнала модерации."""
from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()


class Category(models.Model):
    """Справочник категорий для классификации объявлений."""
    
    name = models.CharField(max_length=100, verbose_name='Название')
    description = models.TextField(blank=True, verbose_name='Описание')
    icon = models.CharField(max_length=50, blank=True, verbose_name='Иконка')
    is_active = models.BooleanField(default=True, verbose_name='Активна')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Категория'
        verbose_name_plural = 'Категории'
        ordering = ['name']

    def __str__(self):
        """Название категории для админки и строкового представления."""
        return self.name


class Ad(models.Model):
    """Объявление о недвижимости с ценой, статусом модерации и контактами."""
    
    STATUS_CHOICES = [
        ('pending', 'На модерации'),
        ('approved', 'Одобрено'),
        ('rejected', 'Отклонено'),
    ]

    title = models.CharField(max_length=200, verbose_name='Заголовок')
    description = models.TextField(verbose_name='Описание')
    price = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        verbose_name='Цена'
    )
    category = models.ForeignKey(
        Category, 
        on_delete=models.CASCADE, 
        related_name='ads',
        verbose_name='Категория'
    )
    author = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='ads',
        verbose_name='Автор'
    )
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='pending',
        verbose_name='Статус'
    )
    location = models.CharField(
        max_length=200, 
        blank=True,
        verbose_name='Местоположение'
    )
    contact_phone = models.CharField(
        max_length=20, 
        blank=True,
        verbose_name='Контактный телефон'
    )
    contact_email = models.EmailField(
        blank=True,
        verbose_name='Контактный email'
    )
    is_featured = models.BooleanField(
        default=False,
        verbose_name='Рекомендуемое'
    )
    views_count = models.PositiveIntegerField(
        default=0,
        verbose_name='Количество просмотров'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    published_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'Объявление'
        verbose_name_plural = 'Объявления'
        ordering = ['-created_at']

    def __str__(self):
        """Заголовок объявления."""
        return self.title

    def save(self, *args, **kwargs):
        """При первом переходе в статус approved выставляет published_at."""
        if self.status == 'approved' and not self.published_at:
            self.published_at = timezone.now()
        super().save(*args, **kwargs)


class AdModerationHistory(models.Model):
    """Журнал решений модератора (объявление или отзыв; снимок данных ИИ на момент решения)."""

    SUBJECT_TYPE_CHOICES = [
        ('ad', 'Объявление'),
        ('review', 'Отзыв'),
    ]
    DECISION_CHOICES = [
        ('approved', 'Одобрено'),
        ('rejected', 'Отклонено'),
    ]

    subject_type = models.CharField(
        max_length=20,
        choices=SUBJECT_TYPE_CHOICES,
        default='ad',
        verbose_name='Тип сущности',
    )
    ad = models.ForeignKey(
        Ad,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='moderation_history',
        verbose_name='Объявление',
    )
    review = models.ForeignKey(
        'reviews.Review',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='moderation_history_entries',
        verbose_name='Отзыв',
    )
    moderator = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='ad_moderation_decisions',
        verbose_name='Модератор',
    )
    decision = models.CharField(
        max_length=20,
        choices=DECISION_CHOICES,
        verbose_name='Решение',
    )
    reason = models.TextField(blank=True, verbose_name='Причина отклонения')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Время решения')

    ai_status = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        verbose_name='Статус проверки ИИ',
    )
    ai_normalized_prediction = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        verbose_name='Нормализованное решение ИИ',
    )
    ai_confidence = models.FloatField(
        null=True,
        blank=True,
        verbose_name='Уверенность ИИ',
    )
    ai_verdict_sfw = models.BooleanField(
        null=True,
        blank=True,
        verbose_name='SFW вердикт ИИ',
    )
    ai_message = models.TextField(blank=True, verbose_name='Сообщение ИИ')
    ai_error = models.TextField(blank=True, verbose_name='Ошибка ИИ')
    ai_checked_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Время проверки ИИ',
    )

    class Meta:
        verbose_name = 'Запись журнала модерации'
        verbose_name_plural = 'Журнал модерации'
        ordering = ['-created_at']
        constraints = [
            models.CheckConstraint(
                check=(
                    models.Q(ad__isnull=False, review__isnull=True)
                    | models.Q(ad__isnull=True, review__isnull=False)
                ),
                name='ads_admoderationhistory_exactly_one_subject',
            ),
        ]

    def __str__(self):
        """Краткая строка: тип сущности, id, решение и время записи."""
        sid = self.ad_id if self.subject_type == 'ad' else self.review_id
        return f"{self.subject_type}:{sid} {self.decision} @ {self.created_at}"


class AdImage(models.Model):
    """Файл изображения, привязанный к объявлению (основное или дополнительное)."""
    
    ad = models.ForeignKey(
        Ad, 
        on_delete=models.CASCADE, 
        related_name='images'
    )
    image = models.ImageField(
        upload_to='ads_images/',
        verbose_name='Изображение'
    )
    is_primary = models.BooleanField(
        default=False,
        verbose_name='Основное изображение'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Изображение объявления'
        verbose_name_plural = 'Изображения объявлений'

    def __str__(self):
        """Подпись для админки: объявление-владелец."""
        return f"Изображение для {self.ad.title}"


class Favorite(models.Model):
    """Связь пользователь–объявление для списка избранного."""
    
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='favorites'
    )
    ad = models.ForeignKey(
        Ad, 
        on_delete=models.CASCADE, 
        related_name='favorites'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Избранное'
        verbose_name_plural = 'Избранные'
        unique_together = ['user', 'ad']
        ordering = ['-created_at']

    def __str__(self):
        """Пользователь и заголовок объявления в избранном."""
        return f"{self.user.username} - {self.ad.title}"


class Chat(models.Model):
    """Диалог по объявлению между арендатором и арендодателем (уникальная тройка ad/tenant/landlord)."""
    
    ad = models.ForeignKey(
        Ad,
        on_delete=models.CASCADE,
        related_name='chats',
        verbose_name='Объявление'
    )
    tenant = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='tenant_chats',
        verbose_name='Арендатор'
    )
    landlord = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='landlord_chats',
        verbose_name='Арендодатель'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Чат'
        verbose_name_plural = 'Чаты'
        unique_together = ['ad', 'tenant', 'landlord']
        ordering = ['-updated_at']

    def __str__(self):
        """Идентификация чата по заголовку объявления."""
        return f"Чат по объявлению {self.ad.title}"


class Message(models.Model):
    """Текстовое сообщение внутри чата с флагом прочтения."""
    
    chat = models.ForeignKey(
        Chat,
        on_delete=models.CASCADE,
        related_name='messages',
        verbose_name='Чат'
    )
    sender = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='sent_messages',
        verbose_name='Отправитель'
    )
    text = models.TextField(verbose_name='Текст сообщения')
    is_read = models.BooleanField(default=False, verbose_name='Прочитано')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Сообщение'
        verbose_name_plural = 'Сообщения'
        ordering = ['created_at']

    def __str__(self):
        """Отправитель сообщения для отладки и админки."""
        return f"Сообщение от {self.sender.username}"