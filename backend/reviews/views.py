"""REST API отзывов: список, создание, модерация и повторная проверка ML."""
from rest_framework import generics, permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from ml_service.models import ReviewModerationQueue
from ml_service.tasks import process_review_moderation_task
from ads.views import IsAdminModerator, _record_review_moderation_history

from .models import Review
from .serializers import ReviewSerializer, MyReviewSerializer


class MyReviewsListView(generics.ListAPIView):
    """Отзывы только текущего пользователя (вкладка профиля)."""

    serializer_class = MyReviewSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Все отзывы текущего пользователя с подгрузкой объявления."""
        return (
            Review.objects.filter(author=self.request.user)
            .select_related('ad')
            .order_by('-created_at')
        )


class ReviewListView(generics.ListCreateAPIView):
    """Публичный список (только одобренные для анонимов) и создание отзыва с очередью ML."""
    serializer_class = ReviewSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['ad', 'rating', 'status']

    def get_queryset(self):
        """Фильтруем отзывы по статусу для неавторизованных пользователей"""
        queryset = Review.objects.select_related(
            'author', 'ad__author', 'ad__category', 'moderation_queue'
        )
        if not self.request.user.is_authenticated:
            return queryset.filter(status='approved')
        return queryset

    def create(self, request, *args, **kwargs):
        """Создание отзыва и постановка в очередь проверки ИИ."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        ad_id = serializer.validated_data.get('ad_id')
        if Review.objects.filter(author=request.user, ad_id=ad_id).exists():
            return Response(
                {'error': 'Вы уже оставили отзыв на это объявление'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer.save()
        review = serializer.instance

        queue_item = ReviewModerationQueue.objects.create(review=review, status='queued')
        try:
            process_review_moderation_task.delay(queue_item.id)
        except Exception as error:
            queue_item.status = 'failed'
            queue_item.error = str(error)
            queue_item.save(update_fields=['status', 'error', 'updated_at'])

        response_serializer = ReviewSerializer(review, context={'request': request})
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)


class ReviewDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Просмотр отзыва и изменение/удаление автором."""
    queryset = Review.objects.select_related(
        'author', 'ad__author', 'ad__category', 'moderation_queue'
    )
    serializer_class = ReviewSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_permissions(self):
        """Настройка прав доступа"""
        if self.request.method in ['PUT', 'PATCH', 'DELETE']:
            return [permissions.IsAuthenticated()]
        return [permissions.AllowAny()]

    def get_queryset(self):
        """Фильтруем отзывы по статусу для неавторизованных пользователей"""
        queryset = super().get_queryset()
        if not self.request.user.is_authenticated:
            return queryset.filter(status='approved')
        return queryset

    def perform_update(self, serializer):
        """Сохраняет изменения только если пользователь — автор отзыва."""
        if serializer.instance.author != self.request.user:
            return Response({'error': 'Нет прав на редактирование'},
                          status=status.HTTP_403_FORBIDDEN)
        serializer.save()

    def perform_destroy(self, instance):
        """Удаляет отзыв только если пользователь — автор."""
        if instance.author != self.request.user:
            return Response({'error': 'Нет прав на удаление'},
                          status=status.HTTP_403_FORBIDDEN)
        instance.delete()


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def approve_review_view(request, pk):
    """Одобрить отзыв (только для админов)"""
    if not request.user.is_staff and request.user.role != 'admin':
        return Response({'error': 'Нет прав доступа'},
                      status=status.HTTP_403_FORBIDDEN)

    try:
        review = Review.objects.select_related('moderation_queue').get(id=pk)
        review.status = 'approved'
        review.save()
        _record_review_moderation_history(review, request.user, 'approved')
        return Response({'message': 'Отзыв одобрен'})
    except Review.DoesNotExist:
        return Response({'error': 'Отзыв не найден'},
                      status=status.HTTP_404_NOT_FOUND)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def reject_review_view(request, pk):
    """Отклонить отзыв (только для админов)"""
    if not request.user.is_staff and request.user.role != 'admin':
        return Response({'error': 'Нет прав доступа'},
                      status=status.HTTP_403_FORBIDDEN)

    try:
        review = Review.objects.select_related('moderation_queue').get(id=pk)
        review.status = 'rejected'
        review.save()
        reason = (request.data.get('reason') or '') if isinstance(request.data, dict) else ''
        _record_review_moderation_history(review, request.user, 'rejected', reason=reason)
        return Response({'message': 'Отзыв отклонен'})
    except Review.DoesNotExist:
        return Response({'error': 'Отзыв не найден'},
                      status=status.HTTP_404_NOT_FOUND)


@api_view(['POST'])
@permission_classes([IsAdminModerator])
def retry_review_moderation_view(request, pk):
    """Снова отправить отзыв на проверку ИИ (только для админов)."""
    try:
        review = Review.objects.get(id=pk)
    except Review.DoesNotExist:
        return Response({'error': 'Отзыв не найден'},
                      status=status.HTTP_404_NOT_FOUND)

    queue_item, created = ReviewModerationQueue.objects.get_or_create(
        review=review,
        defaults={'status': 'queued'},
    )
    if not created:
        queue_item.status = 'queued'
        queue_item.error = ''
        queue_item.save(update_fields=['status', 'error', 'updated_at'])

    try:
        process_review_moderation_task.delay(queue_item.id)
    except Exception as error:
        queue_item.status = 'failed'
        queue_item.error = str(error)
        queue_item.save(update_fields=['status', 'error', 'updated_at'])
        return Response(
            {'error': f'Не удалось поставить задачу в очередь: {error}'},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    return Response({
        'message': 'Отзыв снова отправлен на проверку ИИ',
        'queue_id': queue_item.id,
    })
