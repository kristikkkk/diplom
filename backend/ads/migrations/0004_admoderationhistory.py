# Generated manually
"""Журнал решений модераторов по объявлениям с снимком полей проверки ИИ."""

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    """Таблица AdModerationHistory привязана к объявлению и модератору."""

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('ads', '0003_chat_message'),
    ]

    operations = [
        migrations.CreateModel(
            name='AdModerationHistory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('decision', models.CharField(choices=[('approved', 'Одобрено'), ('rejected', 'Отклонено')], max_length=20, verbose_name='Решение')),
                ('reason', models.TextField(blank=True, verbose_name='Причина отклонения')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Время решения')),
                ('ai_status', models.CharField(blank=True, max_length=20, null=True, verbose_name='Статус проверки ИИ')),
                ('ai_normalized_prediction', models.CharField(blank=True, max_length=20, null=True, verbose_name='Нормализованное решение ИИ')),
                ('ai_confidence', models.FloatField(blank=True, null=True, verbose_name='Уверенность ИИ')),
                ('ai_verdict_sfw', models.BooleanField(blank=True, null=True, verbose_name='SFW вердикт ИИ')),
                ('ai_message', models.TextField(blank=True, verbose_name='Сообщение ИИ')),
                ('ai_error', models.TextField(blank=True, verbose_name='Ошибка ИИ')),
                ('ai_checked_at', models.DateTimeField(blank=True, null=True, verbose_name='Время проверки ИИ')),
                ('ad', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='moderation_history', to='ads.ad', verbose_name='Объявление')),
                ('moderator', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='ad_moderation_decisions', to=settings.AUTH_USER_MODEL, verbose_name='Модератор')),
            ],
            options={
                'verbose_name': 'История модерации объявления',
                'verbose_name_plural': 'История модерации объявлений',
                'ordering': ['-created_at'],
            },
        ),
    ]
