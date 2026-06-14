"""HTTP-клиент к внешнему сервису модерации контента (ML_CHECK_URL)."""
import json
import logging
import mimetypes
import urllib.error
import urllib.request
import uuid
from pathlib import Path
from typing import Optional, Tuple

from django.conf import settings

logger = logging.getLogger('ml_service')

class ContentModerationService:
    """Отправляет текст и опционально изображение на endpoint и нормализует ответ."""

    def __init__(self):
        """Читает URL и таймаут из настроек Django."""
        self.check_url = getattr(settings, "ML_CHECK_URL", "http://127.0.0.1:8091/check")
        self.timeout = float(getattr(settings, "ML_CHECK_TIMEOUT", 60))

    def _normalize_prediction(self, prediction: object) -> str:
        """Приводит строковый вердикт сервиса к одному из approved/rejected/pending."""
        value = str(prediction or "").strip().lower()
        mapping = {
            "approved": "approved",
            "approve": "approved",
            "ok": "approved",
            "clean": "approved",
            "safe": "approved",
            "rejected": "rejected",
            "reject": "rejected",
            "spam": "rejected",
            "blocked": "rejected",
            "unsafe": "rejected",
            "pending": "pending",
            "review": "pending",
            "manual_review": "pending",
        }
        return mapping.get(value, "pending")

    def _parse_confidence(self, data: dict) -> float:
        """Извлекает числовую уверенность из типичных ключей ответа или 0.5 по умолчанию."""
        raw_confidence = (
            data.get("sfw_confidence")
            or data.get("confidence")
            or data.get("probability")
            or data.get("score")
            or 0.5
        )
        try:
            return float(raw_confidence)
        except (TypeError, ValueError):
            return 0.5

    def _parse_response(self, data: dict) -> dict:
        """Строит единый словарь: sfw-флаг, нормализованный класс, confidence, сообщение."""
        sfw_value = data.get("sfw")
        normalized_prediction = "pending"
        if isinstance(sfw_value, bool):
            normalized_prediction = "approved" if sfw_value else "rejected"
        else:
            raw_prediction = (
                data.get("prediction")
                or data.get("status")
                or data.get("result")
                or data.get("label")
                or data.get("class")
            )
            normalized_prediction = self._normalize_prediction(raw_prediction)

        return {
            "sfw": sfw_value if isinstance(sfw_value, bool) else None,
            "normalized_prediction": normalized_prediction,
            "confidence": self._parse_confidence(data),
            "message": str(data.get("message") or data.get("detail") or "").strip(),
            "raw_response": data,
        }

    def _build_request_payload(self, text: str, image_path: Optional[str]) -> Tuple[bytes, str]:
        """Собирает multipart/form-data тело POST-запроса для сервиса проверки."""
        boundary = f"----cursor-boundary-{uuid.uuid4().hex}"
        body = bytearray()

        def add_text_field(name: str, value: str) -> None:
            """Добавляет текстовое поле multipart."""
            body.extend(f"--{boundary}\r\n".encode())
            body.extend(
                f'Content-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'.encode("utf-8")
            )

        if text:
            add_text_field("text", text)

        if image_path:
            path = Path(image_path)
            if path.exists() and path.is_file():
                content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
                body.extend(f"--{boundary}\r\n".encode())
                body.extend(
                    (
                        f'Content-Disposition: form-data; name="image"; '
                        f'filename="{path.name}"\r\n'
                    ).encode("utf-8")
                )
                body.extend(f"Content-Type: {content_type}\r\n\r\n".encode("utf-8"))
                body.extend(path.read_bytes())
                body.extend(b"\r\n")
            else:
                logger.warning("Файл изображения не найден: %s", image_path)

        body.extend(f"--{boundary}--\r\n".encode())
        return bytes(body), f"multipart/form-data; boundary={boundary}"

    def predict(self, text: str, image_path: Optional[str] = None) -> Tuple[str, float]:
        """Вызывает predict_detailed и возвращает только пару (вердикт, уверенность)."""
        result = self.predict_detailed(text=text, image_path=image_path)
        return result["normalized_prediction"], result["confidence"]

    def predict_detailed(self, text: str, image_path: Optional[str] = None) -> dict:
        """POST на ML_CHECK_URL; при ошибке сети/JSON возвращает заглушку с полем error."""
        if not text and not image_path:
            return {
                "sfw": None,
                "normalized_prediction": "pending",
                "confidence": 0.5,
                "message": "Нет данных для проверки.",
                "raw_response": {},
                "error": "",
            }

        try:
            payload, content_type = self._build_request_payload(text=text, image_path=image_path)
            request = urllib.request.Request(
                self.check_url,
                data=payload,
                headers={"Content-Type": content_type},
                method="POST",
            )
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                body = response.read().decode("utf-8")
                max_raw_log = 8000
                if len(body) > max_raw_log:
                    logger.info(
                        "Сырой ответ сервиса модерации (%s символов, показано %s): %s…",
                        len(body),
                        max_raw_log,
                        body[:max_raw_log],
                    )
                else:
                    logger.info("Сырой ответ сервиса модерации: %s", body)
                data = json.loads(body) if body else {}

            parsed = self._parse_response(data)
            parsed["error"] = ""
            return parsed
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError) as error:
            logger.error("Ошибка запроса к сервису модерации: %s", error)
            return {
                "sfw": None,
                "normalized_prediction": "pending",
                "confidence": 0.5,
                "message": "",
                "raw_response": {},
                "error": str(error),
            }

    def is_spam(self, text: str) -> bool:
        """Устаревшая эвристика: спам если вердикт rejected и confidence > 0.7."""
        prediction, confidence = self.predict(text)
        return prediction == "rejected" and confidence > 0.7


# Глобальный экземпляр сервиса
moderation_service = ContentModerationService()
