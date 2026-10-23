#!/usr/bin/env python3
"""
ONNX Runtime Vehicle Damage Inference Engine
Implements production inference pipeline per TRD v1.1 Section 7:
- Letterbox image resizing (640x640)
- ONNX Runtime execution (CPU Lambda container or GPU SageMaker)
- Bounding box decoding & Non-Maximum Suppression (NMS)
- Severity banding based on panel area ratio (<2% minor, 2-8% moderate, >8% major)
"""

import os
import cv2
import numpy as np
import onnxruntime as ort
from typing import List, Dict, Any, Tuple, Optional
from backend.core.models import Finding, BoundingBox

CARDD_CLASSES = [
    "dent",
    "scratch",
    "crack",
    "glass_shatter",
    "lamp_broken",
    "tyre_flat"
]

class OnnxDamageDetector:
    def __init__(
        self,
        model_path: str = "ml/models/cardd_yolov8.onnx",
        conf_threshold: float = 0.35,
        iou_threshold: float = 0.45,
        input_size: int = 640
    ):
        self.model_path = model_path
        self.conf_threshold = conf_threshold
        self.iou_threshold = iou_threshold
        self.input_size = input_size
        self.session = None

        if os.path.exists(model_path):
            try:
                # Optimized ONNX Runtime Session Options
                opts = ort.SessionOptions()
                opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
                opts.intra_op_num_threads = 4
                self.session = ort.InferenceSession(model_path, opts, providers=["CPUExecutionProvider"])
                self.input_name = self.session.get_inputs()[0].name
                self.output_names = [o.name for o in self.session.get_outputs()]
            except Exception as e:
                print(f"Warning: Failed to load ONNX model {model_path}: {e}")

    def preprocess(self, image_bgr: np.ndarray) -> Tuple[np.ndarray, float, Tuple[int, int]]:
        """Letterbox resizing preserving aspect ratio with grey padding (114, 114, 114)."""
        h, w = image_bgr.shape[:2]
        scale = min(self.input_size / h, self.input_size / w)
        new_w = int(w * scale)
        new_h = int(h * scale)

        resized = cv2.resize(image_bgr, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
        canvas = np.full((self.input_size, self.input_size, 3), 114, dtype=np.uint8)

        pad_x = (self.input_size - new_w) // 2
        pad_y = (self.input_size - new_h) // 2
        canvas[pad_y:pad_y + new_h, pad_x:pad_x + new_w] = resized

        # HWC BGR -> CHW RGB, normalized to [0, 1]
        rgb = cv2.cvtColor(canvas, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
        blob = np.transpose(rgb, (2, 0, 1))[None, ...]
        return blob, scale, (pad_x, pad_y)

    def calculate_severity(self, box_w: float, box_h: float, img_w: int, img_h: int) -> str:
        """
        Assigns severity band based on area ratio relative to vehicle panel per TRD 7:
        - minor: area < 2%
        - moderate: area 2% to 8%
        - major: area > 8%
        """
        panel_area = (img_w * 0.7) * (img_h * 0.6) # Approximate visible panel area
        damage_area = box_w * box_h
        area_ratio = damage_area / (panel_area + 1e-6)

        if area_ratio < 0.02:
            return "minor"
        elif area_ratio <= 0.08:
            return "moderate"
        else:
            return "major"

    def detect(self, image_bgr: np.ndarray) -> List[Dict[str, Any]]:
        """Runs ONNX model inference and decodes detected damage with NMS."""
        if self.session is None:
            return []

        orig_h, orig_w = image_bgr.shape[:2]
        blob, scale, (pad_x, pad_y) = self.preprocess(image_bgr)

        # Run ONNX session
        outputs = self.session.run(self.output_names, {self.input_name: blob})
        raw_output = outputs[0] # [1, 10, 8400] or [1, 8400, 10]

        # Handle transpose if needed
        if raw_output.shape[1] == 10 and raw_output.shape[2] == 8400:
            preds = raw_output[0].T # [8400, 10]
        else:
            preds = raw_output[0]

        boxes = []
        confidences = []
        class_ids = []

        for row in preds:
            cx, cy, w, h = row[:4]
            class_scores = row[4:]
            best_cls = np.argmax(class_scores)
            conf = float(class_scores[best_cls])

            if conf >= self.conf_threshold:
                # Transform back to original image space
                x1 = (cx - w / 2 - pad_x) / scale
                y1 = (cy - h / 2 - pad_y) / scale
                x2 = (cx + w / 2 - pad_x) / scale
                y2 = (cy + h / 2 - pad_y) / scale

                x1 = max(0, min(orig_w, x1))
                y1 = max(0, min(orig_h, y1))
                x2 = max(0, min(orig_w, x2))
                y2 = max(0, min(orig_h, y2))

                boxes.append([int(x1), int(y1), int(x2 - x1), int(y2 - y1)])
                confidences.append(float(conf))
                class_ids.append(int(best_cls))

        # Non-Maximum Suppression (NMS)
        indices = cv2.dnn.NMSBoxes(boxes, confidences, self.conf_threshold, self.iou_threshold)
        detections = []

        if len(indices) > 0:
            for i in indices.flatten():
                bx, by, bw, bh = boxes[i]
                cls_idx = class_ids[i]
                cls_name = CARDD_CLASSES[cls_idx] if cls_idx < len(CARDD_CLASSES) else "damage"
                sev = self.calculate_severity(bw, bh, orig_w, orig_h)

                detections.append({
                    "class": cls_name,
                    "confidence": round(confidences[i], 2),
                    "severity": sev,
                    "box": (bx, by, bx + bw, by + bh)
                })

        return detections
