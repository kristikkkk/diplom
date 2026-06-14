"""Админка ML-моделей, логов предсказаний и очередей модерации."""
from django.contrib import admin
from .models import MLModel, PredictionLog, AdModerationQueue, ReviewModerationQueue


@admin.register(MLModel)
class MLModelAdmin(admin.ModelAdmin):
    """Админка для ML моделей"""
    list_display = ('name', 'model_type', 'is_active', 'accuracy', 'created_at')
    list_filter = ('model_type', 'is_active', 'created_at')
    search_fields = ('name', 'model_path')
    ordering = ('-created_at',)
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('name', 'model_type', 'model_path')
        }),
        ('Настройки', {
            'fields': ('is_active', 'accuracy')
        }),
    )


@admin.register(PredictionLog)
class PredictionLogAdmin(admin.ModelAdmin):
    """Админка для логов предсказаний"""
    list_display = ('model', 'content_type', 'content_id', 'prediction', 'confidence', 'is_correct', 'created_at')
    list_filter = ('model', 'content_type', 'prediction', 'is_correct', 'created_at')
    search_fields = ('text', 'model__name')
    ordering = ('-created_at',)
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('model', 'content_type', 'content_id', 'text')
        }),
        ('Результат', {
            'fields': ('prediction', 'confidence', 'is_correct')
        }),
    )
    
    readonly_fields = ('created_at',)


@admin.register(AdModerationQueue)
class AdModerationQueueAdmin(admin.ModelAdmin):
    """Админка очереди модерации объявлений."""

    list_display = (
        'ad',
        'status',
        'normalized_prediction',
        'confidence',
        'is_uncertain',
        'checked_at',
        'created_at',
    )
    list_filter = ('status', 'normalized_prediction', 'is_uncertain', 'created_at')
    search_fields = ('ad__title', 'ad__author__username', 'ad__author__email', 'message', 'error')
    ordering = ('-created_at',)
    readonly_fields = ('created_at', 'updated_at', 'checked_at')


@admin.register(ReviewModerationQueue)
class ReviewModerationQueueAdmin(admin.ModelAdmin):
    """Админка очереди модерации отзывов."""

    list_display = (
        'review',
        'status',
        'normalized_prediction',
        'confidence',
        'is_uncertain',
        'checked_at',
        'created_at',
    )
    list_filter = ('status', 'normalized_prediction', 'is_uncertain', 'created_at')
    search_fields = ('review__text', 'review__author__username', 'message', 'error')
    ordering = ('-created_at',)
    readonly_fields = ('created_at', 'updated_at', 'checked_at')