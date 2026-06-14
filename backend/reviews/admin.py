"""Админка отзывов с массовым одобрением и отклонением."""
from django.contrib import admin
from .models import Review


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    """Админка для отзывов"""
    list_display = ('author', 'ad', 'rating', 'status', 'created_at')
    list_filter = ('status', 'rating', 'created_at')
    search_fields = ('author__username', 'ad__title', 'text')
    ordering = ('-created_at',)
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('author', 'ad', 'text', 'rating')
        }),
        ('Статус', {
            'fields': ('status',)
        }),
        ('Даты', {
            'fields': ('created_at', 'updated_at')
        }),
    )
    
    readonly_fields = ('created_at', 'updated_at')
    
    actions = ['approve_reviews', 'reject_reviews']
    
    def approve_reviews(self, request, queryset):
        """Одобрить выбранные отзывы"""
        updated = queryset.update(status='approved')
        self.message_user(request, f'{updated} отзывов одобрено.')
    approve_reviews.short_description = 'Одобрить выбранные отзывы'
    
    def reject_reviews(self, request, queryset):
        """Отклонить выбранные отзывы"""
        updated = queryset.update(status='rejected')
        self.message_user(request, f'{updated} отзывов отклонено.')
    reject_reviews.short_description = 'Отклонить выбранные отзывы'