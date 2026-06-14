"""Регистрация модели настроек сайта в Django Admin с ограничением лишних записей."""
from django.contrib import admin
from .models import SiteSettings


@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    """Админка для единственной записи глобальных настроек сайта."""
    list_display = ('site_name', 'moderation_enabled', 'ml_moderation_enabled', 'updated_at')
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('site_name', 'site_description')
        }),
        ('Контактная информация', {
            'fields': ('contact_email', 'contact_phone')
        }),
        ('Настройки модерации', {
            'fields': ('moderation_enabled', 'ml_moderation_enabled', 'max_images_per_ad')
        }),
    )
    
    def has_add_permission(self, request):
        """Разрешает добавление только если записи настроек ещё нет."""
        return not SiteSettings.objects.exists()
    
    def has_delete_permission(self, request, obj=None):
        """Запрещает удаление настроек (защита от потери конфигурации)."""
        return False