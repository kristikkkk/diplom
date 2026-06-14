import argparse
import csv
import json
import os
import platform
import time
from datetime import datetime, timezone
from pathlib import Path

import torch
import torch.nn as nn
from torch.utils.data import DataLoader
from tqdm import tqdm
from torchvision import datasets, transforms

from model_arch import build_model

SUMMARY_CSV_COLUMNS = [
    "epoch",
    "train_loss",
    "train_loss_min",
    "train_loss_max",
    "val_loss",
    "val_acc",
    "epoch_time_sec",
    "num_train_samples",
    "val_total",
    "status",
]


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_run_config(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def save_epoch_json(epochs_dir: Path, epoch_idx: int, data: dict) -> Path:
    epochs_dir.mkdir(parents=True, exist_ok=True)
    out_path = epochs_dir / f"epoch_{epoch_idx:03d}.json"
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    return out_path


def append_summary_csv(csv_path: Path, row: dict) -> None:
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    write_header = not csv_path.exists()
    with csv_path.open("a", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=SUMMARY_CSV_COLUMNS, extrasaction="ignore")
        if write_header:
            writer.writeheader()
        writer.writerow({col: row.get(col) for col in SUMMARY_CSV_COLUMNS})


def summary_row_from_metrics(metrics: dict) -> dict:
    return {
        "epoch": metrics.get("epoch"),
        "train_loss": metrics.get("train_loss"),
        "train_loss_min": metrics.get("train_loss_min"),
        "train_loss_max": metrics.get("train_loss_max"),
        "val_loss": metrics.get("val_loss"),
        "val_acc": metrics.get("val_acc"),
        "epoch_time_sec": metrics.get("epoch_time_sec"),
        "num_train_samples": metrics.get("num_train_samples"),
        "val_total": metrics.get("val_total"),
        "status": metrics.get("status"),
    }


def resolve_training_device(preferred: str) -> torch.device:
    """auto → cuda | mps | cpu; иначе явная строка устройства (cuda:0, cpu, …)."""
    p = (preferred or "auto").lower().strip()
    if p == "auto":
        if torch.cuda.is_available():
            return torch.device("cuda")
        if getattr(torch.backends, "mps", None) is not None and torch.backends.mps.is_available():
            return torch.device("mps")
        return torch.device("cpu")
    return torch.device(preferred)


def default_num_workers() -> int:
    """На macOS многопоточная загрузка чаще проблемна — по умолчанию 0."""
    if platform.system() == "Darwin":
        return 0
    return min(8, os.cpu_count() or 1)


def get_transforms(is_train: bool):
    normalize = transforms.Normalize(
        mean=[0.485, 0.456, 0.406],
        std=[0.229, 0.224, 0.225],
    )

    if is_train:
        return transforms.Compose([
            transforms.Resize((256, 256)),
            transforms.RandomCrop(224),
            transforms.RandomHorizontalFlip(),
            transforms.ToTensor(),
            normalize,
        ])

    return transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        normalize,
    ])


def main():
    parser = argparse.ArgumentParser(description="Train SFW/NSFW classifier")
    parser.add_argument("--data-dir", type=str, default="data")
    parser.add_argument("--epochs", type=int, default=20)
    parser.add_argument("--batch-size", type=int, default=194)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--out-dir", type=str, default="checkpoints")
    parser.add_argument(
        "--device",
        type=str,
        default="auto",
        help="auto | cpu | cuda | mps | cuda:0 …",
    )
    parser.add_argument(
        "--num-workers",
        type=int,
        default=None,
        help="DataLoader workers; по умолчанию 0 на macOS, иначе до 8",
    )
    parser.add_argument(
        "--metrics-dir",
        type=str,
        default=None,
        help="Каталог логов метрик; по умолчанию <out-dir>/training_logs",
    )
    args = parser.parse_args()

    device = resolve_training_device(args.device)
    use_cuda_amp = device.type == "cuda"
    use_channels_last = device.type == "cuda"
    non_blocking = device.type == "cuda"

    if device.type == "cuda":
        torch.backends.cudnn.benchmark = True
    torch.set_float32_matmul_precision("high")

    print("Device:", device)
    _mps = getattr(torch.backends, "mps", None)
    mps_built = bool(_mps and _mps.is_built())
    mps_available = bool(_mps and _mps.is_available())
    print("CUDA:", torch.cuda.is_available(), "| MPS built:", mps_built, "| MPS available:", mps_available)

    data_dir = Path(args.data_dir)
    train_dir = data_dir / "train"
    val_dir = data_dir / "val"

    if not (train_dir / "sfw").exists() or not (train_dir / "nsfw").exists():
        raise FileNotFoundError("Missing sfw/nsfw folders")

    train_ds = datasets.ImageFolder(str(train_dir), transform=get_transforms(True))

    val_ds = None
    if val_dir.exists():
        val_ds = datasets.ImageFolder(str(val_dir), transform=get_transforms(False))

    num_workers = args.num_workers if args.num_workers is not None else default_num_workers()
    pin_memory = device.type == "cuda"

    def loader_kwargs(shuffle: bool) -> dict:
        kw: dict = {
            "batch_size": args.batch_size,
            "shuffle": shuffle,
            "num_workers": num_workers,
            "pin_memory": pin_memory,
        }
        if num_workers > 0:
            kw["persistent_workers"] = True
            kw["prefetch_factor"] = 4
        return kw

    train_loader = DataLoader(train_ds, **loader_kwargs(shuffle=True))

    val_loader = None
    if val_ds:
        val_loader = DataLoader(val_ds, **loader_kwargs(shuffle=False))

    nsfw_idx = train_ds.class_to_idx["nsfw"]
    sfw_idx = train_ds.class_to_idx["sfw"]

    out_dir = Path(args.out_dir)
    metrics_dir = Path(args.metrics_dir) if args.metrics_dir else out_dir / "training_logs"
    epochs_dir = metrics_dir / "epochs"
    summary_csv_path = metrics_dir / "summary.csv"

    os.makedirs(out_dir, exist_ok=True)
    epochs_dir.mkdir(parents=True, exist_ok=True)
    checkpoint_path = out_dir / "sfw_nsfw_model.pt"

    resumed_from_checkpoint = checkpoint_path.exists()
    model = build_model(num_classes=2, pretrained=True).to(device)
    if resumed_from_checkpoint:
        try:
            state = torch.load(checkpoint_path, map_location=device, weights_only=False)
        except Exception as e:
            raise RuntimeError(f"Failed to load checkpoint '{checkpoint_path}': {e}") from e

        if "model_state_dict" not in state:
            raise KeyError(
                f"Checkpoint '{checkpoint_path}' does not contain required key 'model_state_dict'."
            )
        if "class_to_idx" not in state:
            raise KeyError(
                f"Checkpoint '{checkpoint_path}' does not contain required key 'class_to_idx'."
            )
        if state["class_to_idx"] != train_ds.class_to_idx:
            raise ValueError(
                "Checkpoint class mapping is incompatible with current dataset. "
                f"checkpoint={state['class_to_idx']}, dataset={train_ds.class_to_idx}"
            )

        model.load_state_dict(state["model_state_dict"], strict=True)
        print(f"Resume training from checkpoint: {checkpoint_path}")
    else:
        print("Start training from pretrained backbone (no checkpoint found).")
    if use_channels_last:
        model = model.to(memory_format=torch.channels_last)

    write_run_config(
        metrics_dir / "run_config.json",
        {
            "started_at": utc_now_iso(),
            "data_dir": str(data_dir.resolve()),
            "out_dir": str(out_dir.resolve()),
            "metrics_dir": str(metrics_dir.resolve()),
            "epochs": args.epochs,
            "batch_size": args.batch_size,
            "lr": args.lr,
            "device": str(device),
            "num_workers": num_workers,
            "use_cuda_amp": use_cuda_amp,
            "use_channels_last": use_channels_last,
            "train_samples": len(train_ds),
            "val_samples": len(val_ds) if val_ds else None,
            "class_to_idx": train_ds.class_to_idx,
            "torch_version": torch.__version__,
            "resumed_from_checkpoint": resumed_from_checkpoint,
        },
    )
    print("Training metrics dir:", metrics_dir.resolve())

    criterion = nn.CrossEntropyLoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=args.lr)

    scaler = torch.amp.GradScaler("cuda") if use_cuda_amp else None
    device_verified = False

    epochs_bar = tqdm(
        range(args.epochs),
        desc="Epochs",
        unit="epoch",
        leave=True,
    )

    for epoch in epochs_bar:
        epoch_num = epoch + 1
        epoch_start = time.perf_counter()
        epoch_metrics: dict = {
            "epoch": epoch_num,
            "total_epochs": args.epochs,
            "status": "completed",
            "num_train_batches": len(train_loader),
            "num_train_samples": len(train_ds),
            "val_loss": None,
            "val_acc": None,
            "val_correct": None,
            "val_total": None,
        }

        try:
            model.train()
            running_loss = 0.0
            batch_losses: list[float] = []

            train_bar = tqdm(
                train_loader,
                desc=f"Train {epoch_num}/{args.epochs}",
                unit="batch",
                leave=False,
            )
            for step, (images, labels) in enumerate(train_bar, start=1):

                if use_channels_last:
                    images = images.to(device, non_blocking=non_blocking).to(memory_format=torch.channels_last)
                else:
                    images = images.to(device, non_blocking=non_blocking)
                labels = labels.to(device, non_blocking=non_blocking)

                optimizer.zero_grad()

                if use_cuda_amp:
                    with torch.amp.autocast("cuda"):
                        logits = model(images)
                        loss = criterion(logits, labels)
                    scaler.scale(loss).backward()
                    scaler.step(optimizer)
                    scaler.update()
                else:
                    logits = model(images)
                    loss = criterion(logits, labels)
                    loss.backward()
                    optimizer.step()

                if not device_verified:
                    tqdm.write(
                        f"Runtime device check: model={next(model.parameters()).device}, logits={logits.device}"
                    )
                    if device.type == "mps" and (
                        next(model.parameters()).device.type != "mps" or logits.device.type != "mps"
                    ):
                        raise RuntimeError(
                            "Selected device is MPS, but runtime tensors are not on mps. "
                            "Check your PyTorch installation/build for MPS support."
                        )
                    device_verified = True

                loss_value = loss.item()
                batch_losses.append(loss_value)
                running_loss += loss_value
                avg_loss = running_loss / step
                train_bar.set_postfix(loss=f"{loss_value:.4f}", avg_loss=f"{avg_loss:.4f}")

            train_loss = running_loss / len(train_loader)
            train_bar.close()

            epoch_metrics.update({
                "train_loss": train_loss,
                "train_loss_min": min(batch_losses) if batch_losses else None,
                "train_loss_max": max(batch_losses) if batch_losses else None,
                "train_loss_last": batch_losses[-1] if batch_losses else None,
            })

            if val_loader:
                model.eval()
                correct = 0
                total = 0
                val_running_loss = 0.0

                with torch.no_grad():
                    val_bar = tqdm(
                        val_loader,
                        desc=f"Val   {epoch_num}/{args.epochs}",
                        unit="batch",
                        leave=False,
                    )
                    for val_step, (images, labels) in enumerate(val_bar, start=1):

                        if use_channels_last:
                            images = images.to(
                                device, non_blocking=non_blocking
                            ).to(memory_format=torch.channels_last)
                        else:
                            images = images.to(device, non_blocking=non_blocking)
                        labels = labels.to(device)

                        if use_cuda_amp:
                            with torch.amp.autocast("cuda"):
                                logits = model(images)
                        else:
                            logits = model(images)

                        batch_val_loss = criterion(logits, labels)
                        val_running_loss += batch_val_loss.item()
                        pred = logits.argmax(dim=1)

                        total += labels.size(0)
                        correct += (pred == labels).sum().item()
                        val_bar.set_postfix(
                            acc=f"{(correct / total):.4f}",
                            loss=f"{(val_running_loss / val_step):.4f}",
                        )
                    val_bar.close()

                val_loss = val_running_loss / len(val_loader)
                val_acc = 100 * correct / total
                epoch_metrics.update({
                    "val_loss": val_loss,
                    "val_acc": val_acc,
                    "val_correct": correct,
                    "val_total": total,
                })

        except Exception as e:
            epoch_time = time.perf_counter() - epoch_start
            epoch_metrics.update({
                "status": "failed",
                "error": str(e),
                "epoch_time_sec": round(epoch_time, 3),
                "finished_at": utc_now_iso(),
            })
            save_epoch_json(epochs_dir, epoch_num, epoch_metrics)
            append_summary_csv(summary_csv_path, summary_row_from_metrics(epoch_metrics))
            raise

        epoch_time = time.perf_counter() - epoch_start
        epoch_metrics.update({
            "epoch_time_sec": round(epoch_time, 3),
            "finished_at": utc_now_iso(),
        })

        save_epoch_json(epochs_dir, epoch_num, epoch_metrics)
        append_summary_csv(summary_csv_path, summary_row_from_metrics(epoch_metrics))

        postfix = {"train_loss": f"{epoch_metrics['train_loss']:.4f}", "time": f"{epoch_time:.1f}s"}
        if epoch_metrics["val_acc"] is not None:
            postfix["val_acc"] = f"{epoch_metrics['val_acc']:.2f}%"
        if epoch_metrics["val_loss"] is not None:
            postfix["val_loss"] = f"{epoch_metrics['val_loss']:.4f}"
        epochs_bar.set_postfix(postfix)

        summary = (
            f"Epoch {epoch_num}/{args.epochs} | time={epoch_time:.1f}s "
            f"| train_loss={epoch_metrics['train_loss']:.4f}"
        )
        if epoch_metrics["val_acc"] is not None:
            summary += f" | val_acc={epoch_metrics['val_acc']:.2f}%"
        if epoch_metrics["val_loss"] is not None:
            summary += f" | val_loss={epoch_metrics['val_loss']:.4f}"
        tqdm.write(summary)

    state = {
        "model_state_dict": model.state_dict(),
        "class_to_idx": train_ds.class_to_idx,
        "nsfw_idx": int(nsfw_idx),
        "sfw_idx": int(sfw_idx),
    }

    torch.save(state, checkpoint_path)

    print("Model saved:", checkpoint_path)
    print("Training metrics:", summary_csv_path.resolve())


if __name__ == "__main__":

    print("Torch:", torch.__version__)

    main()
