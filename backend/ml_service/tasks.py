"""Celery-задачи асинхронной проверки объявлений и отзывов внешним ML-сервисом."""
import logging

from celery import shared_task
from django.utils import timezone

from .models import AdModerationQueue, MLModel, PredictionLog, ReviewModerationQueue
from .services import moderation_service

logger = logging.getLogger("ml_service")


def _get_ad_image_path(ad_instance):
    """Возвращает путь к основному или первому файлу изображения объявления для отправки в ML."""
    primary_image = ad_instance.images.filter(is_primary=True).first()
    if not primary_image:
        primary_image = ad_instance.images.first()
    if primary_image and primary_image.image:
        return primary_image.image.path
    return None


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def process_ad_moderation_task(self, queue_id: int):
    """Асинхронно вызывает ML для объявления, обновляет AdModerationQueue и пишет PredictionLog."""
    try:
        queue_item = AdModerationQueue.objects.select_related("ad").get(id=queue_id)
    except AdModerationQueue.DoesNotExist:
        logger.warning("Задача модерации: запись очереди %s не найдена", queue_id)
        return {"queue_id": queue_id, "skipped": True, "reason": "queue_not_found"}

    queue_item.status = "processing"
    queue_item.error = ""
    queue_item.save(update_fields=["status", "error", "updated_at"])

    ad_instance = queue_item.ad
    text_to_analyze = f"{ad_instance.title} {ad_instance.description}"
    image_path = _get_ad_image_path(ad_instance)

    result = moderation_service.predict_detailed(text=text_to_analyze, image_path=image_path)
    confidence = result["confidence"]
    normalized_prediction = result["normalized_prediction"]
    is_uncertain = confidence < 0.75

    queue_item.verdict_sfw = result["sfw"]
    queue_item.normalized_prediction = normalized_prediction
    queue_item.confidence = confidence
    queue_item.message = result["message"]
    queue_item.raw_response = result["raw_response"]
    queue_item.is_uncertain = is_uncertain
    queue_item.checked_at = timezone.now()

    if result["error"]:
        queue_item.status = "failed"
        queue_item.error = result["error"]
    else:
        queue_item.status = "checked"
        queue_item.error = ""

    queue_item.save(
        update_fields=[
            "status",
            "verdict_sfw",
            "normalized_prediction",
            "confidence",
            "message",
            "raw_response",
            "is_uncertain",
            "error",
            "checked_at",
            "updated_at",
        ]
    )

    ml_model = MLModel.objects.filter(model_type="content_moderation", is_active=True).first()
    if ml_model:
        PredictionLog.objects.create(
            model=ml_model,
            content_type="ad",
            content_id=ad_instance.id,
            text=text_to_analyze,
            prediction=normalized_prediction,
            confidence=confidence,
        )

    return {
        "queue_id": queue_item.id,
        "ad_id": ad_instance.id,
        "status": queue_item.status,
        "normalized_prediction": normalized_prediction,
    }


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def process_review_moderation_task(self, queue_id: int):
    """Асинхронно проверяет текст отзыва и сохраняет результат в ReviewModerationQueue."""
    try:
        queue_item = ReviewModerationQueue.objects.select_related("review").get(id=queue_id)
    except ReviewModerationQueue.DoesNotExist:
        logger.warning("Задача модерации отзыва: запись очереди %s не найдена", queue_id)
        return {"queue_id": queue_id, "skipped": True, "reason": "queue_not_found"}

    queue_item.status = "processing"
    queue_item.error = ""
    queue_item.save(update_fields=["status", "error", "updated_at"])

    review_instance = queue_item.review
    text_to_analyze = review_instance.text

    result = moderation_service.predict_detailed(text=text_to_analyze, image_path=None)
    confidence = result["confidence"]
    normalized_prediction = result["normalized_prediction"]
    is_uncertain = confidence < 0.75

    queue_item.verdict_sfw = result["sfw"]
    queue_item.normalized_prediction = normalized_prediction
    queue_item.confidence = confidence
    queue_item.message = result["message"]
    queue_item.raw_response = result["raw_response"]
    queue_item.is_uncertain = is_uncertain
    queue_item.checked_at = timezone.now()

    if result["error"]:
        queue_item.status = "failed"
        queue_item.error = result["error"]
    else:
        queue_item.status = "checked"
        queue_item.error = ""

    queue_item.save(
        update_fields=[
            "status",
            "verdict_sfw",
            "normalized_prediction",
            "confidence",
            "message",
            "raw_response",
            "is_uncertain",
            "error",
            "checked_at",
            "updated_at",
        ]
    )

    ml_model = MLModel.objects.filter(model_type="content_moderation", is_active=True).first()
    if ml_model:
        PredictionLog.objects.create(
            model=ml_model,
            content_type="review",
            content_id=review_instance.id,
            text=text_to_analyze,
            prediction=normalized_prediction,
            confidence=confidence,
        )

    return {
        "queue_id": queue_item.id,
        "review_id": review_instance.id,
        "status": queue_item.status,
        "normalized_prediction": normalized_prediction,
    }
