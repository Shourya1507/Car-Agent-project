from __future__ import annotations
from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field
import time
import uuid

# Viewpoint definitions (8 classes per TRD 6.2)
VIEWPOINTS = [
    "front",
    "front-left",
    "left",
    "rear-left",
    "rear",
    "rear-right",
    "right",
    "front-right",
]

class BoundingBox(BaseModel):
    x1: float
    y1: float
    x2: float
    y2: float

class Finding(BaseModel):
    id: str = Field(default_factory=lambda: f"fnd_{uuid.uuid4().hex[:8]}")
    type: Literal["dent", "scratch", "rust", "crack", "paint_mismatch", "panel_gap_asymmetry", "tyre_wear", "glass_chip"]
    panel: str
    severity: Literal["minor", "moderate", "major"]
    confidence: float # 0.0 to 1.0
    evidenceKey: str
    note: str
    source: Literal["detector", "opencv", "reconciled"] = "detector"
    box: Optional[BoundingBox] = None
    # Handover mode fields
    changeStatus: Optional[Literal["NEW", "PRE-EXISTING", "RESOLVED", "UNCERTAIN"]] = None
    baselineFindingId: Optional[str] = None
    baselineEvidenceKey: Optional[str] = None
    returnEvidenceKey: Optional[str] = None

class QualityScore(BaseModel):
    sharpness: float
    exposure_ok: bool
    glare_ratio: float
    passed: bool
    reason: Optional[str] = None

class KeyFrame(BaseModel):
    frame_index: int
    timestamp_sec: float
    viewpoint: str
    sharpness: float
    exposure_ok: bool
    glare_ratio: float
    file_key: str

class CoverageItem(BaseModel):
    viewpoint: str
    captured: bool
    frameCount: int = 0
    bestQualityScore: float = 0.0
    reason: Optional[str] = None

class GapMeasurement(BaseModel):
    seam_name: str
    viewpoint: str
    mean_width_mm: Optional[float] = None
    std_dev_mm: Optional[float] = None
    relative_ratio: Optional[float] = None # left vs right relative ratio
    scale_used: Literal["aruco", "plate", "ratio_only"]
    asymmetry_flag: bool
    confidence: float
    evidenceKey: Optional[str] = None

class PaintMeasurement(BaseModel):
    panel_a: str
    panel_b: str
    viewpoint: str
    delta_e: float
    mismatch_flag: bool
    confidence: float
    evidenceKey: Optional[str] = None

class TyreMeasurement(BaseModel):
    viewpoint: str
    depth_range_mm: str # e.g. "3 to 5 mm"
    condition_band: Literal["good", "moderate", "worn"]
    sidewall_cracking: bool
    confidence: float
    evidenceKey: Optional[str] = None

class GlassMeasurement(BaseModel):
    viewpoint: str
    cracks_detected: bool
    chips_detected: bool
    confidence: float
    evidenceKey: Optional[str] = None

class IntegritySummary(BaseModel):
    challengePassed: bool
    challengeAttempts: int = 1
    matchedFrameTimeSec: Optional[float] = None
    inAppCapture: bool = True
    videoSha256: str
    sha256Match: bool = True
    hardCutCount: int = 0
    cutTimestamps: List[float] = []
    plateConsistent: bool = True
    plateConfidence: float = 0.95
    colourConsistencyScore: float = 0.92
    appearanceConsistent: bool = True
    trustLevel: Literal["VERIFIED", "PARTIAL", "UNVERIFIED"]
    reasons: List[str]

class ChangeItem(BaseModel):
    findingId: str
    changeStatus: Literal["NEW", "PRE-EXISTING", "RESOLVED", "UNCERTAIN"]
    panel: str
    type: str
    confidence: float
    baselineEvidenceKey: Optional[str] = None
    returnEvidenceKey: Optional[str] = None
    alignmentQuality: float # inlier ratio or RANSAC score
    note: str

class ReportSchema(BaseModel):
    inspectionId: str
    carMake: str
    carModel: str
    year: int
    inspectionDate: str
    score: int # 0 to 100
    scoreSummary: str
    coverage: List[CoverageItem]
    findings: List[Finding]
    sellerQuestions: List[str]
    limitations: List[str]
    trust: Dict[str, Any]
    changes: Optional[List[ChangeItem]] = None
    reportSignature: Optional[str] = None
    reportHash: Optional[str] = None
    pdfKey: Optional[str] = None

class Challenge(BaseModel):
    inspectionId: str
    nonce: str
    angleOrder: List[str]
    issuedAt: float = Field(default_factory=time.time)
    expiresAt: float = Field(default_factory=lambda: time.time() + 600) # 10 min TTL
    verified: bool = False
    attempts: int = 0

class Inspection(BaseModel):
    inspectionId: str
    userId: str
    carMake: str
    carModel: str
    year: int
    type: Literal["STANDARD", "BASELINE", "COMPARISON"] = "STANDARD"
    baselineId: Optional[str] = None
    trustMode: bool = True
    status: Literal["CREATED", "UPLOADED", "PROCESSING", "NEEDS_RETAKE", "DONE", "FAILED"] = "CREATED"
    score: Optional[int] = None
    trustLevel: Optional[Literal["VERIFIED", "PARTIAL", "UNVERIFIED"]] = None
    videoSha256: Optional[str] = None
    reportSignature: Optional[str] = None
    reportHash: Optional[str] = None
    retakeRound: int = 0
    missingViewpoints: List[str] = []
    createdAt: str
    updatedAt: str
    rawVideoKey: Optional[str] = None
    reportKey: Optional[str] = None
    report: Optional[ReportSchema] = None
    failureReason: Optional[str] = None

class ShareLink(BaseModel):
    token: str
    inspectionId: str
    createdAt: float = Field(default_factory=time.time)
    expiresAt: float
