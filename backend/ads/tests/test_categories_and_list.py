"""API-тесты категорий и списка объявлений."""
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from tests.helpers import auth, create_ad, create_admin, create_category, create_landlord


class CategoryListAPITests(APITestCase):
    def test_categories_list_returns_only_active(self):
        active = create_category(name='Активная')
        create_category(name='Неактивная', is_active=False)
        url = reverse('category-list')

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data.get('results', response.data)
        names = [c['name'] for c in data]
        self.assertIn(active.name, names)
        self.assertNotIn('Неактивная', names)


class AdListAPITests(APITestCase):
    def setUp(self):
        self.landlord = create_landlord()
        self.category = create_category()
        self.approved = create_ad(
            self.landlord, category=self.category, status='approved', title='Одобренное'
        )
        self.pending = create_ad(
            self.landlord, category=self.category, status='pending', title='На модерации'
        )
        self.url = reverse('ad-list')

    def test_anonymous_list_shows_only_approved(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data.get('results', response.data)
        ids = [item['id'] for item in data]
        self.assertIn(self.approved.id, ids)
        self.assertNotIn(self.pending.id, ids)

    def test_admin_can_filter_by_pending_status(self):
        admin = create_admin()
        auth(self.client, admin)

        response = self.client.get(self.url, {'status': 'pending'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data.get('results', response.data)
        ids = [item['id'] for item in data]
        self.assertIn(self.pending.id, ids)

    def test_filter_by_category(self):
        other_cat = create_category(name='Другая')
        other_ad = create_ad(
            self.landlord, category=other_cat, status='approved', title='Другое'
        )

        response = self.client.get(self.url, {'category': self.category.id})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data.get('results', response.data)
        ids = [item['id'] for item in data]
        self.assertIn(self.approved.id, ids)
        self.assertNotIn(other_ad.id, ids)

    def test_search_by_title(self):
        response = self.client.get(self.url, {'search': 'Одобренное'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data.get('results', response.data)
        titles = [item['title'] for item in data]
        self.assertIn('Одобренное', titles)

    def test_ordering_by_price(self):
        cheap = create_ad(
            self.landlord,
            category=self.category,
            status='approved',
            title='Дешёвое',
            price='1000.00',
        )
        response = self.client.get(self.url, {'ordering': 'price'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data.get('results', response.data)
        prices = [item['id'] for item in data]
        self.assertIn(cheap.id, prices)
