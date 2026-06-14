"""API-тесты выдачи изображений объявлений."""
from pathlib import Path

from django.conf import settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase


class AdImageViewAPITests(APITestCase):
    def test_missing_path_returns_400(self):
        url = reverse('ad-image')

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_nonexistent_file_returns_404(self):
        url = reverse('ad-image')

        response = self.client.get(url, {'path': 'ads_images/nonexistent.jpg'})

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_path_traversal_returns_400(self):
        url = reverse('ad-image')

        response = self.client.get(url, {'path': '../../etc/passwd'})

        self.assertIn(
            response.status_code,
            (status.HTTP_400_BAD_REQUEST, status.HTTP_404_NOT_FOUND),
        )

    def test_existing_file_returns_200(self):
        media_root = Path(settings.MEDIA_ROOT)
        media_root.mkdir(parents=True, exist_ok=True)
        rel_path = 'ads_images/test_image.txt'
        file_path = media_root / rel_path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text('test', encoding='utf-8')
        url = reverse('ad-image')

        response = self.client.get(url, {'path': rel_path})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        file_path.unlink(missing_ok=True)
