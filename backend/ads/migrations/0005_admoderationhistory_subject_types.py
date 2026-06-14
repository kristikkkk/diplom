"""Расширение журнала модерации: одна запись либо по объявлению, либо по отзыву."""
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    """Добавляет subject_type, nullable FK на отзыв и ограничение ровно одного субъекта."""

    dependencies = [
        ("ads", "0004_admoderationhistory"),
        ("reviews", "0002_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="admoderationhistory",
            name="subject_type",
            field=models.CharField(
                choices=[("ad", "Объявление"), ("review", "Отзыв")],
                default="ad",
                max_length=20,
                verbose_name="Тип сущности",
            ),
        ),
        migrations.AddField(
            model_name="admoderationhistory",
            name="review",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="moderation_history_entries",
                to="reviews.review",
                verbose_name="Отзыв",
            ),
        ),
        migrations.AlterField(
            model_name="admoderationhistory",
            name="ad",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="moderation_history",
                to="ads.ad",
                verbose_name="Объявление",
            ),
        ),
        migrations.AddConstraint(
            model_name="admoderationhistory",
            constraint=models.CheckConstraint(
                check=models.Q(ad__isnull=False, review__isnull=True)
                | models.Q(ad__isnull=True, review__isnull=False),
                name="ads_admoderationhistory_exactly_one_subject",
            ),
        ),
    ]
