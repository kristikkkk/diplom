"""Админка категорий, объявлений, изображений, избранного, чатов и сообщений."""
from django.contrib import admin
from .models import Category, Ad, AdImage, Favorite, Chat, Message


class AdImageInline(admin.TabularInline):
    """Инлайн для изображений объявлений"""
    model = AdImage
    extra = 1
    fields = ('image', 'is_primary')


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    """Админка для категорий"""
    list_display = ('name', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'description')
    ordering = ('name',)


@admin.register(Ad)
class AdAdmin(admin.ModelAdmin):
    """Админка для объявлений"""
    list_display = ('title', 'author', 'category', 'status', 'price', 'views_count', 'created_at')
    list_filter = ('status', 'category', 'is_featured', 'created_at')
    search_fields = ('title', 'description', 'author__username', 'author__email')
    ordering = ('-created_at',)
    inlines = [AdImageInline]
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('title', 'description', 'category', 'author', 'price')
        }),
        ('Контактная информация', {
            'fields': ('location', 'contact_phone', 'contact_email')
        }),
        ('Статус и настройки', {
            'fields': ('status', 'is_featured', 'views_count')
        }),
        ('Даты', {
            'fields': ('created_at', 'updated_at', 'published_at')
        }),
    )
    
    readonly_fields = ('created_at', 'updated_at', 'views_count')
    
    actions = ['approve_ads', 'reject_ads']
    
    def approve_ads(self, request, queryset):
        """Одобрить выбранные объявления"""
        updated = queryset.update(status='approved')
        self.message_user(request, f'{updated} объявлений одобрено.')
    approve_ads.short_description = 'Одобрить выбранные объявления'
    
    def reject_ads(self, request, queryset):
        """Отклонить выбранные объявления"""
        updated = queryset.update(status='rejected')
        self.message_user(request, f'{updated} объявлений отклонено.')
    reject_ads.short_description = 'Отклонить выбранные объявления'


@admin.register(AdImage)
class AdImageAdmin(admin.ModelAdmin):
    """Админка для изображений объявлений"""
    list_display = ('ad', 'is_primary', 'created_at')
    list_filter = ('is_primary', 'created_at')
    search_fields = ('ad__title',)


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    """Админка для избранных объявлений"""
    list_display = ('user', 'ad', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('user__username', 'ad__title')
    ordering = ('-created_at',)


class MessageInline(admin.TabularInline):
    """Инлайн для сообщений в чате"""
    model = Message
    extra = 0
    fields = ('sender', 'text', 'is_read', 'created_at')
    readonly_fields = ('created_at',)


@admin.register(Chat)
class ChatAdmin(admin.ModelAdmin):
    """Админка для чатов"""
    list_display = ('id', 'ad', 'tenant', 'landlord', 'created_at', 'updated_at')
    list_filter = ('created_at', 'updated_at')
    search_fields = ('ad__title', 'tenant__username', 'landlord__username')
    ordering = ('-updated_at',)
    inlines = [MessageInline]
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('ad', 'tenant', 'landlord')
        }),
        ('Даты', {
            'fields': ('created_at', 'updated_at')
        }),
    )
    
    readonly_fields = ('created_at', 'updated_at')


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    """Админка для сообщений"""
    list_display = ('id', 'chat', 'sender', 'text_preview', 'is_read', 'created_at')
    list_filter = ('is_read', 'created_at')
    search_fields = ('text', 'sender__username', 'chat__ad__title')
    ordering = ('-created_at',)
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('chat', 'sender', 'text', 'is_read')
        }),
        ('Даты', {
            'fields': ('created_at',)
        }),
    )
    
    readonly_fields = ('created_at',)
    
    def text_preview(self, obj):
        """Превью текста сообщения"""
        return obj.text[:50] + '...' if len(obj.text) > 50 else obj.text
    text_preview.short_description = 'Текст'