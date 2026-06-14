"""Маршруты /api/reviews/: список, свои отзывы, детали и действия модератора."""
from django.urls import path
from . import views

urlpatterns = [
    path('me/', views.MyReviewsListView.as_view(), name='review-list-mine'),
    path('', views.ReviewListView.as_view(), name='review-list'),
    path('<int:pk>/retry-moderation/', views.retry_review_moderation_view, name='retry-review-moderation'),
    path('<int:pk>/approve/', views.approve_review_view, name='approve-review'),
    path('<int:pk>/reject/', views.reject_review_view, name='reject-review'),
    path('<int:pk>/', views.ReviewDetailView.as_view(), name='review-detail'),
]

