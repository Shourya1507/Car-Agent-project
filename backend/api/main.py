from fastapi import FastAPI, Depends, HTTPException, Header, status, Response, Request
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Literal
import time
import uuid
import os
import hashlib
import random

from backend.core.models import (
    Inspection, Finding, Challenge, ShareLink, VIEWPOINTS
)
from backend.adapters.storage_local import LocalStorageAdapter
from backend.adapters.db_local import LocalDbAdapter
from backend.adapters.auth_local import LocalAuthAdapter
from backend.adapters.signing_local import LocalEcdsaSigningAdapter
from backend.adapters.detector_local import LocalDamageDetector
from backend.adapters.agent_local import LocalBedrockAgentAdapter
from backend.adapters.workflow_local import LocalWorkflowRunner

app = FastAPI(
    title="CarCheck Agent API",
    description="Evidence-backed used-car screening and handover inspection platform",
    version="1.1.0"
)

# Enable CORS for local Vite frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Ports and Adapters
storage = LocalStorageAdapter(base_dir="data")
db = LocalDbAdapter(db_path="data/carcheck.db")
auth = LocalAuthAdapter()
signer = LocalEcdsaSigningAdapter(key_path="data/keys/report_signing_p256.pem")
detector = LocalDamageDetector(storage=storage)
agent = LocalBedrockAgentAdapter()
workflow = LocalWorkflowRunner(
    storage=storage,
    db=db,
    detector=detector,
    agent=agent,
    signer=signer
)

# Auth dependency
def get_current_user(authorization: Optional[str] = Header(None)) -> str:
    if not authorization:
        # Fallback to default demo user for frictionless local run
        return "usr_demo_buyer"

    token = authorization.replace("Bearer ", "").strip()
    payload = auth.verify_token(token)
    if not payload:
        return "usr_demo_buyer"
    return payload.get("sub", "usr_demo_buyer")

# Request Schemas
class CreateInspectionRequest(BaseModel):
    carMake: str
    carModel: str
    year: int
    type: Literal["STANDARD", "BASELINE", "COMPARISON"] = "STANDARD"
    baselineId: Optional[str] = None
    trustMode: bool = True
    videoSha256: Optional[str] = None

class ShareRequest(BaseModel):
    expiryHours: int = 72

class RetakeRequest(BaseModel):
    viewpoints: List[str]

# API Endpoints per TRD Section 9

@app.post("/auth/demo-login")
def demo_login(email: str = "demo@carcheck.local"):
    """Issues local JWT token for instant testing."""
    user_id = f"usr_{hashlib.md5(email.encode()).hexdigest()[:8]}"
    token = auth.create_token(user_id=user_id, email=email)
    return {
        "accessToken": token,
        "tokenType": "Bearer",
        "userId": user_id,
        "email": email
    }

@app.post("/inspections", status_code=status.HTTP_201_CREATED)
def create_inspection(
    req: CreateInspectionRequest,
    user_id: str = Depends(get_current_user)
):
    """Creates a new inspection record and issues pre-signed upload URL."""
    if req.type == "COMPARISON":
        if not req.baselineId:
            raise HTTPException(status_code=400, detail="baselineId is required for COMPARISON inspections.")
        baseline = db.get_inspection(user_id, req.baselineId)
        if not baseline:
            raise HTTPException(status_code=404, detail="Baseline inspection not found or not owned by user.")

    inspection_id = f"insp_{uuid.uuid4().hex[:10]}"
    now_str = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    inspection = Inspection(
        inspectionId=inspection_id,
        userId=user_id,
        carMake=req.carMake,
        carModel=req.carModel,
        year=req.year,
        type=req.type,
        baselineId=req.baselineId,
        trustMode=req.trustMode,
        videoSha256=req.videoSha256,
        status="CREATED",
        createdAt=now_str,
        updatedAt=now_str
    )
    db.save_inspection(inspection)

    # Issue single-use challenge if trustMode is active
    challenge_data = None
    if req.trustMode:
        nonce = f"{random.randint(1000, 9999)}"
        angle_order = list(VIEWPOINTS)
        random.shuffle(angle_order)
        challenge = Challenge(
            inspectionId=inspection_id,
            nonce=nonce,
            angleOrder=angle_order,
            issuedAt=time.time(),
            expiresAt=time.time() + 600,
            verified=False
        )
        db.save_challenge(challenge)
        challenge_data = {
            "nonce": nonce,
            "angleOrder": angle_order,
            "expiresInSec": 600
        }

    raw_key = f"raw/{user_id}/{inspection_id}/walkaround.mp4"
    upload_url = storage.get_upload_url(raw_key, expires_in_sec=600)

    return {
        "inspectionId": inspection_id,
        "uploadUrl": upload_url,
        "rawVideoKey": raw_key,
        "expiresInSec": 600,
        "challenge": challenge_data
    }

@app.get("/inspections")
def list_inspections(user_id: str = Depends(get_current_user)):
    """Lists inspections for the authenticated user."""
    inspections = db.list_inspections(user_id)
    return {"inspections": [i.model_dump() for i in inspections]}

@app.post("/inspections/{id}/start", status_code=status.HTTP_202_ACCEPTED)
def start_inspection(id: str, user_id: str = Depends(get_current_user)):
    """Starts asynchronous processing workflow after client video upload."""
    inspection = db.get_inspection(user_id, id)
    if not inspection:
        raise HTTPException(status_code=404, detail="Inspection not found.")

    inspection.status = "PROCESSING"
    db.save_inspection(inspection)

    exec_id = workflow.start_inspection_workflow(id)
    return {
        "inspectionId": id,
        "status": "PROCESSING",
        "executionId": exec_id
    }

@app.get("/inspections/{id}")
def get_inspection(id: str, user_id: str = Depends(get_current_user)):
    """Retrieves current inspection state, retake list, or final report."""
    inspection = db.get_inspection(user_id, id)
    if not inspection:
        raise HTTPException(status_code=404, detail="Inspection not found.")

    resp: Dict[str, Any] = {
        "inspectionId": inspection.inspectionId,
        "status": inspection.status,
        "carMake": inspection.carMake,
        "carModel": inspection.carModel,
        "year": inspection.year,
        "type": inspection.type,
        "trustMode": inspection.trustMode,
        "score": inspection.score,
        "trustLevel": inspection.trustLevel,
        "retakeRound": inspection.retakeRound,
        "missingViewpoints": inspection.missingViewpoints,
        "failureReason": inspection.failureReason,
        "createdAt": inspection.createdAt
    }

    if inspection.status == "DONE" and inspection.report:
        resp["report"] = inspection.report.model_dump()
        resp["reportUrl"] = f"/inspections/{id}/report.pdf"

    return resp

@app.post("/inspections/{id}/retake")
def request_retake_upload(
    id: str,
    req: RetakeRequest,
    user_id: str = Depends(get_current_user)
):
    """Issues new upload URLs for requested retake viewpoints and resumes workflow."""
    inspection = db.get_inspection(user_id, id)
    if not inspection:
        raise HTTPException(status_code=404, detail="Inspection not found.")

    urls = {}
    for vp in req.viewpoints:
        key = f"frames/{id}/{vp}/retake.jpg"
        urls[vp] = storage.get_upload_url(key)

    workflow.resume_retake(id, new_frames_uploaded=True)

    return {
        "inspectionId": id,
        "retakeRound": inspection.retakeRound + 1,
        "uploadUrls": urls
    }

@app.get("/inspections/{id}/report.pdf")
def get_report_pdf(id: str, user_id: str = Depends(get_current_user)):
    """Downloads official signed PDF condition report."""
    inspection = db.get_inspection(user_id, id)
    if not inspection:
        # Check if requested by shared token or public check
        inspection = db.get_inspection_by_id(id)
    if not inspection or not inspection.reportKey:
        raise HTTPException(status_code=404, detail="Report PDF not available yet.")

    pdf_bytes = storage.get_bytes(inspection.reportKey)
    if not pdf_bytes:
        raise HTTPException(status_code=404, detail="Report PDF file not found on storage.")

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=carcheck_{inspection.carMake}_{inspection.carModel}_{id}.pdf"}
    )

@app.post("/inspections/{id}/share")
def create_share_link(
    id: str,
    req: ShareRequest = ShareRequest(),
    user_id: str = Depends(get_current_user)
):
    """Generates read-only share link token with TTL."""
    inspection = db.get_inspection(user_id, id)
    if not inspection:
        raise HTTPException(status_code=404, detail="Inspection not found.")

    token = f"sh_{uuid.uuid4().hex}"
    expires_at = time.time() + (req.expiryHours * 3600)
    link = ShareLink(
        token=token,
        inspectionId=id,
        expiresAt=expires_at
    )
    db.save_share_link(link)

    return {
        "token": token,
        "shareUrl": f"/share/{token}",
        "expiresAt": expires_at
    }

@app.get("/share/{token}")
def get_shared_report(token: str):
    """Public read-only report viewer without authentication."""
    link = db.get_share_link(token)
    if not link or link.expiresAt < time.time():
        raise HTTPException(status_code=404, detail="Share link is invalid or expired.")

    inspection = db.get_inspection_by_id(link.inspectionId)
    if not inspection or not inspection.report:
        raise HTTPException(status_code=404, detail="Report not ready.")

    return {
        "inspectionId": inspection.inspectionId,
        "carMake": inspection.carMake,
        "carModel": inspection.carModel,
        "year": inspection.year,
        "score": inspection.score,
        "trustLevel": inspection.trustLevel,
        "report": inspection.report.model_dump()
    }

@app.get("/inspections/{id}/challenge")
def get_challenge(id: str, user_id: str = Depends(get_current_user)):
    """Retrieves single-use capture challenge (nonce and angle order)."""
    inspection = db.get_inspection(user_id, id)
    if not inspection:
        raise HTTPException(status_code=404, detail="Inspection not found.")

    challenge = db.get_challenge(id)
    if not challenge or challenge.expiresAt < time.time():
        # Issue fresh challenge
        nonce = f"{random.randint(1000, 9999)}"
        angle_order = list(VIEWPOINTS)
        random.shuffle(angle_order)
        challenge = Challenge(
            inspectionId=id,
            nonce=nonce,
            angleOrder=angle_order,
            issuedAt=time.time(),
            expiresAt=time.time() + 600
        )
        db.save_challenge(challenge)

    return {
        "nonce": challenge.nonce,
        "angleOrder": challenge.angleOrder,
        "expiresAt": challenge.expiresAt,
        "verified": challenge.verified
    }

@app.post("/inspections/{id}/challenge/verify")
def verify_challenge(id: str, user_id: str = Depends(get_current_user)):
    """Simulates/records verification of the single-use challenge code."""
    challenge = db.get_challenge(id)
    if not challenge:
        raise HTTPException(status_code=404, detail="No active challenge for this inspection.")
    challenge.verified = True
    db.save_challenge(challenge)
    return {"verified": True, "nonce": challenge.nonce}

@app.get("/inspections/{id}/comparison")
def get_comparison(id: str, user_id: str = Depends(get_current_user)):
    """Retrieves Handover Mode comparison diff against linked baseline."""
    inspection = db.get_inspection(user_id, id)
    if not inspection:
        raise HTTPException(status_code=404, detail="Inspection not found.")
    if inspection.type != "COMPARISON" or not inspection.baselineId:
        raise HTTPException(status_code=400, detail="Inspection is not in COMPARISON mode.")

    changes = inspection.report.changes if inspection.report else []
    return {
        "inspectionId": id,
        "baselineId": inspection.baselineId,
        "changes": [c.model_dump() for c in (changes or [])]
    }

@app.get("/reports/{id}/verify")
def verify_report(id: str):
    """
    Public verification endpoint (TRD 9, 21.2):
    Recomputes SHA-256 digest of report JSON and validates ECDSA P-256 digital signature.
    """
    inspection = db.get_inspection_by_id(id)
    if not inspection or not inspection.report:
        raise HTTPException(status_code=404, detail="Report not found or not finalized.")

    report = inspection.report
    # Recompute SHA-256 digest of canonical report JSON
    report_json_str = report.model_dump_json(exclude={"reportSignature", "reportHash", "pdfKey"})
    expected_digest = hashlib.sha256(report_json_str.encode("utf-8")).digest()
    expected_hash = hashlib.sha256(report_json_str.encode("utf-8")).hexdigest()

    signature_valid = False
    if report.reportSignature:
        signature_valid = signer.verify_signature(expected_digest, report.reportSignature)

    return {
        "inspectionId": id,
        "reportHash": report.reportHash,
        "computedHash": expected_hash,
        "hashMatches": (report.reportHash == expected_hash),
        "signatureValid": signature_valid,
        "trustLevel": inspection.trustLevel or "UNVERIFIED",
        "videoSha256": inspection.videoSha256,
        "carMake": inspection.carMake,
        "carModel": inspection.carModel,
        "year": inspection.year,
        "inspectionDate": report.inspectionDate,
        "screeningDisclaimer": "Screening tool only: not a certification of accident-free condition.",
        "publicKeyPem": signer.get_public_key_pem()
    }

@app.delete("/inspections/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_inspection(id: str, user_id: str = Depends(get_current_user)):
    """Deletes inspection, findings, challenges, and related media from storage."""
    deleted = db.delete_inspection(user_id, id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Inspection not found.")

    # Remove storage files asynchronously / directly
    storage.delete_prefix(f"raw/{user_id}/{id}")
    storage.delete_prefix(f"frames/{id}")
    storage.delete_prefix(f"evidence/{id}")
    storage.delete_prefix(f"reports/{id}")

    return Response(status_code=status.HTTP_204_NO_CONTENT)

# Direct file upload endpoint for local runner
@app.put("/upload/{file_path:path}")
async def upload_file(file_path: str, request: Request):
    """Receives binary PUT upload from frontend."""
    body = await request.body()
    storage.save_bytes(file_path, body)
    return {"status": "SUCCESS", "path": file_path, "bytes": len(body)}

# Media serving endpoint
@app.get("/media/{file_path:path}")
def serve_media(file_path: str):
    data = storage.get_bytes(file_path)
    if not data:
        raise HTTPException(status_code=404, detail="Media not found")
    media_type = "image/jpeg"
    if file_path.endswith(".pdf"):
        media_type = "application/pdf"
    elif file_path.endswith(".mp4"):
        media_type = "video/mp4"
    return Response(content=data, media_type=media_type)

# Mount frontend/dist for single-command full-stack serving
from fastapi.staticfiles import StaticFiles
frontend_dist = os.path.abspath("frontend/dist")
if os.path.exists(frontend_dist):
    app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="frontend")

