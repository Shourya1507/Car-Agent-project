#!/usr/bin/env python3
"""
CarDD YOLO Damage Detection Fine-Tuning Script
Implements training pipeline per TRD v1.1 Section 7:
- Model: YOLOv8 small (yolov8s.pt) fine-tuned on CarDD
- Input resolution: 640x640
- Data augmentations: brightness, blur, perspective, mosaic
- Target: 100 epochs with early stopping (patience=15)
- Automated ONNX export post-training
"""

import os
import argparse
from typing import Optional

def train_yolo(
    data_yaml: str = "ml/data/cardd.yaml",
    model_name: str = "yolov8s.pt",
    epochs: int = 100,
    img_size: int = 640,
    batch_size: int = 16,
    project_dir: str = "ml/runs/train",
    name: str = "cardd_yolov8s"
):
    print("=" * 70)
    print(" CARCHECK AGENT - CarDD YOLO DAMAGE DETECTOR TRAINING")
    print("=" * 70)
    print(f"Data YAML:    {data_yaml}")
    print(f"Base Model:   {model_name}")
    print(f"Epochs:       {epochs}")
    print(f"Input Size:   {img_size}x{img_size}")
    print(f"Batch Size:   {batch_size}")
    print("Augmentations: Mosaic, HSV (brightness/saturation), perspective, blur")
    print("Licence Note: Ultralytics is AGPL-3.0. For commercial use, use an Apache-2.0 detector.")
    print("=" * 70)

    try:
        from ultralytics import YOLO
        model = YOLO(model_name)

        # Train model with augmentations per TRD Section 7
        results = model.train(
            data=data_yaml,
            epochs=epochs,
            imgsz=img_size,
            batch=batch_size,
            patience=15, # Early stopping on val mAP50-95
            save=True,
            project=project_dir,
            name=name,
            hsv_h=0.015,
            hsv_s=0.7,
            hsv_v=0.4, # Brightness augmentation
            degrees=10.0,
            perspective=0.001,
            mosaic=1.0,
            plots=True
        )

        print("\nTraining complete! Exporting best weights to ONNX format...")
        best_pt = os.path.join(project_dir, name, "weights", "best.pt")
        if os.path.exists(best_pt):
            model.export(format="onnx", imgsz=img_size, dynamic=True, simplify=True)
            print(f"Model exported to ONNX successfully at: {best_pt.replace('.pt', '.onnx')}")
    except ImportError:
        print("\n[NOTE] 'ultralytics' package not installed in current environment.")
        print("To run GPU training on AWS SageMaker / local GPU machine:")
        print("  pip install ultralytics torch torchvision")
        print("  python ml/train_cardd.py --epochs 100 --batch 16")
        print("\nProceeding with ONNX inference engine demonstration in ml/onnx_inference.py.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train YOLO on CarDD dataset")
    parser.add_argument("--epochs", type=int, default=100)
    parser.add_argument("--batch", type=int, default=16)
    parser.add_argument("--imgsz", type=int, default=640)
    args = parser.parse_args()

    train_yolo(epochs=args.epochs, batch_size=args.batch, img_size=args.imgsz)
