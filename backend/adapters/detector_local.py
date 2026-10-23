import os
import cv2
import numpy as np
import uuid
from typing import List, Optional
from backend.core.ports.detector import DetectorPort
from backend.core.ports.storage import StoragePort
from backend.core.models import Finding, BoundingBox

class LocalDamageDetector(DetectorPort):
    def __init__(self, storage: StoragePort, inspection_id: str = ""):
        self.storage = storage
        self.inspection_id = inspection_id
        self.onnx_detector = None

        try:
            from ml.onnx_inference import OnnxDamageDetector
            model_path = os.environ.get("ONNX_MODEL_PATH", "ml/models/cardd_yolov8.onnx")
            if os.path.exists(model_path):
                self.onnx_detector = OnnxDamageDetector(model_path=model_path)
        except Exception:
            self.onnx_detector = None

    def set_inspection_id(self, inspection_id: str):
        self.inspection_id = inspection_id

    def detect_damage(self, image_bgr: np.ndarray, viewpoint: str, frame_key: str) -> List[Finding]:
        """
        Detects vehicle surface damage using CarDD ONNX Runtime model or OpenCV anomaly analysis.
        Assigns severity based on relative area and saves annotated evidence crops.
        """
        h, w = image_bgr.shape[:2]
        panel_name = self._viewpoint_to_panel(viewpoint)
        findings: List[Finding] = []

        # 1. Primary: ONNX Runtime ML Detector (if initialized)
        if self.onnx_detector and self.onnx_detector.session is not None:
            try:
                raw_dets = self.onnx_detector.detect(image_bgr)
                for det in raw_dets[:2]:
                    bx1, by1, bx2, by2 = det["box"]
                    crop_bgr = image_bgr[by1:by2, bx1:bx2].copy()
                    finding_id = f"fnd_{uuid.uuid4().hex[:8]}"
                    crop_key = f"evidence/{self.inspection_id}/{finding_id}.jpg"

                    if crop_bgr.size > 0:
                        cv2.rectangle(crop_bgr, (2, 2), (crop_bgr.shape[1] - 3, crop_bgr.shape[0] - 3), (0, 140, 255), 2)
                        _, enc = cv2.imencode(".jpg", crop_bgr, [cv2.IMWRITE_JPEG_QUALITY, 90])
                        self.storage.save_bytes(crop_key, enc.tobytes(), "image/jpeg")

                    note = f"Possible {det['severity']} {det['class']} detected on {panel_name} ({det['confidence']*100:.0f}% confidence)."
                    findings.append(Finding(
                        id=finding_id,
                        type=det["class"],
                        panel=panel_name,
                        severity=det["severity"],
                        confidence=det["confidence"],
                        evidenceKey=crop_key,
                        note=note,
                        source="onnx_yolov8",
                        box=BoundingBox(x1=bx1, y1=by1, x2=bx2, y2=by2)
                    ))
                if findings:
                    return findings
            except Exception:
                pass # Fall back to OpenCV

        # 2. Fallback: OpenCV Gradient & Texture Anomaly Detector
        gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)

        # Vehicle panel ROI
        y1_car, y2_car = int(h * 0.25), int(h * 0.85)
        x1_car, x2_car = int(w * 0.15), int(w * 0.85)
        car_roi = gray[y1_car:y2_car, x1_car:x2_car]

        # Sobel gradient detection for surface scratches/dents
        grad_x = cv2.Sobel(car_roi, cv2.CV_16S, 1, 0, ksize=3)
        grad_y = cv2.Sobel(car_roi, cv2.CV_16S, 0, 1, ksize=3)
        abs_grad = cv2.addWeighted(cv2.convertScaleAbs(grad_x), 0.5, cv2.convertScaleAbs(grad_y), 0.5, 0)
        
        # Adaptive thresholding to detect local surface disruptions
        _, thresh = cv2.threshold(abs_grad, 45, 255, cv2.THRESH_BINARY)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
        closed = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)

        contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        panel_name = self._viewpoint_to_panel(viewpoint)

        for c in contours:
            area = cv2.contourArea(c)
            # Filter realistic damage contour sizes
            if 150 < area < (car_roi.size * 0.15):
                bx, by, bw, bh = cv2.boundingRect(c)
                # Map to full image coordinates
                abs_x1 = max(0, x1_car + bx - 10)
                abs_y1 = max(0, y1_car + by - 10)
                abs_x2 = min(w, x1_car + bx + bw + 10)
                abs_y2 = min(h, y1_car + by + bh + 10)

                aspect = float(bw) / float(bh) if bh > 0 else 1.0
                damage_type = "scratch" if (aspect > 2.2 or aspect < 0.45) else "dent"

                area_ratio = float(bw * bh) / float(car_roi.size)
                if area_ratio < 0.02:
                    severity = "minor"
                elif area_ratio < 0.08:
                    severity = "moderate"
                else:
                    severity = "major"

                confidence = round(float(min(0.94, max(0.65, 0.75 + (area_ratio * 2.0)))), 2)

                finding_id = f"fnd_{uuid.uuid4().hex[:8]}"
                crop_key = f"evidence/{self.inspection_id}/{finding_id}.jpg"

                # Create annotated crop image with bounding box and callout
                crop_bgr = image_bgr[abs_y1:abs_y2, abs_x1:abs_x2].copy()
                if crop_bgr.size > 0:
                    cv2.rectangle(crop_bgr, (2, 2), (crop_bgr.shape[1] - 3, crop_bgr.shape[0] - 3), (0, 140, 255), 2)
                    # Encode to JPEG and save via storage port
                    _, enc = cv2.imencode(".jpg", crop_bgr, [cv2.IMWRITE_JPEG_QUALITY, 90])
                    self.storage.save_bytes(crop_key, enc.tobytes(), "image/jpeg")

                note = f"Possible {severity} {damage_type} detected on {panel_name} ({confidence*100:.0f}% confidence)."

                finding = Finding(
                    id=finding_id,
                    type=damage_type,
                    panel=panel_name,
                    severity=severity,
                    confidence=confidence,
                    evidenceKey=crop_key,
                    note=note,
                    source="detector",
                    box=BoundingBox(x1=abs_x1, y1=abs_y1, x2=abs_x2, y2=abs_y2)
                )
                findings.append(finding)

                # Cap per viewpoint to avoid clutter
                if len(findings) >= 2:
                    break

        return findings

    def _viewpoint_to_panel(self, viewpoint: str) -> str:
        mapping = {
            "front": "front bumper",
            "front-left": "front-left fender",
            "left": "left door",
            "rear-left": "rear-left quarter panel",
            "rear": "rear bumper & boot",
            "rear-right": "rear-right quarter panel",
            "right": "right door",
            "front-right": "front-right fender"
        }
        return mapping.get(viewpoint, "body panel")
