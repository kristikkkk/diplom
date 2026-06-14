"""
Загрузка модели и инференс для одного изображения.
Используется бэкендом.
"""
from pathlib import Path
from typing import Tuple

import torch
from PIL import Image

from model_arch import build_model, get_inference_transform


def pick_image_inference_device() -> torch.device:
    """Приоритет как при обучении: CUDA → MPS (Apple Silicon) → CPU."""
    if torch.cuda.is_available():
        return torch.device("cuda")
    mps = getattr(torch.backends, "mps", None)
    if mps is not None and mps.is_available():
        return torch.device("mps")
    return torch.device("cpu")


class SFWNSFWClassifier:
    def __init__(self, checkpoint_path: str = "checkpoints/sfw_nsfw_model.pt"):
        self.device = pick_image_inference_device()
        self.transform = get_inference_transform()
        state = torch.load(checkpoint_path, map_location=self.device, weights_only=False)
        self.class_to_idx = state["class_to_idx"]
        self.nsfw_idx = state["nsfw_idx"]
        self.sfw_idx = state["sfw_idx"]
        self.model = build_model(num_classes=2, pretrained=False)
        self.model.load_state_dict(state["model_state_dict"], strict=True)
        self.model.to(self.device)
        self.model.eval()

    def predict_image(self, image: Image.Image) -> Tuple[bool, float]:
        """
        Возвращает (is_sfw, confidence_sfw).
        is_sfw: True если контент Safe for Work.
        confidence_sfw: вероятность класса SFW от 0 до 1.
        """
        x = self.transform(image).unsqueeze(0).to(self.device)
        with torch.no_grad():
            logits = self.model(x)
            probs = torch.softmax(logits, dim=1)[0]
        sfw_prob = probs[self.sfw_idx].item()
        return sfw_prob >= 0.5, sfw_prob

    def predict_image_path(self, path: str) -> Tuple[bool, float]:
        image = Image.open(path).convert("RGB")
        return self.predict_image(image)


def load_classifier(checkpoint_path: str = "checkpoints/sfw_nsfw_model.pt") -> SFWNSFWClassifier:
    if not Path(checkpoint_path).exists():
        raise FileNotFoundError(
            f"Модель не найдена: {checkpoint_path}. Сначала запустите train.py и положите изображения в data/train/sfw и data/train/nsfw."
        )
    return SFWNSFWClassifier(checkpoint_path)
