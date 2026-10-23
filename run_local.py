#!/usr/bin/env python3
"""
CarCheck Agent - One-Command Local Runner (No AWS Credentials Required)
Starts the FastAPI backend and serves the React 18 PWA frontend.
Seeds initial baseline and comparison inspections for instant demonstration.
"""

import os
import sys
import time
import hashlib
import cv2
import numpy as np
import uvicorn

from backend.core.models import (
    Inspection, Finding, CoverageItem, IntegritySummary, ChangeItem, ReportSchema, VIEWPOINTS
)
from backend.core.scoring import calculate_condition_score
from backend.adapters.db_local import LocalDbAdapter
from backend.adapters.storage_local import LocalStorageAdapter
from backend.adapters.signing_local import LocalEcdsaSigningAdapter
from backend.pdf.report_generator import generate_report_pdf

def seed_demo_data(db: LocalDbAdapter, storage: LocalStorageAdapter, signer: LocalEcdsaSigningAdapter):
    """Pre-populates demonstration data so the app has immediate rich reports on launch."""
    existing = db.list_inspections("usr_demo_buyer")
    if existing:
        return

    print("Initializing demo inspection fixtures...")

    # Create dummy images for evidence crops
    os.makedirs("data/evidence", exist_ok=True)
    os.makedirs("data/frames", exist_ok=True)
    os.makedirs("data/reports", exist_ok=True)

    # Generate synthetic car crop
    crop_img = np.full((300, 450, 3), 200, dtype=np.uint8)
    cv2.rectangle(crop_img, (50, 50), (400, 250), (60, 90, 180), -1) # Blue door panel
    # Scratch mark
    cv2.line(crop_img, (180, 120), (280, 170), (20, 30, 80), 3)
    # Orange bounding box overlay
    cv2.rectangle(crop_img, (160, 100), (300, 190), (0, 140, 255), 2)
    cv2.circle(crop_img, (160, 100), 5, (0, 140, 255), -1)

    _, crop_enc = cv2.imencode(".jpg", crop_img)
    crop_bytes = crop_enc.tobytes()

    # 1. Baseline Inspection (Toyota CH-R 2026)
    base_id = "insp_base_chr01"
    base_crop_key = f"evidence/{base_id}/fnd_base_dent.jpg"
    storage.save_bytes(base_crop_key, crop_bytes, "image/jpeg")

    base_finding = Finding(
        id="fnd_base_dent",
        type="dent",
        panel="front bumper",
        severity="minor",
        confidence=0.88,
        evidenceKey=base_crop_key,
        note="Pre-existing minor surface dent on lower front bumper."
    )

    base_coverage = [
        CoverageItem(viewpoint=vp, captured=True, frameCount=12, bestQualityScore=145.0)
        for vp in VIEWPOINTS
    ]

    base_integrity = IntegritySummary(
        challengePassed=True,
        inAppCapture=True,
        videoSha256="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        sha256Match=True,
        hardCutCount=0,
        plateConsistent=True,
        appearanceConsistent=True,
        trustLevel="VERIFIED",
        reasons=[
            "Single-use capture challenge verified in-frame",
            "Continuous camera stream with zero hard cuts",
            "Video SHA-256 checksum verified",
            "Vehicle appearance and license plate consistent throughout"
        ]
    )

    base_score, base_summary = calculate_condition_score([base_finding])

    base_report = ReportSchema(
        inspectionId=base_id,
        carMake="Toyota",
        carModel="CH-R",
        year=2026,
        inspectionDate="2026-10-21 14:30 UTC",
        score=base_score,
        scoreSummary=base_summary,
        coverage=base_coverage,
        findings=[base_finding],
        sellerQuestions=[
            f"[{base_finding.id}] Confirm whether the minor dent on the front bumper occurred during prior ownership."
        ],
        limitations=[
            "Screening tool only: not a certification of accident-free condition.",
            "Visual condition assessed from walkaround footage; confirm with a mechanic."
        ],
        trust=base_integrity.model_dump()
    )

    # Sign baseline report
    base_json_str = base_report.model_dump_json(exclude={"reportSignature", "reportHash", "pdfKey"})
    base_digest = hashlib.sha256(base_json_str.encode("utf-8")).digest()
    base_report.reportHash = hashlib.sha256(base_json_str.encode("utf-8")).hexdigest()
    base_report.reportSignature = signer.sign_digest(base_digest)

    base_pdf_bytes = generate_report_pdf(base_report, verify_url=f"/reports/{base_id}/verify")
    base_pdf_key = f"reports/{base_id}/report.pdf"
    storage.save_bytes(base_pdf_key, base_pdf_bytes, "application/pdf")
    base_report.pdfKey = base_pdf_key

    baseline_inspection = Inspection(
        inspectionId=base_id,
        userId="usr_demo_buyer",
        carMake="Toyota",
        carModel="CH-R",
        year=2026,
        type="BASELINE",
        trustMode=True,
        status="DONE",
        score=base_score,
        trustLevel="VERIFIED",
        videoSha256=base_integrity.videoSha256,
        reportSignature=base_report.reportSignature,
        reportHash=base_report.reportHash,
        retakeRound=0,
        createdAt="2026-10-21T14:30:00Z",
        updatedAt="2026-10-21T14:31:00Z",
        reportKey=base_pdf_key,
        report=base_report
    )
    db.save_inspection(baseline_inspection)
    db.save_findings(base_id, [base_finding])

    # 2. Return / Comparison Inspection (Handover Mode)
    comp_id = "insp_return_chr02"
    comp_crop_key = f"evidence/{comp_id}/fnd_new_scratch.jpg"
    storage.save_bytes(comp_crop_key, crop_bytes, "image/jpeg")

    new_finding = Finding(
        id="fnd_new_scratch",
        type="scratch",
        panel="right door",
        severity="moderate",
        confidence=0.88,
        evidenceKey=comp_crop_key,
        note="NEW scratch detected on right front door; not present in baseline inspection.",
        changeStatus="NEW",
        returnEvidenceKey=comp_crop_key
    )

    comp_changes = [
        ChangeItem(
            findingId=new_finding.id,
            changeStatus="NEW",
            panel="right door",
            type="scratch",
            confidence=0.88,
            baselineEvidenceKey=None,
            returnEvidenceKey=comp_crop_key,
            alignmentQuality=0.86,
            note="NEW scratch detected on right door (34mm length) not present in baseline pickup inspection."
        ),
        ChangeItem(
            findingId=base_finding.id,
            changeStatus="PRE-EXISTING",
            panel="front bumper",
            type="dent",
            confidence=0.91,
            baselineEvidenceKey=base_crop_key,
            returnEvidenceKey=comp_crop_key,
            alignmentQuality=0.82,
            note="Pre-existing minor dent on front bumper matched and verified from baseline footage."
        )
    ]

    comp_score, comp_summary = calculate_condition_score([base_finding, new_finding])

    comp_integrity = IntegritySummary(
        challengePassed=True,
        inAppCapture=True,
        videoSha256="7f83b1657ff1fc53b92dc18148a1d65dfc2d4b1fa3d677284addd200126d9069",
        sha256Match=True,
        hardCutCount=0,
        plateConsistent=True,
        appearanceConsistent=True,
        trustLevel="VERIFIED",
        reasons=[
            "Single-use capture challenge verified in-frame",
            "Zero hard cuts detected across walkaround",
            "Handover geometric registration succeeded with 86% inlier ratio",
            "Video SHA-256 verified and digitally signed"
        ]
    )

    comp_report = ReportSchema(
        inspectionId=comp_id,
        carMake="Toyota",
        carModel="CH-R",
        year=2026,
        inspectionDate="2026-10-23 09:15 UTC",
        score=comp_score,
        scoreSummary="Possible repaint / scratch: right front door. Handover mode highlights 1 NEW blemish.",
        coverage=base_coverage,
        findings=[base_finding, new_finding],
        sellerQuestions=[
            f"[{new_finding.id}] What caused the new scratch on the right front door during the return rental period?"
        ],
        limitations=[
            "Screening tool only: not a certification of accident-free condition.",
            "Changes detected between two walkaround scans; does not assign legal fault."
        ],
        trust=comp_integrity.model_dump(),
        changes=comp_changes
    )

    comp_json_str = comp_report.model_dump_json(exclude={"reportSignature", "reportHash", "pdfKey"})
    comp_digest = hashlib.sha256(comp_json_str.encode("utf-8")).digest()
    comp_report.reportHash = hashlib.sha256(comp_json_str.encode("utf-8")).hexdigest()
    comp_report.reportSignature = signer.sign_digest(comp_digest)

    comp_pdf_bytes = generate_report_pdf(comp_report, verify_url=f"/reports/{comp_id}/verify")
    comp_pdf_key = f"reports/{comp_id}/report.pdf"
    storage.save_bytes(comp_pdf_key, comp_pdf_bytes, "application/pdf")
    comp_report.pdfKey = comp_pdf_key

    comparison_inspection = Inspection(
        inspectionId=comp_id,
        userId="usr_demo_buyer",
        carMake="Toyota",
        carModel="CH-R",
        year=2026,
        type="COMPARISON",
        baselineId=base_id,
        trustMode=True,
        status="DONE",
        score=comp_score,
        trustLevel="VERIFIED",
        videoSha256=comp_integrity.videoSha256,
        reportSignature=comp_report.reportSignature,
        reportHash=comp_report.reportHash,
        retakeRound=0,
        createdAt="2026-10-23T09:15:00Z",
        updatedAt="2026-10-23T09:16:00Z",
        reportKey=comp_pdf_key,
        report=comp_report
    )
    db.save_inspection(comparison_inspection)
    db.save_findings(comp_id, [base_finding, new_finding])

    print("Demo fixtures seeded successfully (1 Baseline, 1 Return Handover Comparison).")

def main():
    print("=" * 72)
    print(" CARCHECK AGENT (v1.1) - LOCAL RUNNER")
    print("=" * 72)

    db = LocalDbAdapter("data/carcheck.db")
    storage = LocalStorageAdapter("data")
    signer = LocalEcdsaSigningAdapter("data/keys/report_signing_p256.pem")

    seed_demo_data(db, storage, signer)

    print("\nStarting local server...")
    print(" → PWA & API:     http://localhost:8000")
    print(" → Swagger Docs:  http://localhost:8000/docs")
    print(" → Verify Page:   http://localhost:8000/#/verify (or GET /reports/{id}/verify)")
    print("\nFeatures active:")
    print(" • Real OpenCV stages (Laplacian sharpness, exposure histogram, glare HSV)")
    print(" • Handover Mode (ORB 2000 + RANSAC homography, IoU bounding box matching)")
    print(" • Trust Layer (Challenge code, video SHA-256, Bhattacharyya hard cuts, ECDSA P-256 signing)")
    print(" • Bedrock Agent reasoning simulator with grounding guardrails and PDF report generator\n")

    uvicorn.run("backend.api.main:app", host="0.0.0.0", port=8000, reload=False)

if __name__ == "__main__":
    main()
