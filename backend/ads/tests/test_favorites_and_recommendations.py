"""API-тесты избранного и рекомендаций."""
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from ads.models import Favorite
from tests.helpers import auth, create_ad, create_category, create_landlord, create_tenant


class FavoritesAPITests(APITestCase):
    def setUp(self):
        self.user = create_tenant()
        self.landlord = create_landlord()
        self.category = create_category()
        self.ad = create_ad(self.landlord, category=self.category, status='approved')
        self.list_url = reverse('favorite-list')
        self.remove_url = reverse('remove-favorite')

    def test_add_favorite_requires_auth(self):
        response = self.client.post(self.list_url, {'ad_id': self.ad.id}, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_add_favorite_creates_record(self):
        auth(self.client, self.user)

        response = self.client.post(self.list_url, {'ad_id': self.ad.id}, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Favorite.objects.filter(user=self.user, ad=self.ad).exists())

    def test_add_duplicate_favorite_returns_200(self):
        auth(self.client, self.user)
        Favorite.objects.create(user=self.user, ad=self.ad)

        response = self.client.post(self.list_url, {'ad_id': self.ad.id}, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_list_favorites_returns_only_own(self):
        other = create_tenant()
        other_ad = create_ad(self.landlord, category=self.category, status='approved')
        Favorite.objects.create(user=self.user, ad=self.ad)
        Favorite.objects.create(user=other, ad=other_ad)
        auth(self.client, self.user)

        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data.get('results', response.data)
        ad_ids = [item['ad']['id'] if isinstance(item.get('ad'), dict) else item.get('ad_id') for item in data]
        if not ad_ids and data:
            ad_ids = [item.get('ad', {}).get('id') for item in data if item.get('ad')]
        self.assertEqual(len(data), 1)

    def test_remove_favorite(self):
        Favorite.objects.create(user=self.user, ad=self.ad)
        auth(self.client, self.user)

        response = self.client.delete(
            self.remove_url,
            {'ad_id': self.ad.id},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(Favorite.objects.filter(user=self.user, ad=self.ad).exists())

    def test_remove_missing_favorite_returns_404(self):
        auth(self.client, self.user)

        response = self.client.delete(
            self.remove_url,
            {'ad_id': self.ad.id},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class RecommendationsAPITests(APITestCase):
    def setUp(self):
        self.user = create_tenant()
        self.landlord = create_landlord()
        self.category = create_category()
        self.url = reverse('recommendations')

    def test_recommendations_without_favorites_returns_popular(self):
        popular = create_ad(
            self.landlord,
            category=self.category,
            status='approved',
            views_count=100,
        )
        create_ad(
            self.landlord,
            category=self.category,
            status='approved',
            views_count=1,
        )
        auth(self.client, self.user)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data), 1)
        ids = [item['id'] for item in response.data]
        self.assertEqual(ids[0], popular.id)

    def test_recommendations_with_favorites_same_category(self):
        fav_ad = create_ad(
            self.landlord,
            category=self.category,
            status='approved',
        )
        similar = create_ad(
            self.landlord,
            category=self.category,
            status='approved',
            title='Похожее',
        )
        Favorite.objects.create(user=self.user, ad=fav_ad)
        auth(self.client, self.user)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = [item['id'] for item in response.data]
        self.assertIn(similar.id, ids)
        self.assertNotIn(fav_ad.id, ids)
