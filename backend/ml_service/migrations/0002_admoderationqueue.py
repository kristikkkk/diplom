"""Очередь проверки объявления одна-к-одному с результатами ML."""
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    """Таблица AdModerationQueue со связью OneToOne к ads.Ad."""

    dependencies = [
        ("ads", "0003_chat_message"),
        ("ml_service", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="AdModerationQueue",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("queued", "В очереди"),
                            ("processing", "Проверяется"),
                            ("checked", "Проверено"),
                            ("failed", "Ошибка"),
                        ],
                        default="queued",
                        max_length=20,
                        verbose_name="Статус проверки",
                    ),
                ),
                ("verdict_sfw", models.BooleanField(blank=True, null=True, verbose_name="SFW вердикт")),
                (
                    "normalized_prediction",
                    models.CharField(
                        choices=[
                            ("approved", "Безопасно"),
                            ("rejected", "Небезопасно"),
                            ("pending", "Нужна ручная проверка"),
                        ],
                        default="pending",
                        max_length=20,
                        verbose_name="Нормализованное решение",
                    ),
                ),
                ("confidence", models.FloatField(blank=True, null=True, verbose_name="Уверенность модели")),
                ("message", models.TextField(blank=True, verbose_name="Сообщение сервиса")),
                ("raw_response", models.JSONField(blank=True, default=dict, verbose_name="Сырой ответ сервиса")),
                ("is_uncertain", models.BooleanField(default=False, verbose_name="Модель сомневается")),
                ("error", models.TextField(blank=True, verbose_name="Текст ошибки")),
                ("checked_at", models.DateTimeField(blank=True, null=True, verbose_name="Время проверки")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "ad",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="moderation_queue",
                        to="ads.ad",
                        verbose_name="Объявление",
                    ),
                ),
            ],
            options={
                "verbose_name": "Очередь модерации объявления",
                "verbose_name_plural": "Очередь модерации объявлений",
                "ordering": ["-created_at"],
            },
        ),
    ]
