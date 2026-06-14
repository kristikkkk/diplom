"""
Архитектура модели для классификации SFW/NSFW.
Используется при обучении и при инференсе в бэкенде.
"""
import ssl

try:
    import certifi

    ssl._create_default_https_context = lambda: ssl.create_default_context(cafile=certifi.where())
except Exception:
    pass

import torch
import torch.nn as nn
from torchvision import models


def build_model(num_classes: int = 2, pretrained: bool = True) -> nn.Module:
    """Собирает модель на базе ResNet18 с последним слоем на num_classes (SFW/NSFW)."""
    model = models.resnet18(weights=models.ResNet18_Weights.IMAGENET1K_V1 if pretrained else None)
    in_features = model.fc.in_features
    model.fc = nn.Linear(in_features, num_classes)
    return model


def get_inference_transform():
    """Трансформы для инференса (должны совпадать с обучением)."""
    from torchvision import transforms
    return transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize(
            mean=[0.485, 0.456, 0.406],
            std=[0.229, 0.224, 0.225]
        ),
    ])
