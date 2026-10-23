import pytest
import numpy as np
import cv2

from backend.cv.quality import compute_sharpness, check_exposure, compute_glare_ratio, evaluate_frame_quality
from backend.cv.viewpoints import classify_viewpoint_from_time_and_features
from backend.cv.scale import detect_plate_scale
from backend.cv.panel_gap import analyze_seam_gap
from backend.cv.paint import compute_panel_lab, compute_ciede2000, analyze_paint_mismatch
from backend.cv.integrity import detect_hard_cuts, evaluate_trust_level
from backend.cv.comparison import register_frames, box_iou, compare_viewpoint_findings
from backend.core.models import Finding, BoundingBox
from backend.core.scoring import calculate_condition_score

def test_sharpness_calculation():
    # Blurry image (uniform color)
    blurry = np.full((360, 640, 3), 128, dtype=np.uint8)
    sharpness_low = compute_sharpness(blurry)
    assert sharpness_low < 5.0

    # Sharp image with high-frequency edges
    sharp = np.zeros((360, 640, 3), dtype=np.uint8)
    for x in range(0, 640, 20):
        sharp[:, x:x+10] = 255
    sharpness_high = compute_sharpness(sharp)
    assert sharpness_high > 100.0

def test_exposure_check():
    # Normal balanced exposure
    normal = np.random.randint(40, 220, (360, 640, 3), dtype=np.uint8)
    assert check_exposure(normal, clip_ratio=0.05) is True

    # Severely overexposed image (all white)
    overexposed = np.full((360, 640, 3), 255, dtype=np.uint8)
    assert check_exposure(overexposed, clip_ratio=0.05) is False

def test_glare_detection():
    # Moderate lighting
    normal = np.full((360, 640, 3), 100, dtype=np.uint8)
    assert compute_glare_ratio(normal) < 0.05

    # Excessive glare
    glare = np.full((360, 640, 3), 255, dtype=np.uint8)
    assert compute_glare_ratio(glare) > 0.50

def test_viewpoint_classification():
    frame = np.zeros((360, 640, 3), dtype=np.uint8)
    # At t=0s of 24s -> front
    vp_start, conf_start = classify_viewpoint_from_time_and_features(frame, 0.5, 24.0)
    assert vp_start == "front"
    assert conf_start > 0.70

    # At t=12s of 24s -> rear
    vp_mid, conf_mid = classify_viewpoint_from_time_and_features(frame, 12.5, 24.0)
    assert vp_mid == "rear"

def test_panel_gap_analysis():
    # Synthetic seam with two parallel vertical lines 12px apart
    seam = np.full((200, 100, 3), 200, dtype=np.uint8)
    cv2.line(seam, (44, 0), (44, 200), (30, 30, 30), 2)
    cv2.line(seam, (56, 0), (56, 200), (30, 30, 30), 2)

    meas = analyze_seam_gap(seam, "test_seam", "left", pixels_per_mm=3.0)
    assert meas.seam_name == "test_seam"
    assert meas.scale_used == "aruco"
    assert meas.mean_width_mm is not None

def test_paint_ciede2000():
    # Identical panels should have Delta-E near 0
    panel_a = np.full((100, 100, 3), (40, 80, 180), dtype=np.uint8)
    panel_b = np.full((100, 100, 3), (40, 80, 180), dtype=np.uint8)
    result = analyze_paint_mismatch(panel_a, panel_b, "left door", "right door", "side")
    assert result.delta_e < 1.0
    assert result.mismatch_flag is False

    # Distinct colors should have Delta-E > 3.5
    panel_c = np.full((100, 100, 3), (200, 40, 40), dtype=np.uint8)
    result_mismatch = analyze_paint_mismatch(panel_a, panel_c, "left door", "hood", "front")
    assert result_mismatch.delta_e > 10.0
    assert result_mismatch.mismatch_flag is True

def test_hard_cuts_detection():
    # Continuous video frames
    f1 = np.full((200, 200, 3), 100, dtype=np.uint8)
    f2 = np.full((200, 200, 3), 105, dtype=np.uint8)
    # Spliced black frame
    f3 = np.full((200, 200, 3), 0, dtype=np.uint8)

    cuts = detect_hard_cuts([f1, f2, f3], threshold=0.5)
    assert len(cuts) >= 1
    assert 2 in cuts

def test_trust_level_rules():
    # Perfect verified capture
    verified = evaluate_trust_level(
        challenge_passed=True,
        in_app_capture=True,
        sha256_match=True,
        cut_count=0,
        plate_consistent=True,
        appearance_consistent=True,
        video_sha256="abc123sha"
    )
    assert verified.trustLevel == "VERIFIED"

    # Failed challenge -> UNVERIFIED
    failed_challenge = evaluate_trust_level(
        challenge_passed=False,
        in_app_capture=True,
        sha256_match=True,
        cut_count=0,
        plate_consistent=True,
        appearance_consistent=True,
        video_sha256="abc123sha"
    )
    assert failed_challenge.trustLevel == "UNVERIFIED"

    # Hard cut detected -> PARTIAL
    cut_video = evaluate_trust_level(
        challenge_passed=True,
        in_app_capture=True,
        sha256_match=True,
        cut_count=1,
        plate_consistent=True,
        appearance_consistent=True,
        video_sha256="abc123sha"
    )
    assert cut_video.trustLevel == "PARTIAL"

def test_box_iou():
    box_a = (10.0, 10.0, 50.0, 50.0)
    # Identical box -> IoU = 1.0
    assert abs(box_iou(box_a, box_a) - 1.0) < 1e-4

    # Non-overlapping box -> IoU = 0.0
    box_b = (100.0, 100.0, 150.0, 150.0)
    assert box_iou(box_a, box_b) == 0.0

    # Partial overlap
    box_c = (30.0, 30.0, 70.0, 70.0)
    assert 0.1 < box_iou(box_a, box_c) < 0.5

def test_condition_score_calculation():
    # No findings -> 100
    score, _ = calculate_condition_score([])
    assert score == 100

    # Minor scratch -> slight penalty
    f1 = Finding(
        type="scratch",
        panel="door",
        severity="minor",
        confidence=0.8,
        evidenceKey="crop1",
        note="Minor scratch"
    )
    score_f1, _ = calculate_condition_score([f1])
    assert 90 <= score_f1 <= 98

    # Major body damage, gap asymmetry, paint mismatch
    f2 = Finding(type="dent", panel="hood", severity="major", confidence=0.9, evidenceKey="c2", note="Dent")
    f3 = Finding(type="panel_gap_asymmetry", panel="fender", severity="major", confidence=0.9, evidenceKey="c3", note="Gap")
    f4 = Finding(type="paint_mismatch", panel="door", severity="major", confidence=0.9, evidenceKey="c4", note="Paint")
    score_multi, _ = calculate_condition_score([f1, f2, f3, f4])
    assert score_multi < 60
