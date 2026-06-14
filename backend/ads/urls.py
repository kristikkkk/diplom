"""Маршруты под префиксом /api/ads/: объявления, избранное, чаты, модерация."""
from django.urls import path
from . import views

urlpatterns = [
    path('image/', views.ad_image_view, name='ad-image'),
    path('categories/', views.CategoryListView.as_view(), name='category-list'),
    path('moderation-history/', views.AdModerationHistoryListView.as_view(), name='ad-moderation-history'),
    path('', views.AdListView.as_view(), name='ad-list'),
    path('<int:pk>/', views.AdDetailView.as_view(), name='ad-detail'),
    path('<int:pk>/approve/', views.approve_ad_view, name='approve-ad'),
    path('<int:pk>/reject/', views.reject_ad_view, name='reject-ad'),
    path('<int:pk>/retry-moderation/', views.retry_ad_moderation_view, name='retry-ad-moderation'),
    path('favorites/', views.FavoriteListView.as_view(), name='favorite-list'),
    path('favorites/remove/', views.remove_favorite_view, name='remove-favorite'),
    path('recommendations/', views.recommendations_view, name='recommendations'),
    # Chat URLs
    path('chats/', views.ChatListView.as_view(), name='chat-list'),
    path('chats/<int:pk>/', views.ChatDetailView.as_view(), name='chat-detail'),
    path('chats/<int:chat_id>/messages/', views.MessageListView.as_view(), name='message-list'),
    path('chats/<int:chat_id>/read/', views.mark_messages_read, name='mark-messages-read'),
]
