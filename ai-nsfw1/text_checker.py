"""
Проверка текста на NSFW только через модель transformers.
Эвристики не используются.
"""
import logging
import os
import re
from typing import Tuple

try:
    import torch
except Exception:  # pragma: no cover
    torch = None

try:
    from transformers import AutoModelForSequenceClassification, AutoTokenizer
except Exception:  # pragma: no cover
    AutoModelForSequenceClassification = None
    AutoTokenizer = None

TEXT_NSFW_MODEL = os.getenv("TEXT_NSFW_MODEL", "cointegrated/rubert-tiny-toxicity")
TEXT_NSFW_MAX_LENGTH = int(os.getenv("TEXT_NSFW_MAX_LENGTH", "256"))
TEXT_NSFW_POSITIVE_CLASS_ID = int(os.getenv("TEXT_NSFW_POSITIVE_CLASS_ID", "1"))
TEXT_NSFW_MULTI_LABEL = os.getenv("TEXT_NSFW_MULTI_LABEL", "auto").strip().lower()
TEXT_NSFW_LOG_LEVEL = os.getenv("TEXT_NSFW_LOG_LEVEL", "INFO").upper()
TEXT_NSFW_LOG_TEXT_LIMIT = int(os.getenv("TEXT_NSFW_LOG_TEXT_LIMIT", "80"))

POSITIVE_LABEL_HINTS = tuple(
    item.strip().lower()
    for item in os.getenv(
        "TEXT_NSFW_POSITIVE_HINTS",
        "nsfw,unsafe,toxic,obscene,obscenity,sexual,porn,adult,explicit,inappropriate,dangerous,insult,threat",
    ).split(",")
    if item.strip()
)
NEGATIVE_LABEL_HINTS = tuple(
    item.strip().lower()
    for item in os.getenv(
        "TEXT_NSFW_NEGATIVE_HINTS",
        "sfw,safe,clean,neutral,non-toxic,non toxic,appropriate,benign",
    ).split(",")
    if item.strip()
)

POSITIVE_LABEL_WEIGHTS = {
    "dangerous": 1.0,
    "obscenity": 0.95,
    "obscene": 0.95,
    "sexual": 0.9,
    "porn": 1.0,
    "nsfw": 1.0,
    "adult": 0.9,
    "explicit": 0.9,
    "toxic": 0.65,
    "insult": 0.55,
    "threat": 0.7,
}

_TEXT_PIPELINE_ERROR: str | None = None
_TEXT_TOKENIZER = None
_TEXT_MODEL = None
_TEXT_MODEL_DEVICE = "cpu"

logger = logging.getLogger("text_checker")
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter("[text-checker] %(levelname)s %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
logger.setLevel(getattr(logging, TEXT_NSFW_LOG_LEVEL, logging.INFO))
logger.propagate = False


def _bounded(value: float, minimum: float = 0.0, maximum: float = 1.0) -> float:
    return max(minimum, min(maximum, value))


def _short_for_log(text: str, limit: int = TEXT_NSFW_LOG_TEXT_LIMIT) -> str:
    compact = re.sub(r"\s+", " ", text).strip()
    if len(compact) <= limit:
        return compact
    return compact[: limit - 3] + "..."


def _normalize_text(text: str) -> str:
    normalized = text.lower()
    normalized = re.sub(r"[\s_\-]{2,}", " ", normalized)
    return normalized.strip()


def _resolve_model_device() -> str:
    preferred = os.getenv("TEXT_NSFW_DEVICE", "auto").strip().lower()
    if preferred == "cpu":
        return "cpu"
    if preferred.startswith("cuda"):
        parts = preferred.split(":", maxsplit=1)
        if len(parts) == 2 and parts[1].isdigit():
            return f"cuda:{parts[1]}"
        return "cuda:0"
    if preferred.isdigit():
        return f"cuda:{preferred}"
    if torch is not None and torch.cuda.is_available():
        return "cuda:0"
    return "cpu"


def _get_text_model():
    global _TEXT_TOKENIZER, _TEXT_MODEL, _TEXT_MODEL_DEVICE, _TEXT_PIPELINE_ERROR

    if _TEXT_TOKENIZER is not None and _TEXT_MODEL is not None:
        logger.debug("Используем уже загруженную модель '%s' на %s", TEXT_NSFW_MODEL, _TEXT_MODEL_DEVICE)
        return _TEXT_TOKENIZER, _TEXT_MODEL, _TEXT_MODEL_DEVICE

    if _TEXT_PIPELINE_ERROR is not None:
        logger.error("Модель недоступна: %s", _TEXT_PIPELINE_ERROR)
        return None

    if AutoTokenizer is None or AutoModelForSequenceClassification is None or torch is None:
        _TEXT_PIPELINE_ERROR = "transformers/torch not available"
        logger.error("Transformers/Torch недоступны.")
        return None

    try:
        _TEXT_TOKENIZER = AutoTokenizer.from_pretrained(TEXT_NSFW_MODEL)
        _TEXT_MODEL = AutoModelForSequenceClassification.from_pretrained(TEXT_NSFW_MODEL)
        _TEXT_MODEL_DEVICE = _resolve_model_device()
        _TEXT_MODEL.to(_TEXT_MODEL_DEVICE)
        _TEXT_MODEL.eval()
        logger.info("Текстовая модель загружена: model='%s' device='%s'", TEXT_NSFW_MODEL, _TEXT_MODEL_DEVICE)
    except Exception as exc:
        _TEXT_PIPELINE_ERROR = str(exc)
        logger.exception("Ошибка загрузки текстовой модели '%s': %s", TEXT_NSFW_MODEL, exc)
        return None

    return _TEXT_TOKENIZER, _TEXT_MODEL, _TEXT_MODEL_DEVICE


def _is_multilabel_model(id2label: dict[int, str] | None, problem_type: str | None) -> bool:
    if TEXT_NSFW_MULTI_LABEL in {"1", "true", "yes"}:
        return True
    if TEXT_NSFW_MULTI_LABEL in {"0", "false", "no"}:
        return False
    if str(problem_type or "").lower() == "multi_label_classification":
        return True
    labels = [str(v).lower() for v in (id2label or {}).values()]
    return any("non-toxic" in label or "non toxic" in label for label in labels) and any(
        any(key in label for key in ("dangerous", "obscenity", "insult", "threat"))
        for label in labels
    )


def _positive_weight_for_label(label: str) -> float:
    label = label.lower()
    matched = [weight for key, weight in POSITIVE_LABEL_WEIGHTS.items() if key in label]
    if matched:
        return max(matched)
    if any(hint in label for hint in POSITIVE_LABEL_HINTS):
        return 0.75
    return 0.0


def _extract_model_nsfw_probability(probs: list[float], id2label: dict[int, str] | None) -> float | None:
    if not probs:
        return None

    nsfw_scores = []
    safe_scores = []
    id2label = id2label or {}

    for idx, score in enumerate(probs):
        label = str(id2label.get(idx, "")).lower()
        weight = _positive_weight_for_label(label)
        if weight > 0.0:
            nsfw_scores.append(score * weight)
        if any(hint in label for hint in NEGATIVE_LABEL_HINTS):
            safe_scores.append(score)

    if nsfw_scores:
        nsfw_prob = _bounded(max(nsfw_scores))
        if safe_scores:
            nsfw_prob = _bounded(nsfw_prob - 0.25 * max(safe_scores))
        return nsfw_prob
    if safe_scores:
        return _bounded(1.0 - max(safe_scores))
    if 0 <= TEXT_NSFW_POSITIVE_CLASS_ID < len(probs):
        return _bounded(float(probs[TEXT_NSFW_POSITIVE_CLASS_ID]))
    return None


def check_text_nsfw(
    text: str,
    keywords: list[str] | None = None,
    threshold: float = 0.6,
) -> Tuple[bool, float]:
    """
    Возвращает (is_sfw, confidence_sfw).
    Решение принимается только моделью.
    При недоступной модели используется fail-closed: NSFW.
    """
    del keywords  # совместимость сигнатуры

    if not text or not text.strip():
        logger.debug("Пустой текст -> SFW=1.0")
        return True, 1.0

    normalized_text = _normalize_text(text)
    logger.info(
        "Проверка текста: input='%s' normalized='%s' threshold=%.2f",
        _short_for_log(text),
        _short_for_log(normalized_text),
        threshold,
    )

    model_bundle = _get_text_model()
    if model_bundle is None:
        logger.error("Нет доступной модели: fail-closed -> NSFW")
        return False, 0.0

    try:
        tokenizer, model, device = model_bundle
        encoded = tokenizer(
            normalized_text,
            truncation=True,
            max_length=TEXT_NSFW_MAX_LENGTH,
            return_tensors="pt",
        )
        encoded = {k: v.to(device) for k, v in encoded.items()}
        model_config = getattr(model, "config", None)
        id2label = getattr(model_config, "id2label", None)
        problem_type = getattr(model_config, "problem_type", None)
        is_multilabel = _is_multilabel_model(id2label, problem_type)

        with torch.no_grad():
            logits = model(**encoded).logits[0]
            if is_multilabel:
                probs = torch.sigmoid(logits).detach().cpu().tolist()
            else:
                probs = torch.softmax(logits, dim=-1).detach().cpu().tolist()

        model_nsfw_prob = _extract_model_nsfw_probability(probs, id2label)
        logger.debug(
            "Модель: multi_label=%s labels=%s probs=%s model_nsfw_prob=%s",
            is_multilabel,
            id2label,
            [round(float(p), 4) for p in probs],
            None if model_nsfw_prob is None else round(float(model_nsfw_prob), 4),
        )
        if model_nsfw_prob is None:
            logger.error("Не удалось извлечь NSFW score из выходов модели: fail-closed -> NSFW")
            return False, 0.0
    except Exception:
        logger.exception("Ошибка инференса текстовой модели: fail-closed -> NSFW")
        return False, 0.0

    final_nsfw_prob = _bounded(model_nsfw_prob)
    confidence_sfw = _bounded(1.0 - final_nsfw_prob)
    is_sfw = confidence_sfw >= _bounded(threshold)
    logger.info(
        "Итог: sfw=%s sfw_conf=%.4f nsfw_prob=%.4f threshold=%.2f",
        is_sfw,
        confidence_sfw,
        final_nsfw_prob,
        threshold,
    )
    return is_sfw, confidence_sfw
