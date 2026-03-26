"""
Step 7: Train Baseline Model
=============================
Trains YOLOv8m on the merged+augmented P&ID dataset.
Reads all settings from config/train_config.yaml.

Usage:
  python scripts/step7_train.py [--config config/train_config.yaml]

Outputs:
  runs/detect/pid_baseline_yolov8m/
    weights/best.pt       best checkpoint (by val mAP50-95)
    weights/last.pt       latest checkpoint
    results.csv           per-epoch metrics
    confusion_matrix.png
    PR_curve.png
    F1_curve.png
    val_batch*.jpg        sample validation predictions
"""

import argparse
import yaml
from pathlib import Path
from ultralytics import YOLO

ROOT = Path(__file__).parent.parent


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=str(ROOT / "config" / "train_config.yaml"))
    parser.add_argument("--resume", action="store_true",
                        help="Resume from last checkpoint if run exists")
    args = parser.parse_args()

    cfg_path = Path(args.config)
    with open(cfg_path) as f:
        cfg = yaml.safe_load(f)

    # Resolve dataset path relative to ROOT
    data_path = ROOT / cfg["data"]

    print("Step 7: Train Baseline Model")
    print(f"  Config:  {cfg_path}")
    print(f"  Model:   {cfg['model']}")
    print(f"  Data:    {data_path}")
    print(f"  Epochs:  {cfg['epochs']}")
    print(f"  Device:  {cfg['device']}")
    print()

    if args.resume:
        run_dir = ROOT / cfg["project"] / cfg["name"]
        last_ckpt = run_dir / "weights" / "last.pt"
        if last_ckpt.exists():
            print(f"  Resuming from {last_ckpt}")
            model = YOLO(str(last_ckpt))
        else:
            print(f"  No checkpoint found at {last_ckpt}, starting fresh.")
            model = YOLO(cfg["model"])
    else:
        model = YOLO(cfg["model"])

    results = model.train(
        data=str(data_path),
        imgsz=cfg["imgsz"],
        epochs=cfg["epochs"],
        patience=cfg["patience"],
        batch=cfg["batch"],
        workers=cfg["workers"],
        optimizer=cfg["optimizer"],
        lr0=cfg["lr0"],
        lrf=cfg["lrf"],
        momentum=cfg["momentum"],
        weight_decay=cfg["weight_decay"],
        warmup_epochs=cfg["warmup_epochs"],
        warmup_momentum=cfg["warmup_momentum"],
        warmup_bias_lr=cfg["warmup_bias_lr"],
        box=cfg["box"],
        cls=cfg["cls"],
        dfl=cfg["dfl"],
        hsv_h=cfg["hsv_h"],
        hsv_s=cfg["hsv_s"],
        hsv_v=cfg["hsv_v"],
        degrees=cfg["degrees"],
        translate=cfg["translate"],
        scale=cfg["scale"],
        shear=cfg["shear"],
        perspective=cfg["perspective"],
        flipud=cfg["flipud"],
        fliplr=cfg["fliplr"],
        mosaic=cfg["mosaic"],
        mixup=cfg["mixup"],
        copy_paste=cfg["copy_paste"],
        device=cfg["device"],
        amp=cfg["amp"],
        project=str(ROOT / cfg["project"]),
        name=cfg["name"],
        exist_ok=cfg.get("exist_ok", False),
        save=cfg["save"],
        save_period=cfg["save_period"],
        plots=cfg["plots"],
        val=cfg["val"],
        iou=cfg["iou"],
        conf=cfg["conf"],
        max_det=cfg["max_det"],
        resume=args.resume,
        verbose=True,
    )

    print("\n" + "="*65)
    print("Training complete.")
    run_dir = ROOT / cfg["project"] / cfg["name"]
    print(f"  Best weights: {run_dir / 'weights' / 'best.pt'}")
    print(f"  Results:      {run_dir / 'results.csv'}")
    print(f"\nNext: python scripts/step8_evaluate.py")


if __name__ == "__main__":
    main()
