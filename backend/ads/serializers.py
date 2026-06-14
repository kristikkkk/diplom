"""Сериализаторы объявлений, медиа, избранного, чатов и журнала модерации для API."""
from rest_framework import serializers
from urllib.parse import quote
from reviews.models import Review
from .models import Category, Ad, AdImage, Favorite, Chat, Message, AdModerationHistory
from users.serializers import UserSerializer


class CategorySerializer(serializers.ModelSerializer):
    """Сериализатор для категорий"""
    
    class Meta:
        model = Category
        fields = ('id', 'name', 'description', 'icon', 'is_active')


class AdImageSerializer(serializers.ModelSerializer):
    """Сериализатор для изображений объявлений"""
    image = serializers.SerializerMethodField()

    def get_image(self, obj):
        """Возвращает URL прокси `/api/media/image/` для файла в хранилище."""
        if not obj.image:
            return None
        image_path = quote(obj.image.name, safe='')
        return f"/api/media/image/?path={image_path}"
    
    class Meta:
        model = AdImage
        fields = ('id', 'image', 'is_primary')


class AdSerializer(serializers.ModelSerializer):
    """Сериализатор для объявлений"""
    author = UserSerializer(read_only=True)
    category = CategorySerializer(read_only=True)
    category_id = serializers.IntegerField(write_only=True)
    images = AdImageSerializer(many=True, read_only=True)
    is_favorite = serializers.SerializerMethodField()
    ai_moderation = serializers.SerializerMethodField()
    
    class Meta:
        model = Ad
        fields = ('id', 'title', 'description', 'price', 'category', 'category_id',
                 'author', 'status', 'location', 'contact_phone', 'contact_email',
                 'is_featured', 'views_count', 'images', 'is_favorite', 'ai_moderation',
                 'created_at', 'updated_at', 'published_at')
        read_only_fields = ('id', 'author', 'status', 'views_count', 
                           'created_at', 'updated_at', 'published_at')

    def get_is_favorite(self, obj):
        """Проверяем, добавлено ли объявление в избранное"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return Favorite.objects.filter(user=request.user, ad=obj).exists()
        return False

    def get_ai_moderation(self, obj):
        """Для админов добавляет состояние очереди ML по объявлению; для остальных — None."""
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return None

        if not request.user.is_staff and getattr(request.user, 'role', None) != 'admin':
            return None

        queue_item = getattr(obj, 'moderation_queue', None)
        if not queue_item:
            return None

        return {
            'status': queue_item.status,
            'verdict_sfw': queue_item.verdict_sfw,
            'normalized_prediction': queue_item.normalized_prediction,
            'confidence': queue_item.confidence,
            'message': queue_item.message,
            'is_uncertain': queue_item.is_uncertain,
            'checked_at': queue_item.checked_at,
            'error': queue_item.error,
        }

    def create(self, validated_data):
        """Создаёт объявление от имени пользователя из текущего запроса."""
        validated_data['author'] = self.context['request'].user
        return super().create(validated_data)

    def update(self, instance, validated_data):
        """Обновление объявления с обработкой category_id"""
        category_id = validated_data.pop('category_id', None)
        if category_id:
            validated_data['category'] = Category.objects.get(id=category_id)
        return super().update(instance, validated_data)


class AdSummaryForHistorySerializer(serializers.ModelSerializer):
    """Краткое объявление для журнала модерации."""
    author = UserSerializer(read_only=True)
    category = CategorySerializer(read_only=True)

    class Meta:
        model = Ad
        fields = ('id', 'title', 'status', 'author', 'category')


class AdTitleOnlySerializer(serializers.ModelSerializer):
    """Минимум полей объявления для контекста отзыва в журнале."""

    class Meta:
        model = Ad
        fields = ('id', 'title')


class ReviewSummaryForHistorySerializer(serializers.ModelSerializer):
    """Отзыв для журнала модерации."""
    ad = AdTitleOnlySerializer(read_only=True)
    author = UserSerializer(read_only=True)

    class Meta:
        model = Review
        fields = ('id', 'text', 'rating', 'ad', 'author')


class ModerationHistorySerializer(serializers.ModelSerializer):
    """Запись журнала модерации (объявление или отзыв)."""
    ad = AdSummaryForHistorySerializer(read_only=True, allow_null=True)
    review = ReviewSummaryForHistorySerializer(read_only=True, allow_null=True)
    moderator = UserSerializer(read_only=True)

    class Meta:
        model = AdModerationHistory
        fields = (
            'id',
            'subject_type',
            'ad',
            'review',
            'moderator',
            'decision',
            'reason',
            'created_at',
            'ai_status',
            'ai_normalized_prediction',
            'ai_confidence',
            'ai_verdict_sfw',
            'ai_message',
            'ai_error',
            'ai_checked_at',
        )


# Обратная совместимость импортов
AdModerationHistorySerializer = ModerationHistorySerializer


class AdCreateSerializer(serializers.ModelSerializer):
    """Сериализатор для создания объявлений"""
    category_id = serializers.IntegerField(write_only=True)
    
    class Meta:
        model = Ad
        fields = ('title', 'description', 'price', 'category_id', 'location',
                 'contact_phone', 'contact_email')

    def create(self, validated_data):
        """Подставляет категорию по id и автора из запроса."""
        category_id = validated_data.pop('category_id')
        validated_data['category'] = Category.objects.get(id=category_id)
        validated_data['author'] = self.context['request'].user
        return super().create(validated_data)


class FavoriteSerializer(serializers.ModelSerializer):
    """Сериализатор для избранных объявлений"""
    ad = AdSerializer(read_only=True)
    
    class Meta:
        model = Favorite
        fields = ('id', 'ad', 'created_at')
        read_only_fields = ('id', 'created_at')


class MessageSerializer(serializers.ModelSerializer):
    """Сериализатор для сообщений"""
    sender = UserSerializer(read_only=True)
    
    class Meta:
        model = Message
        fields = ('id', 'sender', 'text', 'is_read', 'created_at')
        read_only_fields = ('id', 'sender', 'is_read', 'created_at')


class ChatSerializer(serializers.ModelSerializer):
    """Сериализатор для чата"""
    ad = AdSerializer(read_only=True)
    tenant = UserSerializer(read_only=True)
    landlord = UserSerializer(read_only=True)
    messages = MessageSerializer(many=True, read_only=True)
    unread_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Chat
        fields = ('id', 'ad', 'tenant', 'landlord', 'messages', 'unread_count', 'created_at', 'updated_at')
        read_only_fields = ('id', 'created_at', 'updated_at')
    
    def get_unread_count(self, obj):
        """Число непрочитанных сообщений от собеседника для текущего пользователя."""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return Message.objects.filter(chat=obj, is_read=False).exclude(sender=request.user).count()
        return 0


class MessageCreateSerializer(serializers.ModelSerializer):
    """Сериализатор для создания сообщений"""
    
    class Meta:
        model = Message
        fields = ('text',)
    
    def create(self, validated_data):
        """Создаёт сообщение от текущего пользователя в переданном через контекст чате."""
        validated_data['sender'] = self.context['request'].user
        validated_data['chat'] = self.context['chat']
        return super().create(validated_data)

