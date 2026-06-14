"""Модели общих справочных данных проекта (глобальные настройки сайта)."""
from django.db import models


class SiteSettings(models.Model):
    """Глобальные настройки сайта (контакты, флаги модерации, лимиты); хранится не более одной записи."""
    
    site_name = models.CharField(
        max_length=100, 
        default='Доска объявлений',
        verbose_name='Название сайта'
    )
    site_description = models.TextField(
        blank=True,
        verbose_name='Описание сайта'
    )
    contact_email = models.EmailField(
        blank=True,
        verbose_name='Контактный email'
    )
    contact_phone = models.CharField(
        max_length=20,
        blank=True,
        verbose_name='Контактный телефон'
    )
    moderation_enabled = models.BooleanField(
        default=True,
        verbose_name='Включена модерация'
    )
    ml_moderation_enabled = models.BooleanField(
        default=True,
        verbose_name='Включена ML-модерация'
    )
    max_images_per_ad = models.PositiveIntegerField(
        default=10,
        verbose_name='Максимум изображений на объявление'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Настройки сайта'
        verbose_name_plural = 'Настройки сайта'

    def __str__(self):
        """Возвращает отображаемое имя сайта для админки и отладки."""
        return self.site_name

    def save(self, *args, **kwargs):
        """Сохраняет запись; при первом создании не допускает второй строки настроек."""
        # Обеспечиваем единственность записи настроек
        if not self.pk and SiteSettings.objects.exists():
            return
        super().save(*args, **kwargs)