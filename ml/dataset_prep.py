#!/usr/bin/env python3
"""
CarDD (Car Damage Detection) Dataset Preparation Script
Prepares and formats CarDD dataset into standard YOLO format for training.
Classes: dent, scratch, crack, glass_shatter, lamp_broken, tyre_flat
"""

import os
import json
import shutil
import random
from pathlib import Path
from typing import Dict, List, Tuple

# CarDD Damage Classes per TRD Section 7
CARDD_CLASSES = [
    "dent",
    "scratch",
    "crack",
    "glass_shatter",
    "lamp_broken",
    "tyre_flat"
]

CLASS_TO_ID = {name: idx for idx, name in enumerate(CARDD_CLASSES)}

def create_yolo_dataset_structure(base_dir: str = "ml/data/cardd_yolo") -> Dict[str, str]:
    """Creates directory structure for YOLO training, validation, and testing."""
    paths = {
        "train_images": os.path.join(base_dir, "images", "train"),
        "val_images": os.path.join(base_dir, "images", "val"),
        "test_images": os.path.join(base_dir, "images", "test"),
        "train_labels": os.path.join(base_dir, "labels", "train"),
        "val_labels": os.path.join(base_dir, "labels", "val"),
        "test_labels": os.path.join(base_dir, "labels", "test"),
    }
    for p in paths.values():
        os.makedirs(p, exist_ok=True)
    return paths

def generate_data_yaml(output_path: str = "ml/data/cardd.yaml", dataset_root: str = "ml/data/cardd_yolo"):
    """Generates YOLO dataset configuration YAML file."""
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    yaml_content = f"""# CarDD Damage Detection Dataset Configuration
# Companion to CarCheck Agent TRD v1.1 Section 7

path: {os.path.abspath(dataset_root)}
train: images/train
val: images/val
test: images/test

# Classes (6 categories)
names:
  0: dent
  1: scratch
  2: crack
  3: glass_shatter
  4: lamp_broken
  5: tyre_flat
"""
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(yaml_content)
    print(f"Generated dataset YAML at: {output_path}")

def convert_bbox_to_yolo(size: Tuple[int, int], box: Tuple[float, float, float, float]) -> Tuple[float, float, float, float]:
    """Converts (xmin, ymin, xmax, ymax) to normalized YOLO format (x_center, y_center, width, height)."""
    dw = 1.0 / size[0]
    dh = 1.0 / size[1]
    x_center = (box[0] + box[2]) / 2.0
    y_center = (box[1] + box[3]) / 2.0
    w = box[2] - box[0]
    h = box[3] - box[1]
    return (x_center * dw, y_center * dh, w * dw, h * dh)

if __name__ == "__main__":
    print("Preparing CarDD dataset directory structure...")
    dirs = create_yolo_dataset_structure()
    generate_data_yaml()
    print("Dataset structure ready for CarDD images and annotations.")
