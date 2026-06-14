"""
Бэкенд API: приём запросов (фото, текст или оба), проверка через модель SFW/NSFW, ответ клиенту.
Запуск: uvicorn backend.main:app --reload
"""
import io
import os
from pathlib import Path

from fastapi import FastAPI, File, Form, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from PIL import Image

# Импорты из корня проекта
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from inference import load_classifier
from text_checker import check_text_nsfw


app = FastAPI(title="SFW/NSFW Check API", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# Глобальный классификатор (загружается при старте)
CLASSIFIER = None
CHECKPOINT = Path(__file__).resolve().parent.parent / "checkpoints" / "sfw_nsfw_model.pt"
TEXT_SFW_THRESHOLD = float(os.getenv("TEXT_SFW_THRESHOLD", "0.6"))


def get_classifier():
    global CLASSIFIER
    if CLASSIFIER is None:
        if not CHECKPOINT.exists():
            raise HTTPException(
                status_code=503,
                detail="Модель не найдена. Обучите модель: python train.py",
            )
        CLASSIFIER = load_classifier(str(CHECKPOINT))
    return CLASSIFIER


class CheckResponse(BaseModel):
    sfw: bool
    sfw_confidence: float
    message: str = ""


@app.post("/check", response_model=CheckResponse)
async def check_content(
    image: UploadFile | None = File(None, description="Изображение для проверки"),
    text: str | None = Form(None, description="Текст для проверки"),
):
    """
    Проверка контента на SFW/NSFW.
    Можно передать только изображение, только текст или оба.
    Ответ: sfw (True = безопасно), confidence (уверенность в SFW от 0 до 1).
    """
    has_image = image is not None and image.filename
    has_text = text is not None and text.strip() != ""

    if not has_image and not has_text:
        raise HTTPException(status_code=400, detail="Укажите image и/или text")

    confidence_sfw = 1.0
    is_sfw = True

    if has_image:
        try:
            data = await image.read()
            img = Image.open(io.BytesIO(data)).convert("RGB")
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Не удалось прочитать изображение: {e}")
        classifier = get_classifier()
        img_sfw, img_conf = classifier.predict_image(img)
        is_sfw = img_sfw
        confidence_sfw = img_conf

    if has_text:
        text_sfw, text_conf = check_text_nsfw(text or "", threshold=TEXT_SFW_THRESHOLD)
        if has_image:
            # Комбинируем: если хотя бы один источник NSFW — считаем NSFW; уверенность — минимум
            is_sfw = is_sfw and text_sfw
            confidence_sfw = min(confidence_sfw, text_conf)
        else:
            is_sfw = text_sfw
            confidence_sfw = text_conf

    msg = "Контент безопасен (SFW)." if is_sfw else "Обнаружен контент для взрослых (NSFW)."
    return CheckResponse(sfw=is_sfw, sfw_confidence=round(confidence_sfw, 4), message=msg)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.on_event("startup")
async def startup():
    if CHECKPOINT.exists():
        try:
            get_classifier()
        except Exception:
            pass
