"""API-тесты чатов и сообщений."""
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from ads.models import Chat, Message
from tests.helpers import auth, create_ad, create_category, create_landlord, create_tenant


class ChatAPITests(APITestCase):
    def setUp(self):
        self.landlord = create_landlord()
        self.tenant = create_tenant()
        self.other = create_tenant()
        self.category = create_category()
        self.ad = create_ad(self.landlord, category=self.category, status='approved')
        self.list_url = reverse('chat-list')

    def test_tenant_creates_chat_by_ad_id(self):
        auth(self.client, self.tenant)

        response = self.client.post(
            self.list_url,
            {'ad_id': self.ad.id},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        chat = Chat.objects.get(ad=self.ad, tenant=self.tenant, landlord=self.landlord)
        self.assertEqual(chat.id, response.data['id'])

    def test_landlord_create_without_tenant_id_returns_400(self):
        auth(self.client, self.landlord)

        response = self.client.post(
            self.list_url,
            {'ad_id': self.ad.id},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_chat_list_visible_only_to_participants(self):
        chat = Chat.objects.create(ad=self.ad, tenant=self.tenant, landlord=self.landlord)
        auth(self.client, self.tenant)
        resp_participant = self.client.get(self.list_url)
        auth(self.client, self.other)
        resp_other = self.client.get(self.list_url)

        self.assertEqual(resp_participant.status_code, status.HTTP_200_OK)
        ids_participant = [c['id'] for c in resp_participant.data.get('results', resp_participant.data)]
        ids_other = [c['id'] for c in resp_other.data.get('results', resp_other.data)]
        self.assertIn(chat.id, ids_participant)
        self.assertNotIn(chat.id, ids_other)

    def test_send_message_in_chat(self):
        chat = Chat.objects.create(ad=self.ad, tenant=self.tenant, landlord=self.landlord)
        auth(self.client, self.tenant)
        url = reverse('message-list', kwargs={'chat_id': chat.id})

        response = self.client.post(
            url,
            {'text': 'Здравствуйте'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Message.objects.filter(chat=chat, text='Здравствуйте').exists())

    def test_outsider_cannot_send_message(self):
        chat = Chat.objects.create(ad=self.ad, tenant=self.tenant, landlord=self.landlord)
        auth(self.client, self.other)
        url = reverse('message-list', kwargs={'chat_id': chat.id})

        response = self.client.post(
            url,
            {'text': 'Взлом'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_mark_messages_read(self):
        chat = Chat.objects.create(ad=self.ad, tenant=self.tenant, landlord=self.landlord)
        Message.objects.create(chat=chat, sender=self.landlord, text='Ответ', is_read=False)
        auth(self.client, self.tenant)
        url = reverse('mark-messages-read', kwargs={'chat_id': chat.id})

        response = self.client.post(url, {}, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(
            Message.objects.filter(chat=chat, sender=self.landlord, is_read=False).exists()
        )
