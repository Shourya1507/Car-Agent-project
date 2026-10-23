# CarCheck Agent — Machine Learning & Damage Detection Pipeline

## 1. Overview & Purpose
While classical Computer Vision (OpenCV) excels at deterministic geometric checks (ArUco / license plate millimeter metric scaling, panel gap uniformity via Canny + Hough lines, and CIE94/CIEDE2000 paint chromaticity mismatches), **surface damage detection (dents, scratches, cracks, glass shatter, broken lights, and tyre anomalies)** requires deep semantic feature representation to handle diverse reflections, paint finishes, angles, and complex shadows on vehicle bodywork.

The `ml/` module contains the end-to-end Machine Learning pipeline for CarCheck Agent:
1. **Dataset Preparation** (`ml/dataset_prep.py`): Downloads, formats, and validates the CarDD (Car Damage Dataset) into standard YOLO format.
2. **Transfer Learning / Fine-Tuning** (`ml/train_cardd.py`): Fine-tunes YOLOv8 on damage classes with phone-walkaround augmentations.
3. **ONNX Export & Optimization** (`ml/export_onnx.py`): Quantizes and exports checkpoints to ONNX format with fixed IR versioning for lightweight Lambda serving.
4. **ONNX Runtime Inference Engine** (`ml/onnx_inference.py`): Production inference engine with letterbox preprocessing, Non-Maximum Suppression (NMS), and deterministic panel area-ratio severity banding.
5. **Model Evaluation** (`ml/evaluate_model.py`): Evaluates mAP@50, mAP@50-95, and handheld camera distribution shift.

---

## 2. Supported Damage Classes (CarDD Taxonomy)
The model detects and categorizes findings across 6 core damage classes:
| Class ID | Class Name | Description | Default Severity Banding |
|---|---|---|---|
| 0 | `dent` | Surface indentation on metal or plastic body panels | Minor (<2%), Moderate (2-8%), Major (>8%) |
| 1 | `scratch` | Linear or swirl clear-coat / base-coat paint scratch | Minor (<2%), Moderate (2-8%), Major (>8%) |
| 2 | `crack` | Structural fracture on bumper or composite trim | Moderate to Major |
| 3 | `glass_shatter`| Windshield, window, or panoramic roof cracking | Major (Safety critical) |
| 4 | `lamp_broken` | Headlight, taillight, or indicator lens damage | Moderate to Major |
| 5 | `tyre_flat` | Under-inflated or punctured tyre detected | Major |

---

## 3. Pipeline Architecture

```
Phone Walkaround Video Frame (1080p BGR)
                   │
                   ▼
       [Letterbox Resize 640x640]
       (Aspect preserved, 114 grey padding)
                   │
                   ▼
    [ONNX Runtime CPU InferenceSession]
    (4 intra-op threads, INT8/FP16 optimized)
                   │
                   ▼
         [Raw Tensor: 1 x 10 x 8400]
                   │
                   ▼
  [Confidence Filter (conf >= 0.35)]
                   │
                   ▼
    [Non-Maximum Suppression (IoU 0.45)]
                   │
                   ▼
   [Area Ratio Severity Banding (TRD 7)]
     - Area < 2% panel  -> "minor"
     - Area 2% - 8%     -> "moderate"
     - Area > 8%        -> "major"
                   │
                   ▼
   [Evidence Crop + Bounding Box Callout]
     Saved to S3 / Local storage with ECDSA hash
```

---

## 4. Why ONNX Runtime for Serving?
1. **Zero PyTorch Dependency in Production**: Deploying PyTorch in AWS Lambda requires bulky Docker layers (>2GB) and slow cold starts. ONNX Runtime (`onnxruntime-headless`) weighs only ~50MB and boots in under 200ms.
2. **Deterministic Latency**: Inference on a single 640x640 frame takes 45-65ms on an x86_64 or ARM64 Lambda vCPU.
3. **Hardware Portability**: The same `.onnx` graph runs on local developer laptops, AWS Lambda (CPU), or AWS SageMaker (NVIDIA TensorRT GPU).

---

## 5. Usage Commands

### A. Prepare CarDD Dataset
```bash
python ml/dataset_prep.py --data-dir data/cardd --download
```

### B. Fine-Tune YOLOv8s
```bash
python ml/train_cardd.py --data ml/cardd.yaml --epochs 50 --batch 16 --imgsz 640 --device cpu
```

### C. Export to ONNX
```bash
python ml/export_onnx.py --weights ml/runs/train/cardd_yolov8s/weights/best.pt --output ml/models/cardd_yolov8.onnx --imgsz 640
```

### D. Benchmark & Evaluate
```bash
python ml/evaluate_model.py --model ml/models/cardd_yolov8.onnx --data data/cardd
```

### E. Run Standalone ONNX Inference
```bash
python -m ml.onnx_inference ml/models/cardd_yolov8.onnx
```

---

## 6. Integration with CarCheck Backend
The backend detector adapter in `backend/adapters/detector_local.py` automatically detects `ml/models/cardd_yolov8.onnx`. If present, it uses `OnnxDamageDetector` to generate evidence-backed damage findings. If the ONNX model is missing or runs in an environment without ONNX runtime, it automatically falls back to OpenCV Sobel edge & contour anomaly detection without breaking the workflow.
