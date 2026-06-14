"""API-тесты отзывов: создание, список, модерация, права доступа."""
from unittest.mock import patch

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from ads.models import AdModerationHistory
from ml_service.models import ReviewModerationQueue
from reviews.models import Review
from tests.helpers import auth, create_ad, create_admin, create_category, create_landlord, create_tenant


class ReviewCreateAPITests(APITestCase):
    def setUp(self):
        self.author = create_tenant()
        self.landlord = create_landlord()
        self.category = create_category()
        self.ad = create_ad(
            self.landlord,
            category=self.category,
            status='approved',
        )
        self.url = reverse('review-list')

    @patch('reviews.views.process_review_moderation_task.delay')
    def test_create_review_creates_queue_and_enqueues_task(self, delay_mock):
        auth(self.client, self.author)
        payload = {'text': 'Хорошая квартира', 'rating': 5, 'ad_id': self.ad.id}

        response = self.client.post(self.url, payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        review_id = response.data['id']
        queue_item = ReviewModerationQueue.objects.get(review_id=review_id)
        self.assertEqual(queue_item.status, 'queued')
        delay_mock.assert_called_once_with(queue_item.id)

    @patch('reviews.views.process_review_moderation_task.delay')
    def test_duplicate_review_returns_400(self, _delay_mock):
        Review.objects.create(
            text='Первый',
            rating=5,
            author=self.author,
            ad=self.ad,
        )
        auth(self.client, self.author)

        response = self.client.post(
            self.url,
            {'text': 'Второй', 'rating': 4, 'ad_id': self.ad.id},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class ReviewListAPITests(APITestCase):
    def setUp(self):
        self.landlord = create_landlord()
        self.category = create_category()
        self.ad = create_ad(self.landlord, category=self.category, status='approved')
        self.author = create_tenant()
        Review.objects.create(
            text='Одобрен',
            rating=5,
            author=self.author,
            ad=self.ad,
            status='approved',
        )
        Review.objects.create(
            text='На модерации',
            rating=3,
            author=create_tenant(),
            ad=self.ad,
            status='pending',
        )
        self.url = reverse('review-list')

    def test_anonymous_list_shows_only_approved(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data.get('results', response.data)
        texts = [item['text'] for item in data]
        self.assertIn('Одобрен', texts)
        self.assertNotIn('На модерации', texts)

    def test_filter_by_ad(self):
        response = self.client.get(self.url, {'ad': self.ad.id})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data.get('results', response.data)
        for item in data:
            self.assertEqual(item['ad']['id'], self.ad.id)


class MyReviewsAPITests(APITestCase):
    def test_me_returns_only_own_reviews(self):
        user = create_tenant()
        other = create_tenant()
        landlord = create_landlord()
        category = create_category()
        ad = create_ad(landlord, category=category, status='approved')
        mine = Review.objects.create(text='Мой', rating=5, author=user, ad=ad)
        Review.objects.create(text='Чужой', rating=4, author=other, ad=ad)
        auth(self.client, user)
        url = reverse('review-list-mine')

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data.get('results', response.data)
        ids = [item['id'] for item in data]
        self.assertEqual(ids, [mine.id])


class ReviewModerationAPITests(APITestCase):
    def setUp(self):
        self.admin = create_admin()
        self.landlord = create_landlord()
        self.tenant = create_tenant()
        self.category = create_category()
        self.ad = create_ad(self.landlord, category=self.category, status='approved')

    @patch('reviews.views.process_review_moderation_task.delay')
    def test_approve_review_writes_history(self, _delay_mock):
        auth(self.client, self.tenant)
        create_url = reverse('review-list')
        r = self.client.post(
            create_url,
            {'text': 'Нормально', 'rating': 4, 'ad_id': self.ad.id},
            format='json',
        )
        review_id = r.data['id']

        auth(self.client, self.admin)
        approve_url = reverse('approve-review', kwargs={'pk': review_id})
        resp = self.client.post(approve_url, {}, format='json')

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        entry = AdModerationHistory.objects.get(subject_type='review', review_id=review_id)
        self.assertEqual(entry.decision, 'approved')
        self.assertEqual(entry.moderator_id, self.admin.id)

    def test_reject_review_writes_history(self):
        review = Review.objects.create(
            text='Спорный',
            rating=2,
            author=self.tenant,
            ad=self.ad,
            status='pending',
        )
        auth(self.client, self.admin)
        url = reverse('reject-review', kwargs={'pk': review.pk})

        response = self.client.post(
            url,
            {'reason': 'Спам'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        review.refresh_from_db()
        self.assertEqual(review.status, 'rejected')
        entry = AdModerationHistory.objects.get(subject_type='review', review=review)
        self.assertEqual(entry.decision, 'rejected')
        self.assertEqual(entry.reason, 'Спам')

    @patch('reviews.views.process_review_moderation_task.delay')
    def test_retry_review_moderation_enqueues_task(self, delay_mock):
        review = Review.objects.create(
            text='Повтор',
            rating=5,
            author=self.tenant,
            ad=self.ad,
        )
        auth(self.client, self.admin)
        url = reverse('retry-review-moderation', kwargs={'pk': review.pk})

        response = self.client.post(url, {}, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        queue_item = ReviewModerationQueue.objects.get(review=review)
        self.assertEqual(queue_item.status, 'queued')
        delay_mock.assert_called_once_with(queue_item.id)


class ReviewDetailPermissionsAPITests(APITestCase):
    def setUp(self):
        self.author = create_tenant()
        self.other = create_tenant()
        self.landlord = create_landlord()
        self.category = create_category()
        self.ad = create_ad(self.landlord, category=self.category, status='approved')
        self.review = Review.objects.create(
            text='Отзыв',
            rating=5,
            author=self.author,
            ad=self.ad,
            status='approved',
        )

    def test_non_author_patch_does_not_persist_changes(self):
        """perform_update возвращает 403, но DRF всё равно отвечает 200 — проверяем, что в БД не сохранилось."""
        url = reverse('review-detail', kwargs={'pk': self.review.pk})
        auth(self.client, self.other)

        response = self.client.patch(
            url,
            {'text': 'Взлом'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.review.refresh_from_db()
        self.assertEqual(self.review.text, 'Отзыв')

    def test_author_can_update_review(self):
        url = reverse('review-detail', kwargs={'pk': self.review.pk})
        auth(self.client, self.author)

        response = self.client.patch(
            url,
            {'text': 'Обновлённый текст'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.review.refresh_from_db()
        self.assertEqual(self.review.text, 'Обновлённый текст')

    def test_non_author_delete_does_not_remove_review(self):
        url = reverse('review-detail', kwargs={'pk': self.review.pk})
        auth(self.client, self.other)

        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertTrue(Review.objects.filter(pk=self.review.pk).exists())
