"""API-тесты создания, просмотра, обновления и удаления объявлений."""
from decimal import Decimal
from unittest.mock import patch

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from ads.models import Ad
from ml_service.models import AdModerationQueue
from tests.helpers import auth, create_ad, create_category, create_landlord, create_tenant


class AdCreateAPITests(APITestCase):
    def setUp(self):
        self.user = create_landlord()
        self.category = create_category()
        self.url = reverse('ad-list')

    @patch('ads.views.process_ad_moderation_task.delay')
    def test_create_ad_creates_queue_item_and_enqueues_task(self, delay_mock):
        auth(self.client, self.user)
        payload = {
            'title': 'Уютная квартира',
            'description': 'Описание квартиры',
            'price': '10000.00',
            'category_id': self.category.id,
            'location': 'Москва',
        }

        response = self.client.post(self.url, payload, format='multipart')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        ad = Ad.objects.get(id=response.data['id'])
        self.assertEqual(ad.status, 'pending')
        self.assertEqual(ad.price, Decimal('10000.00'))
        queue_item = AdModerationQueue.objects.get(ad=ad)
        self.assertEqual(queue_item.status, 'queued')
        delay_mock.assert_called_once_with(queue_item.id)


class AdDetailAPITests(APITestCase):
    def setUp(self):
        self.landlord = create_landlord()
        self.other = create_tenant()
        self.category = create_category()
        self.approved = create_ad(
            self.landlord,
            category=self.category,
            status='approved',
            views_count=5,
        )
        self.pending = create_ad(
            self.landlord,
            category=self.category,
            status='pending',
        )

    def test_retrieve_increments_views_count(self):
        url = reverse('ad-detail', kwargs={'pk': self.approved.pk})

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.approved.refresh_from_db()
        self.assertEqual(self.approved.views_count, 6)

    def test_anonymous_cannot_retrieve_pending_ad(self):
        url = reverse('ad-detail', kwargs={'pk': self.pending.pk})

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_author_can_patch_ad(self):
        url = reverse('ad-detail', kwargs={'pk': self.approved.pk})
        auth(self.client, self.landlord)

        response = self.client.patch(
            url,
            {'title': 'Новый заголовок'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.approved.refresh_from_db()
        self.assertEqual(self.approved.title, 'Новый заголовок')

    def test_non_author_patch_returns_403(self):
        url = reverse('ad-detail', kwargs={'pk': self.approved.pk})
        auth(self.client, self.other)

        response = self.client.patch(
            url,
            {'title': 'Чужой заголовок'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_author_delete_removes_ad(self):
        ad = create_ad(self.landlord, category=self.category, status='approved')
        url = reverse('ad-detail', kwargs={'pk': ad.pk})
        auth(self.client, self.landlord)

        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Ad.objects.filter(pk=ad.pk).exists())

    def test_non_author_delete_does_not_remove_ad(self):
        url = reverse('ad-detail', kwargs={'pk': self.approved.pk})
        auth(self.client, self.other)

        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertTrue(Ad.objects.filter(pk=self.approved.pk).exists())
