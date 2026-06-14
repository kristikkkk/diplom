"""REST API объявлений, избранного, рекомендаций, чатов и журнала модерации."""
from rest_framework import generics, permissions, status, filters
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q
from django.contrib.auth import get_user_model
from django.conf import settings
from django.http import FileResponse
from pathlib import Path
import mimetypes
from .models import Category, Ad, AdImage, Favorite, Chat, Message, AdModerationHistory
from ml_service.models import AdModerationQueue, ReviewModerationQueue
from ml_service.tasks import process_ad_moderation_task
from .serializers import (
    CategorySerializer, AdSerializer, AdCreateSerializer, FavoriteSerializer,
    ChatSerializer, MessageSerializer, MessageCreateSerializer,
    ModerationHistorySerializer,
)

User = get_user_model()


def _record_ad_moderation_history(ad, moderator, decision, reason=''):
    """Сохраняет запись в журнал с копией состояния очереди ИИ на момент решения."""
    data = {
        'subject_type': 'ad',
        'ad': ad,
        'review': None,
        'moderator': moderator,
        'decision': decision,
        'reason': reason or '',
    }
    try:
        q = ad.moderation_queue
        data.update({
            'ai_status': q.status,
            'ai_normalized_prediction': q.normalized_prediction,
            'ai_confidence': q.confidence,
            'ai_verdict_sfw': q.verdict_sfw,
            'ai_message': q.message or '',
            'ai_error': q.error or '',
            'ai_checked_at': q.checked_at,
        })
    except AdModerationQueue.DoesNotExist:
        pass
    AdModerationHistory.objects.create(**data)


def _record_review_moderation_history(review, moderator, decision, reason=''):
    """Сохраняет запись в журнал по отзыву с копией состояния очереди ИИ на момент решения."""
    data = {
        'subject_type': 'review',
        'ad': None,
        'review': review,
        'moderator': moderator,
        'decision': decision,
        'reason': reason or '',
    }
    try:
        q = review.moderation_queue
        data.update({
            'ai_status': q.status,
            'ai_normalized_prediction': q.normalized_prediction,
            'ai_confidence': q.confidence,
            'ai_verdict_sfw': q.verdict_sfw,
            'ai_message': q.message or '',
            'ai_error': q.error or '',
            'ai_checked_at': q.checked_at,
        })
    except ReviewModerationQueue.DoesNotExist:
        pass
    AdModerationHistory.objects.create(**data)


class IsAdminModerator(permissions.BasePermission):
    """Доступ только для staff или пользователя с ролью admin."""

    def has_permission(self, request, view):
        """True для аутентифицированных staff или пользователей с ролью admin."""
        user = request.user
        if not user or not user.is_authenticated:
            return False
        return user.is_staff or getattr(user, 'role', None) == 'admin'


class AdModerationHistoryListView(generics.ListAPIView):
    """Журнал решений модераторов (объявления и отзывы)."""
    serializer_class = ModerationHistorySerializer
    permission_classes = [IsAdminModerator]

    def get_queryset(self):
        """Возвращает историю с фильтрами decision и subject_type из query params."""
        qs = AdModerationHistory.objects.select_related(
            'ad__author',
            'ad__category',
            'review__author',
            'review__ad',
            'moderator',
        ).order_by('-created_at')
        decision = self.request.query_params.get('decision')
        if decision in ('approved', 'rejected'):
            qs = qs.filter(decision=decision)
        subject_type = self.request.query_params.get('subject_type')
        if subject_type in ('ad', 'review'):
            qs = qs.filter(subject_type=subject_type)
        return qs


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def ad_image_view(request):
    """Отдает изображение объявления по пути из БД (ads_images/...)."""
    image_path = request.query_params.get('path', '').strip()
    if not image_path:
        return Response({'error': 'Не указан path'}, status=status.HTTP_400_BAD_REQUEST)

    media_root = Path(settings.MEDIA_ROOT).resolve()
    requested_path = image_path.lstrip('/\\')
    file_path = (media_root / requested_path).resolve()

    try:
        file_path.relative_to(media_root)
    except ValueError:
        return Response({'error': 'Некорректный путь'}, status=status.HTTP_400_BAD_REQUEST)

    if not file_path.exists() or not file_path.is_file():
        return Response({'error': 'Файл не найден'}, status=status.HTTP_404_NOT_FOUND)

    content_type = mimetypes.guess_type(str(file_path))[0] or 'application/octet-stream'
    return FileResponse(file_path.open('rb'), content_type=content_type)


class CategoryListView(generics.ListAPIView):
    """Список категорий"""
    queryset = Category.objects.filter(is_active=True)
    serializer_class = CategorySerializer
    permission_classes = [permissions.AllowAny]


class AdListView(generics.ListCreateAPIView):
    """Список и создание объявлений"""
    queryset = Ad.objects.select_related('author', 'category', 'moderation_queue').prefetch_related('images')
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['category', 'status', 'is_featured']
    search_fields = ['title', 'description', 'location']
    ordering_fields = ['created_at', 'price', 'views_count']
    ordering = ['-created_at']

    def get_serializer_class(self):
        """POST — создание через AdCreateSerializer; GET — полное отображение AdSerializer."""
        if self.request.method == 'POST':
            return AdCreateSerializer
        return AdSerializer

    def get_queryset(self):
        """Список GET: по умолчанию только одобренные (каталог для всех). Staff/admin с ?status= — полный queryset для модерации."""
        queryset = super().get_queryset()
        if self.request.method != 'GET':
            return queryset
        user = self.request.user
        is_moderator = user.is_authenticated and (
            user.is_staff or getattr(user, 'role', None) == 'admin'
        )
        if is_moderator and 'status' in self.request.query_params:
            return queryset
        return queryset.filter(status='approved')

    def create(self, request, *args, **kwargs):
        """Создание объявления с обработкой изображений"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        ad = serializer.save()
        
        # Обрабатываем изображения
        images = request.FILES.getlist('images')
        if images:
            for index, image in enumerate(images):
                AdImage.objects.create(
                    ad=ad,
                    image=image,
                    is_primary=(index == 0)
                )

        queue_item = AdModerationQueue.objects.create(ad=ad, status='queued')
        try:
            process_ad_moderation_task.delay(queue_item.id)
        except Exception as error:
            queue_item.status = 'failed'
            queue_item.error = str(error)
            queue_item.save(update_fields=['status', 'error', 'updated_at'])
        
        # Возвращаем созданное объявление с изображениями
        response_serializer = AdSerializer(ad, context={'request': request})
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)


class AdDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Детали объявления"""
    queryset = Ad.objects.select_related('author', 'category', 'moderation_queue').prefetch_related('images')
    serializer_class = AdSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_permissions(self):
        """Настройка прав доступа"""
        if self.request.method in ['PUT', 'PATCH', 'DELETE']:
            return [permissions.IsAuthenticated()]
        return [permissions.AllowAny()]

    def get_queryset(self):
        """Фильтруем объявления по статусу для неавторизованных пользователей"""
        queryset = super().get_queryset()
        if not self.request.user.is_authenticated:
            return queryset.filter(status='approved')
        return queryset

    def retrieve(self, request, *args, **kwargs):
        """Увеличиваем счетчик просмотров"""
        instance = self.get_object()
        instance.views_count += 1
        instance.save(update_fields=['views_count'])
        return super().retrieve(request, *args, **kwargs)

    def get_serializer_class(self):
        """Выбираем сериализатор в зависимости от метода"""
        if self.request.method in ['PUT', 'PATCH']:
            return AdSerializer
        return AdSerializer

    def update(self, request, *args, **kwargs):
        """Обновление объявления с обработкой изображений"""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        
        if instance.author != request.user and not request.user.is_staff:
            return Response({'error': 'Нет прав на редактирование'}, 
                          status=status.HTTP_403_FORBIDDEN)
        
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        ad = serializer.save()
        
        # Обрабатываем новые изображения
        images = request.FILES.getlist('images')
        if images:
            # Проверяем, есть ли уже основное изображение
            has_primary = AdImage.objects.filter(ad=ad, is_primary=True).exists()
            for index, image in enumerate(images):
                AdImage.objects.create(
                    ad=ad,
                    image=image,
                    is_primary=(index == 0 and not has_primary)
                )
        
        response_serializer = AdSerializer(ad, context={'request': request})
        return Response(response_serializer.data)

    def perform_destroy(self, instance):
        """Удаляет объявление, если запрос от автора объявления."""
        if instance.author != self.request.user:
            return Response({'error': 'Нет прав на удаление'}, 
                          status=status.HTTP_403_FORBIDDEN)
        instance.delete()


class FavoriteListView(generics.ListCreateAPIView):
    """Избранные объявления"""
    serializer_class = FavoriteSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Избранное текущего пользователя с данными объявления и автора."""
        return Favorite.objects.filter(user=self.request.user).select_related('ad__author', 'ad__category')

    def post(self, request, *args, **kwargs):
        """Добавление в избранное"""
        ad_id = request.data.get('ad_id')
        if not ad_id:
            return Response({'error': 'Не указан ID объявления'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        try:
            ad = Ad.objects.get(id=ad_id)
        except Ad.DoesNotExist:
            return Response({'error': 'Объявление не найдено'}, 
                          status=status.HTTP_404_NOT_FOUND)
        
        favorite, created = Favorite.objects.get_or_create(
            user=request.user,
            ad=ad
        )
        
        if created:
            return Response({'message': 'Добавлено в избранное'}, 
                          status=status.HTTP_201_CREATED)
        else:
            return Response({'message': 'Уже в избранном'}, 
                          status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def approve_ad_view(request, pk):
    """Одобрить объявление (только для админов)"""
    if not request.user.is_staff and request.user.role != 'admin':
        return Response({'error': 'Нет прав доступа'}, 
                      status=status.HTTP_403_FORBIDDEN)
    
    try:
        ad = Ad.objects.get(id=pk)
        ad.status = 'approved'
        ad.save()
        _record_ad_moderation_history(ad, request.user, 'approved')
        return Response({'message': 'Объявление одобрено'})
    except Ad.DoesNotExist:
        return Response({'error': 'Объявление не найдено'}, 
                      status=status.HTTP_404_NOT_FOUND)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def reject_ad_view(request, pk):
    """Отклонить объявление (только для админов)"""
    if not request.user.is_staff and request.user.role != 'admin':
        return Response({'error': 'Нет прав доступа'}, 
                      status=status.HTTP_403_FORBIDDEN)
    
    try:
        ad = Ad.objects.get(id=pk)
        ad.status = 'rejected'
        ad.save()
        reason = (request.data.get('reason') or '') if isinstance(request.data, dict) else ''
        _record_ad_moderation_history(ad, request.user, 'rejected', reason=reason)
        return Response({'message': 'Объявление отклонено'})
    except Ad.DoesNotExist:
        return Response({'error': 'Объявление не найдено'}, 
                      status=status.HTTP_404_NOT_FOUND)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def retry_ad_moderation_view(request, pk):
    """Снова отправить объявление в очередь модерации ИИ (только для админов)."""
    if not request.user.is_staff and getattr(request.user, 'role', None) != 'admin':
        return Response({'error': 'Нет прав доступа'},
                      status=status.HTTP_403_FORBIDDEN)

    try:
        ad = Ad.objects.get(id=pk)
    except Ad.DoesNotExist:
        return Response({'error': 'Объявление не найдено'},
                      status=status.HTTP_404_NOT_FOUND)

    queue_item, created = AdModerationQueue.objects.get_or_create(
        ad=ad,
        defaults={'status': 'queued'},
    )
    if not created:
        queue_item.status = 'queued'
        queue_item.error = ''
        queue_item.save(update_fields=['status', 'error', 'updated_at'])

    try:
        process_ad_moderation_task.delay(queue_item.id)
    except Exception as error:
        queue_item.status = 'failed'
        queue_item.error = str(error)
        queue_item.save(update_fields=['status', 'error', 'updated_at'])
        return Response(
            {'error': f'Не удалось поставить задачу в очередь: {error}'},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    return Response({
        'message': 'Объявление снова отправлено на проверку ИИ',
        'queue_id': queue_item.id,
    })


@api_view(['DELETE'])
@permission_classes([permissions.IsAuthenticated])
def remove_favorite_view(request):
    """Удаление из избранного"""
    ad_id = request.data.get('ad_id')
    if not ad_id:
        return Response({'error': 'Не указан ID объявления'}, 
                      status=status.HTTP_400_BAD_REQUEST)
    
    try:
        favorite = Favorite.objects.get(user=request.user, ad_id=ad_id)
        favorite.delete()
        return Response({'message': 'Удалено из избранного'}, 
                      status=status.HTTP_200_OK)
    except Favorite.DoesNotExist:
        return Response({'error': 'Не найдено в избранном'}, 
                      status=status.HTTP_404_NOT_FOUND)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def recommendations_view(request):
    """Рекомендации для пользователя"""
    user = request.user
    
    # Получаем избранные объявления пользователя
    favorite_ads = Favorite.objects.filter(user=user).values_list('ad_id', flat=True)
    
    if not favorite_ads:
        # Если нет избранных, показываем популярные объявления
        recommendations = Ad.objects.filter(status='approved').order_by('-views_count')[:10]
    else:
        # Получаем категории избранных объявлений
        favorite_categories = Ad.objects.filter(id__in=favorite_ads).values_list('category_id', flat=True)
        
        # Ищем похожие объявления
        recommendations = Ad.objects.filter(
            category_id__in=favorite_categories,
            status='approved'
        ).exclude(id__in=favorite_ads).order_by('-views_count')[:10]
    
    serializer = AdSerializer(recommendations, many=True, context={'request': request})
    return Response(serializer.data)


class ChatListView(generics.ListCreateAPIView):
    """Список чатов пользователя"""
    serializer_class = ChatSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Получаем чаты текущего пользователя"""
        user = self.request.user
        return Chat.objects.filter(
            Q(tenant=user) | Q(landlord=user)
        ).select_related('ad', 'tenant', 'landlord').prefetch_related('messages__sender')

    def get_serializer_context(self):
        """Прокидывает request в сериализатор (избранное, абсолютные URL и т.д.)."""
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

    def create(self, request, *args, **kwargs):
        """Создание чата по объявлению"""
        ad_id = request.data.get('ad_id')
        if not ad_id:
            return Response({'error': 'Не указан ID объявления'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        try:
            ad = Ad.objects.get(id=ad_id)
        except Ad.DoesNotExist:
            return Response({'error': 'Объявление не найдено'}, 
                          status=status.HTTP_404_NOT_FOUND)
        if request.user == ad.author:
            # Если пользователь - автор объявления, он арендодатель
            tenant_id = request.data.get('tenant_id')
            if not tenant_id:
                return Response({'error': 'Не указан ID арендатора'}, 
                              status=status.HTTP_400_BAD_REQUEST)
            try:
                tenant = User.objects.get(id=tenant_id)
            except User.DoesNotExist:
                return Response({'error': 'Пользователь не найден'}, 
                              status=status.HTTP_404_NOT_FOUND)
            landlord = request.user
        else:
            # Если пользователь не автор, он арендатор
            tenant = request.user
            landlord = ad.author
        # Проверяем, существует ли уже чат
        chat, created = Chat.objects.get_or_create(
            ad=ad,
            tenant=tenant,
            landlord=landlord
        )
        serializer = ChatSerializer(chat, context={'request': request})
        return Response(serializer.data, 
                      status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


class ChatDetailView(generics.RetrieveAPIView):
    """Детали чата"""
    serializer_class = ChatSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Получаем чаты текущего пользователя"""
        user = self.request.user
        return Chat.objects.filter(
            Q(tenant=user) | Q(landlord=user)
        ).select_related('ad', 'tenant', 'landlord').prefetch_related('messages__sender')

    def get_serializer_context(self):
        """Прокидывает request для вложенных сериализаторов объявления и сообщений."""
        context = super().get_serializer_context()
        context['request'] = self.request
        return context


class MessageListView(generics.ListCreateAPIView):
    """Список сообщений в чате"""
    serializer_class = MessageSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Получаем сообщения чата"""
        chat_id = self.kwargs.get('chat_id')
        user = self.request.user
        
        # Проверяем, что пользователь участвует в чате
        try:
            chat = Chat.objects.get(id=chat_id)
            if chat.tenant != user and chat.landlord != user:
                return Message.objects.none()
        except Chat.DoesNotExist:
            return Message.objects.none()
        
        return Message.objects.filter(chat_id=chat_id).select_related('sender').order_by('created_at')

    def create(self, request, *args, **kwargs):
        """Создание сообщения"""
        chat_id = self.kwargs.get('chat_id')
        user = request.user
        
        try:
            chat = Chat.objects.get(id=chat_id)
            if chat.tenant != user and chat.landlord != user:
                return Response({'error': 'Нет доступа к этому чату'}, 
                              status=status.HTTP_403_FORBIDDEN)
        except Chat.DoesNotExist:
            return Response({'error': 'Чат не найден'}, 
                          status=status.HTTP_404_NOT_FOUND)
        
        serializer = MessageCreateSerializer(
            data=request.data,
            context={'request': request, 'chat': chat}
        )
        serializer.is_valid(raise_exception=True)
        message = serializer.save()
        
        # Обновляем время последнего обновления чата
        chat.save(update_fields=['updated_at'])
        
        # Помечаем сообщения как прочитанные для отправителя
        Message.objects.filter(chat=chat, sender=user, is_read=False).update(is_read=True)
        
        return Response(MessageSerializer(message).data, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def mark_messages_read(request, chat_id):
    """Пометить сообщения как прочитанные"""
    try:
        chat = Chat.objects.get(id=chat_id)
        if chat.tenant != request.user and chat.landlord != request.user:
            return Response({'error': 'Нет доступа к этому чату'}, 
                          status=status.HTTP_403_FORBIDDEN)
        
        # Помечаем все сообщения от другого пользователя как прочитанные
        other_user = chat.tenant if request.user == chat.landlord else chat.landlord
        Message.objects.filter(chat=chat, sender=other_user, is_read=False).update(is_read=True)
        
        return Response({'message': 'Сообщения помечены как прочитанные'})
    except Chat.DoesNotExist:
        return Response({'error': 'Чат не найден'}, 
                      status=status.HTTP_404_NOT_FOUND)