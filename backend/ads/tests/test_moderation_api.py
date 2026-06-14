"""API-тесты ручной модерации объявлений и журнала решений."""
from unittest.mock import patch

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from ads.models import AdModerationHistory
from ml_service.models import AdModerationQueue
from tests.helpers import auth, create_ad, create_admin, create_category, create_landlord, create_tenant


class AdModerationActionAPITests(APITestCase):
    def setUp(self):
        self.admin = create_admin()
        self.tenant = create_tenant()
        self.landlord = create_landlord()
        self.category = create_category()
        self.ad = create_ad(self.landlord, category=self.category, status='pending')

    def test_admin_approve_ad_updates_status_and_history(self):
        auth(self.client, self.admin)
        url = reverse('approve-ad', kwargs={'pk': self.ad.pk})

        response = self.client.post(url, {}, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.ad.refresh_from_db()
        self.assertEqual(self.ad.status, 'approved')
        history = AdModerationHistory.objects.get(subject_type='ad', ad=self.ad)
        self.assertEqual(history.decision, 'approved')
        self.assertEqual(history.moderator_id, self.admin.id)

    def test_admin_reject_ad_with_reason(self):
        auth(self.client, self.admin)
        url = reverse('reject-ad', kwargs={'pk': self.ad.pk})

        response = self.client.post(url, {'reason': 'Нарушение правил'}, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.ad.refresh_from_db()
        self.assertEqual(self.ad.status, 'rejected')
        history = AdModerationHistory.objects.get(subject_type='ad', ad=self.ad)
        self.assertEqual(history.decision, 'rejected')
        self.assertEqual(history.reason, 'Нарушение правил')

    def test_tenant_cannot_approve_ad(self):
        auth(self.client, self.tenant)
        url = reverse('approve-ad', kwargs={'pk': self.ad.pk})

        response = self.client.post(url, {}, format='json')

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class AdModerationHistoryAPITests(APITestCase):
    def setUp(self):
        self.admin = create_admin()
        self.landlord = create_landlord()
        self.category = create_category()
        self.ad = create_ad(self.landlord, category=self.category, status='approved')
        AdModerationHistory.objects.create(
            subject_type='ad',
            ad=self.ad,
            moderator=self.admin,
            decision='approved',
        )
        self.url = reverse('ad-moderation-history')

    def test_admin_can_list_moderation_history(self):
        auth(self.client, self.admin)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data.get('results', response.data)
        self.assertGreaterEqual(len(data), 1)

    def test_history_filter_by_decision(self):
        auth(self.client, self.admin)

        response = self.client.get(self.url, {'decision': 'approved'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data.get('results', response.data)
        for item in data:
            self.assertEqual(item['decision'], 'approved')

    def test_tenant_cannot_access_history(self):
        tenant = create_tenant()
        auth(self.client, tenant)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class AdRetryModerationAPITests(APITestCase):
    @patch('ads.views.process_ad_moderation_task.delay')
    def test_admin_retry_moderation_enqueues_task(self, delay_mock):
        admin = create_admin()
        landlord = create_landlord()
        ad = create_ad(landlord, status='pending')
        auth(self.client, admin)
        url = reverse('retry-ad-moderation', kwargs={'pk': ad.pk})

        response = self.client.post(url, {}, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        queue_item = AdModerationQueue.objects.get(ad=ad)
        self.assertEqual(queue_item.status, 'queued')
        delay_mock.assert_called_once_with(queue_item.id)

    def test_tenant_cannot_retry_moderation(self):
        tenant = create_tenant()
        landlord = create_landlord()
        ad = create_ad(landlord, status='pending')
        auth(self.client, tenant)
        url = reverse('retry-ad-moderation', kwargs={'pk': ad.pk})

        response = self.client.post(url, {}, format='json')

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
