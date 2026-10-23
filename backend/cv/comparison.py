import cv2
import numpy as np
from typing import List, Tuple, Optional, Dict
from backend.core.models import Finding, ChangeItem, BoundingBox

def register_frames(base_bgr: np.ndarray, new_bgr: np.ndarray, min_inliers: int = 40) -> Optional[Tuple[np.ndarray, float]]:
    """
    Computes geometric alignment between baseline frame and return frame using ORB + RANSAC homography.
    Requires at least 40 inliers and an inlier ratio >= 0.4 (per TRD 21.1).
    """
    orb = cv2.ORB_create(2000)
    g1 = cv2.cvtColor(base_bgr, cv2.COLOR_BGR2GRAY)
    g2 = cv2.cvtColor(new_bgr, cv2.COLOR_BGR2GRAY)

    k1, d1 = orb.detectAndCompute(g1, None)
    k2, d2 = orb.detectAndCompute(g2, None)

    if d1 is None or d2 is None or len(k1) < 10 or len(k2) < 10:
        return None

    matcher = cv2.BFMatcher(cv2.NORM_HAMMING)
    pairs = matcher.knnMatch(d2, d1, k=2)

    good = []
    for p in pairs:
        if len(p) == 2 and p[0].distance < 0.75 * p[1].distance:
            good.append(p[0])

    if len(good) < min_inliers:
        return None

    src = np.float32([k2[m.queryIdx].pt for m in good]).reshape(-1, 1, 2)
    dst = np.float32([k1[m.trainIdx].pt for m in good]).reshape(-1, 1, 2)

    H, mask = cv2.findHomography(src, dst, cv2.RANSAC, 4.0)
    if H is None:
        return None

    inlier_count = int(mask.sum())
    inlier_ratio = float(mask.mean())

    if inlier_count < min_inliers or inlier_ratio < 0.4:
        return None

    return H, inlier_ratio

def box_iou(a: Tuple[float, float, float, float], b: Tuple[float, float, float, float]) -> float:
    """Computes Intersection over Union of two bounding boxes (x1, y1, x2, y2)."""
    x1 = max(a[0], b[0])
    y1 = max(a[1], b[1])
    x2 = min(a[2], b[2])
    y2 = min(a[3], b[3])

    inter = max(0.0, x2 - x1) * max(0.0, y2 - y1)
    area_a = max(0.0, a[2] - a[0]) * max(0.0, a[3] - a[1])
    area_b = max(0.0, b[2] - b[0]) * max(0.0, b[3] - b[1])
    union = area_a + area_b - inter

    return (inter / union) if union > 0 else 0.0

def transform_box(box: BoundingBox, H: np.ndarray) -> Tuple[float, float, float, float]:
    """Transforms bounding box corners from return coordinate space into baseline coordinate space using H."""
    pts = np.float32([
        [box.x1, box.y1],
        [box.x2, box.y1],
        [box.x2, box.y2],
        [box.x1, box.y2]
    ]).reshape(-1, 1, 2)

    transformed = cv2.perspectiveTransform(pts, H)
    tx1 = float(np.min(transformed[:, 0, 0]))
    ty1 = float(np.min(transformed[:, 0, 1]))
    tx2 = float(np.max(transformed[:, 0, 0]))
    ty2 = float(np.max(transformed[:, 0, 1]))

    return (tx1, ty1, tx2, ty2)

def compare_viewpoint_findings(
    viewpoint: str,
    base_frame_bgr: Optional[np.ndarray],
    return_frame_bgr: Optional[np.ndarray],
    baseline_findings: List[Finding],
    return_findings: List[Finding],
    iou_threshold: float = 0.3
) -> Tuple[List[ChangeItem], List[Finding]]:
    """
    Performs Handover Mode comparison for a viewpoint:
    1. Geometrically registers return frame to baseline frame.
    2. Matches bounding boxes using homography transform + IoU.
    3. Categorizes each finding as NEW, PRE-EXISTING, RESOLVED, or UNCERTAIN.
    """
    changes: List[ChangeItem] = []
    labeled_findings: List[Finding] = []

    # Check if both frames are available
    if base_frame_bgr is None or return_frame_bgr is None:
        for rf in return_findings:
            item = ChangeItem(
                findingId=rf.id,
                changeStatus="UNCERTAIN",
                panel=rf.panel,
                type=rf.type,
                confidence=rf.confidence * 0.5,
                baselineEvidenceKey=None,
                returnEvidenceKey=rf.evidenceKey,
                alignmentQuality=0.0,
                note=f"Viewpoint {viewpoint} skipped: missing paired frame"
            )
            changes.append(item)
            rf.changeStatus = "UNCERTAIN"
            labeled_findings.append(rf)
        return changes, labeled_findings

    reg_result = register_frames(base_frame_bgr, return_frame_bgr)
    if reg_result is None:
        # Homography failed (< 40 inliers or inlier ratio < 0.4)
        for rf in return_findings:
            item = ChangeItem(
                findingId=rf.id,
                changeStatus="UNCERTAIN",
                panel=rf.panel,
                type=rf.type,
                confidence=round(rf.confidence * 0.6, 2),
                baselineEvidenceKey=None,
                returnEvidenceKey=rf.evidenceKey,
                alignmentQuality=0.0,
                note=f"Alignment failed for {viewpoint}: camera angle or lighting varied significantly."
            )
            changes.append(item)
            rf.changeStatus = "UNCERTAIN"
            labeled_findings.append(rf)
        return changes, labeled_findings

    H, inlier_ratio = reg_result
    matched_base_ids = set()

    # Compare return findings against baseline findings
    for rf in return_findings:
        matched_bf = None
        best_iou = 0.0

        if rf.box is not None:
            t_box = transform_box(rf.box, H)
            for bf in baseline_findings:
                if bf.box is not None and bf.type == rf.type and bf.panel == rf.panel:
                    cur_iou = box_iou(t_box, (bf.box.x1, bf.box.y1, bf.box.x2, bf.box.y2))
                    if cur_iou >= iou_threshold and cur_iou > best_iou:
                        best_iou = cur_iou
                        matched_bf = bf

        if matched_bf is not None:
            # PRE-EXISTING
            matched_base_ids.add(matched_bf.id)
            rf.changeStatus = "PRE-EXISTING"
            rf.baselineFindingId = matched_bf.id
            rf.baselineEvidenceKey = matched_bf.evidenceKey
            rf.returnEvidenceKey = rf.evidenceKey
            labeled_findings.append(rf)
            changes.append(ChangeItem(
                findingId=rf.id,
                changeStatus="PRE-EXISTING",
                panel=rf.panel,
                type=rf.type,
                confidence=round((rf.confidence + matched_bf.confidence) / 2.0, 2),
                baselineEvidenceKey=matched_bf.evidenceKey,
                returnEvidenceKey=rf.evidenceKey,
                alignmentQuality=round(inlier_ratio, 2),
                note=f"Pre-existing {rf.type} on {rf.panel} verified from baseline pickup inspection."
            ))
        else:
            # NEW finding
            rf.changeStatus = "NEW"
            rf.returnEvidenceKey = rf.evidenceKey
            labeled_findings.append(rf)
            changes.append(ChangeItem(
                findingId=rf.id,
                changeStatus="NEW",
                panel=rf.panel,
                type=rf.type,
                confidence=rf.confidence,
                baselineEvidenceKey=None,
                returnEvidenceKey=rf.evidenceKey,
                alignmentQuality=round(inlier_ratio, 2),
                note=f"NEW {rf.type} detected on {rf.panel} not present in baseline inspection."
            ))

    # Check for RESOLVED findings (in baseline but absent in return)
    for bf in baseline_findings:
        if bf.id not in matched_base_ids:
            changes.append(ChangeItem(
                findingId=bf.id,
                changeStatus="RESOLVED",
                panel=bf.panel,
                type=bf.type,
                confidence=bf.confidence,
                baselineEvidenceKey=bf.evidenceKey,
                returnEvidenceKey=None,
                alignmentQuality=round(inlier_ratio, 2),
                note=f"Baseline {bf.type} on {bf.panel} no longer detected (possible repair or buffing)."
            ))

    return changes, labeled_findings
