"""Сериализаторы отзывов и представление объявления во вкладке «мои отзывы»."""
from rest_framework import serializers
from ads.models import Ad
from .models import Review
from users.serializers import UserSerializer
from ads.serializers import AdSerializer


class ReviewSerializer(serializers.ModelSerializer):
    """Чтение/создание отзыва с вложенным объявлением и блоком ai_moderation для админов."""
    author = UserSerializer(read_only=True)
    ad = AdSerializer(read_only=True)
    ad_id = serializers.IntegerField(write_only=True)
    ai_moderation = serializers.SerializerMethodField()

    class Meta:
        model = Review
        fields = ('id', 'text', 'rating', 'author', 'ad', 'ad_id', 'status',
                 'created_at', 'updated_at', 'ai_moderation')
        read_only_fields = ('id', 'author', 'status', 'created_at', 'updated_at')

    def create(self, validated_data):
        """Назначает автором текущего пользователя перед сохранением."""
        validated_data['author'] = self.context['request'].user
        return super().create(validated_data)

    def validate_rating(self, value):
        """Валидация рейтинга"""
        if not 1 <= value <= 5:
            raise serializers.ValidationError("Рейтинг должен быть от 1 до 5")
        return value

    def get_ai_moderation(self, obj):
        """Для администраторов возвращает состояние ReviewModerationQueue; иначе None."""
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


class AdBriefSerializer(serializers.ModelSerializer):
    """Краткое объявление для списка «мои отзывы»."""

    class Meta:
        model = Ad
        fields = ('id', 'title')


class MyReviewSerializer(serializers.ModelSerializer):
    """Отзывы текущего пользователя с причиной отклонения из журнала модерации."""

    ad = AdBriefSerializer(read_only=True)
    moderation_rejection_reason = serializers.SerializerMethodField()

    class Meta:
        model = Review
        fields = (
            'id',
            'text',
            'rating',
            'ad',
            'status',
            'created_at',
            'updated_at',
            'moderation_rejection_reason',
        )

    def get_moderation_rejection_reason(self, obj):
        """Подтягивает текст причины из последней записи журнала модерации для отклонённого отзыва."""
        if obj.status != 'rejected':
            return ''
        from ads.models import AdModerationHistory

        entry = (
            AdModerationHistory.objects.filter(
                subject_type='review',
                review_id=obj.pk,
                decision='rejected',
            )
            .order_by('-created_at')
            .first()
        )
        return (entry.reason or '') if entry else ''


