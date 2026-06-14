"""Заглушки сигналов pre_save (модерация выполняется через очередь и Celery)."""
from django.db.models.signals import pre_save
from django.dispatch import receiver


@receiver(pre_save, sender='ads.Ad')
def moderate_ad_content(sender, instance, **kwargs):
    """Зарезервировано; синхронная модерация отключена в пользу очереди."""
    return


@receiver(pre_save, sender='reviews.Review')
def moderate_review_content(sender, instance, **kwargs):
    """Зарезервировано; проверка отзыва выполняется задачей process_review_moderation_task."""
    return
