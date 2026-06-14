"""API-тесты регистрации, входа, профиля и обновления JWT."""
import uuid

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from tests.helpers import create_user
from users.models import User


class UserRegistrationAPITests(APITestCase):
    def test_register_success_returns_user_and_tokens(self):
        su = str(uuid.uuid4())[:8]
        url = reverse('user-register')
        payload = {
            'username': f'newuser_{su}',
            'email': f'new_{su}@example.com',
            'password': 'password123',
            'password_confirm': 'password123',
            'role': 'tenant',
            'phone_number': '+79001234567',
        }

        response = self.client.post(url, payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('user', response.data)
        self.assertIn('tokens', response.data)
        self.assertIn('access', response.data['tokens'])
        self.assertIn('refresh', response.data['tokens'])
        self.assertEqual(response.data['user']['email'], payload['email'])

    def test_register_password_mismatch_returns_400(self):
        su = str(uuid.uuid4())[:8]
        url = reverse('user-register')
        payload = {
            'username': f'user_{su}',
            'email': f'mismatch_{su}@example.com',
            'password': 'password123',
            'password_confirm': 'otherpass',
            'role': 'tenant',
        }

        response = self.client.post(url, payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_duplicate_email_returns_400(self):
        user = create_user()
        url = reverse('user-register')
        payload = {
            'username': 'another_name',
            'email': user.email,
            'password': 'password123',
            'password_confirm': 'password123',
            'role': 'tenant',
        }

        response = self.client.post(url, payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class UserLoginAPITests(APITestCase):
    def test_login_success_returns_tokens(self):
        user = create_user(email='login_ok@example.com')
        user.set_password('secretpass99')
        user.save()
        url = reverse('user-login')

        response = self.client.post(
            url,
            {'email': 'login_ok@example.com', 'password': 'secretpass99'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('tokens', response.data)
        self.assertEqual(response.data['user']['email'], 'login_ok@example.com')

    def test_login_wrong_password_returns_400(self):
        user = create_user()
        url = reverse('user-login')

        response = self.client.post(
            url,
            {'email': user.email, 'password': 'wrongpassword'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class UserProfileAPITests(APITestCase):
    def test_profile_get_requires_authentication(self):
        url = reverse('user-profile')

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_profile_get_and_patch(self):
        user = create_user(phone_number='+79001111111')
        self.client.force_authenticate(user=user)
        url = reverse('user-profile')

        get_resp = self.client.get(url)
        self.assertEqual(get_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(get_resp.data['phone_number'], '+79001111111')

        patch_resp = self.client.patch(
            url,
            {'phone_number': '+79002222222'},
            format='json',
        )
        self.assertEqual(patch_resp.status_code, status.HTTP_200_OK)
        user.refresh_from_db()
        self.assertEqual(user.phone_number, '+79002222222')


class TokenRefreshAPITests(APITestCase):
    def test_token_refresh_returns_new_access(self):
        su = str(uuid.uuid4())[:8]
        register_url = reverse('user-register')
        reg = self.client.post(
            register_url,
            {
                'username': f'refresh_{su}',
                'email': f'refresh_{su}@example.com',
                'password': 'password123',
                'password_confirm': 'password123',
                'role': 'tenant',
            },
            format='json',
        )
        refresh_token = reg.data['tokens']['refresh']
        refresh_url = reverse('token_refresh')

        response = self.client.post(
            refresh_url,
            {'refresh': refresh_token},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
