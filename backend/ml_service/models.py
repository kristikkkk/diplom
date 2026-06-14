"""Модели учёта ML-моделей, логов предсказаний и очередей автоматической модерации."""
from django.db import models


class MLModel(models.Model):
    """Запись о подключаемой модели (метаданные и путь для админки/логов)."""
    
    MODEL_TYPES = [
        ('content_moderation', 'Модерация контента'),
        ('spam_detection', 'Обнаружение спама'),
        ('sentiment_analysis', 'Анализ тональности'),
    ]

    name = models.CharField(max_length=100, verbose_name='Название модели')
    model_type = models.CharField(
        max_length=50, 
        choices=MODEL_TYPES,
        verbose_name='Тип модели'
    )
    model_path = models.CharField(
        max_length=200,
        verbose_name='Путь к модели'
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name='Активна'
    )
    accuracy = models.FloatField(
        null=True, 
        blank=True,
        verbose_name='Точность'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'ML Модель'
        verbose_name_plural = 'ML Модели'

    def __str__(self):
        """Название и человекочитаемый тип модели."""
        return f"{self.name} ({self.get_model_type_display()})"


class PredictionLog(models.Model):
    """История предсказаний для аудита: тип контента, id, текст и метрики."""
    
    model = models.ForeignKey(
        MLModel, 
        on_delete=models.CASCADE,
        related_name='predictions'
    )
    content_type = models.CharField(
        max_length=50,
        verbose_name='Тип контента'
    )
    content_id = models.PositiveIntegerField(
        verbose_name='ID контента'
    )
    text = models.TextField(verbose_name='Текст')
    prediction = models.CharField(
        max_length=50,
        verbose_name='Предсказание'
    )
    confidence = models.FloatField(
        verbose_name='Уверенность'
    )
    is_correct = models.BooleanField(
        null=True,
        blank=True,
        verbose_name='Корректно'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Лог предсказания'
        verbose_name_plural = 'Логи предсказаний'
        ordering = ['-created_at']

    def __str__(self):
        """Краткая строка для списка логов в админке."""
        return f"Предсказание {self.model.name} - {self.prediction}"


class AdModerationQueue(models.Model):
    """Очередь и результат проверки объявления ML-сервисом."""

    STATUS_CHOICES = [
        ("queued", "В очереди"),
        ("processing", "Проверяется"),
        ("checked", "Проверено"),
        ("failed", "Ошибка"),
    ]

    NORMALIZED_PREDICTION_CHOICES = [
        ("approved", "Безопасно"),
        ("rejected", "Небезопасно"),
        ("pending", "Нужна ручная проверка"),
    ]

    ad = models.OneToOneField(
        "ads.Ad",
        on_delete=models.CASCADE,
        related_name="moderation_queue",
        verbose_name="Объявление",
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="queued",
        verbose_name="Статус проверки",
    )
    verdict_sfw = models.BooleanField(
        null=True,
        blank=True,
        verbose_name="SFW вердикт",
    )
    normalized_prediction = models.CharField(
        max_length=20,
        choices=NORMALIZED_PREDICTION_CHOICES,
        default="pending",
        verbose_name="Нормализованное решение",
    )
    confidence = models.FloatField(
        null=True,
        blank=True,
        verbose_name="Уверенность модели",
    )
    message = models.TextField(
        blank=True,
        verbose_name="Сообщение сервиса",
    )
    raw_response = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="Сырой ответ сервиса",
    )
    is_uncertain = models.BooleanField(
        default=False,
        verbose_name="Модель сомневается",
    )
    error = models.TextField(
        blank=True,
        verbose_name="Текст ошибки",
    )
    checked_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Время проверки",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Очередь модерации объявления"
        verbose_name_plural = "Очередь модерации объявлений"
        ordering = ["-created_at"]

    def __str__(self):
        """Ид объявления и текущий статус очереди."""
        return f"Проверка объявления #{self.ad_id}: {self.status}"


class ReviewModerationQueue(models.Model):
    """Очередь и результат проверки отзыва ML-сервисом."""

    STATUS_CHOICES = [
        ("queued", "В очереди"),
        ("processing", "Проверяется"),
        ("checked", "Проверено"),
        ("failed", "Ошибка"),
    ]
    NORMALIZED_PREDICTION_CHOICES = [
        ("approved", "Безопасно"),
        ("rejected", "Небезопасно"),
        ("pending", "Нужна ручная проверка"),
    ]

    review = models.OneToOneField(
        "reviews.Review",
        on_delete=models.CASCADE,
        related_name="moderation_queue",
        verbose_name="Отзыв",
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="queued",
        verbose_name="Статус проверки",
    )
    verdict_sfw = models.BooleanField(
        null=True,
        blank=True,
        verbose_name="SFW вердикт",
    )
    normalized_prediction = models.CharField(
        max_length=20,
        choices=NORMALIZED_PREDICTION_CHOICES,
        default="pending",
        verbose_name="Нормализованное решение",
    )
    confidence = models.FloatField(
        null=True,
        blank=True,
        verbose_name="Уверенность модели",
    )
    message = models.TextField(
        blank=True,
        verbose_name="Сообщение сервиса",
    )
    raw_response = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="Сырой ответ сервиса",
    )
    is_uncertain = models.BooleanField(
        default=False,
        verbose_name="Модель сомневается",
    )
    error = models.TextField(
        blank=True,
        verbose_name="Текст ошибки",
    )
    checked_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Время проверки",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Очередь модерации отзыва"
        verbose_name_plural = "Очередь модерации отзывов"
        ordering = ["-created_at"]

    def __str__(self):
        """Ид отзыва и статус проверки."""
        return f"Проверка отзыва #{self.review_id}: {self.status}"