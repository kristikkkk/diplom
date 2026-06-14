"""Юнит-тесты сервиса модерации и Celery-задач очередей объявлений и отзывов."""
import json
from unittest.mock import patch

from django.test import TestCase

from ads.models import Ad, Category
from ml_service.models import AdModerationQueue, ReviewModerationQueue
from reviews.models import Review
from ml_service.services import ContentModerationService
from ml_service.tasks import process_ad_moderation_task, process_review_moderation_task
from users.models import User


class FakeHttpResponse:
    """Имитация ответа urllib для мока HTTP без реального сокета."""
    def __init__(self, payload):
        """Сохраняет словарь, который будет сериализован в JSON как тело ответа."""
        self.payload = payload

    def read(self):
        """Возвращает тело ответа в байтах UTF-8."""
        return json.dumps(self.payload).encode('utf-8')

    def __enter__(self):
        """Входит в контекст urllib.urlopen."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Завершает контекст без подавления исключений."""
        return False


class ContentModerationServiceTests(TestCase):
    @patch('urllib.request.urlopen')
    def test_predict_detailed_parses_sfw_response(self, urlopen_mock):
        """Проверяет разбор успешного JSON с полями sfw и confidence."""
        urlopen_mock.return_value = FakeHttpResponse(
            {
                'sfw': True,
                'confidence': 0.98,
                'message': 'Контент безопасен (SFW).',
            }
        )
        service = ContentModerationService()

        result = service.predict_detailed(text='test text')

        self.assertEqual(result['normalized_prediction'], 'approved')
        self.assertTrue(result['sfw'])
        self.assertEqual(result['confidence'], 0.98)
        self.assertEqual(result['message'], 'Контент безопасен (SFW).')
        self.assertEqual(result['error'], '')


class AdModerationQueueTaskTests(TestCase):
    def setUp(self):
        """Создаёт пользователя, категорию и объявление для задачи модерации."""
        self.user = User.objects.create_user(
            username='moderation-user',
            email='moderation-user@example.com',
            password='password123',
            role='landlord',
        )
        self.category = Category.objects.create(name='Комнаты')
        self.ad = Ad.objects.create(
            title='Комната рядом с метро',
            description='Сдам комнату',
            price='15000.00',
            category=self.category,
            author=self.user,
        )

    @patch('ml_service.tasks.moderation_service.predict_detailed')
    def test_task_marks_uncertain_when_confidence_below_threshold(self, predict_mock):
        """При низкой уверенности очередь помечается is_uncertain, статус checked сохраняется."""
        predict_mock.return_value = {
            'sfw': True,
            'normalized_prediction': 'approved',
            'confidence': 0.7,
            'message': 'Неуверенный ответ',
            'raw_response': {'sfw': True},
            'error': '',
        }
        queue_item = AdModerationQueue.objects.create(ad=self.ad, status='queued')

        process_ad_moderation_task(queue_item.id)
        queue_item.refresh_from_db()

        self.assertEqual(queue_item.status, 'checked')
        self.assertTrue(queue_item.is_uncertain)
        self.assertEqual(queue_item.normalized_prediction, 'approved')
        self.assertEqual(queue_item.message, 'Неуверенный ответ')


class ReviewModerationQueueTaskTests(TestCase):
    def setUp(self):
        """Готовит пользователей, объявление и отзыв для теста задачи по отзыву."""
        self.user = User.objects.create_user(
            username='review-author',
            email='review-author@example.com',
            password='password123',
            role='tenant',
        )
        self.landlord = User.objects.create_user(
            username='review-landlord',
            email='review-landlord@example.com',
            password='password123',
            role='landlord',
        )
        self.category = Category.objects.create(name='Студии')
        self.ad = Ad.objects.create(
            title='Студия у парка',
            description='Сдам студию',
            price='12000.00',
            category=self.category,
            author=self.landlord,
        )
        self.review = Review.objects.create(
            text='Все понравилось',
            rating=5,
            author=self.user,
            ad=self.ad,
        )

    @patch('ml_service.tasks.moderation_service.predict_detailed')
    def test_review_task_updates_queue(self, predict_mock):
        """Задача обновляет ReviewModerationQueue статусом checked и вердиктом модели."""
        predict_mock.return_value = {
            'sfw': True,
            'normalized_prediction': 'approved',
            'confidence': 0.9,
            'message': 'Ок',
            'raw_response': {'sfw': True},
            'error': '',
        }
        queue_item = ReviewModerationQueue.objects.create(review=self.review, status='queued')

        process_review_moderation_task(queue_item.id)
        queue_item.refresh_from_db()

        self.assertEqual(queue_item.status, 'checked')
        self.assertEqual(queue_item.normalized_prediction, 'approved')
