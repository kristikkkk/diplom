"""Очередь проверки отзывов после появления приложения reviews."""
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    """Таблица ReviewModerationQueue с OneToOne к reviews.Review."""

    dependencies = [
        ("ml_service", "0002_admoderationqueue"),
        ("reviews", "0002_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="ReviewModerationQueue",
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
                    "review",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="moderation_queue",
                        to="reviews.review",
                        verbose_name="Отзыв",
                    ),
                ),
            ],
            options={
                "verbose_name": "Очередь модерации отзыва",
                "verbose_name_plural": "Очередь модерации отзывов",
                "ordering": ["-created_at"],
            },
        ),
    ]
