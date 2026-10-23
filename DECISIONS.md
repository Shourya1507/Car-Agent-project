# Architecture & Implementation Decisions (DECISIONS.md)

This document tracks technical decisions, trade-offs, and resolutions between the Product Requirements Document (PRD v1.1) and Technical Requirements Document (TRD v1.1) for CarCheck Agent.

---

## 1. Scope & Release Alignment
- **PRD/TRD Specification**: MVP focuses on P0 requirements (FR2 to FR8, FR12 to FR14) plus key differentiators FR19, FR20, FR23, FR24, and P1 items (FR9 paint, FR10 tyre, FR15 PDF, FR16 deletion, FR21, FR22, FR25, FR26).
- **Decision**: Deliverable 1 implements the complete local runnable pipeline with all CV stages (quality gate, viewpoints, damage detection, panel gap, paint delta-E, tyre tread, glass checks, continuity/cuts, plate consistency, baseline comparison, Bedrock agent reasoning & tool-use simulator, PDF report generation with ECDSA signature, share links, and public verification). Deliverable 2 provides the complete AWS CDK IaC infrastructure matching the v1.1 architecture diagram.

---

## 2. Ports and Adapters Architecture (Hexagonal Architecture)
- **Requirement**: Support one-command local execution with zero AWS credentials alongside seamless AWS CDK deployment.
- **Decision**: Define strict abstract domain interfaces (Ports) in `backend/core/ports/`:
  - `StoragePort`: Abstraction for object storage (`raw/`, `frames/`, `evidence/`, `reports/`).
    - Local Adapter: `LocalStorageAdapter` (stores in `data/`).
    - AWS Adapter: `S3StorageAdapter` (Amazon S3 with SSE-KMS, presigned PUT/GET).
  - `DbPort`: Abstraction for metadata and relational lookups (`Inspections`, `Findings`, `Captures`, `Challenges`, `ShareLinks`).
    - Local Adapter: `LocalDbAdapter` (SQLite with ACID transactions).
    - AWS Adapter: `DynamoDbAdapter` (Amazon DynamoDB on-demand).
  - `AuthPort`: User authentication and JWT claims extraction.
    - Local Adapter: `LocalAuthAdapter` (HMAC-SHA256 JWTs with instant demo login).
    - AWS Adapter: `CognitoAuthAdapter` (Amazon Cognito User Pool JWT verification).
  - `DetectorPort`: Vehicle surface damage detection (dent, scratch, rust, crack, etc.).
    - Local Adapter: `LocalDamageDetector` (OpenCV feature-based analysis + ONNX runtime fallback).
    - AWS Adapter: `SageMakerDetectorAdapter` (SageMaker real-time endpoint or Lambda container).
  - `AgentPort`: Agentic AI vision reasoning and structured evidence reconciliation.
    - Local Adapter: `LocalBedrockAgentAdapter` (full Bedrock agent simulator running the exact 7 tool schemas, guardrails, JSON schema validator, and rule-based fallback).
    - AWS Adapter: `BedrockAgentAdapter` (Amazon Bedrock Agent Runtime `InvokeAgent`).
  - `SigningPort`: Report hashing and cryptographic signing.
    - Local Adapter: `LocalEcdsaSigningAdapter` (ECDSA P-256 via Python `cryptography`).
    - AWS Adapter: `KmsSigningAdapter` (AWS KMS Asymmetric Signing Key `ECC_NIST_P256`).
  - `WorkflowPort`: Multi-stage processing orchestrator.
    - Local Adapter: `LocalWorkflowRunner` (Async Python state machine executing the exact Step Functions states and retake callbacks).
    - AWS Adapter: `StepFunctionsWorkflowAdapter` (AWS Step Functions Standard workflow).

---

## 3. Scale Reference for Panel-Gap Measurements
- **PRD/TRD Specification**: TRD 6.3 lists primary as ArUco marker (e.g. 10 cm), secondary as vehicle license plate, fallback as left-vs-right symmetry ratio.
- **Decision**: Implement all three:
  1. Primary: `cv2.aruco` detects 4x4 ArUco markers to compute `pixels_per_mm`.
  2. Secondary: Plate contour extraction to estimate scale if ArUco is absent.
  3. Fallback: Normalized left-versus-right relative seam asymmetry ratio with reduced confidence.

---

## 4. Paint & Color Mismatch (CIEDE2000)
- **PRD/TRD Specification**: TRD 6.5 specifies converting OpenCV BGR to CIELAB, discarding specular highlights ($L < 240$), computing median color per panel, and evaluating CIEDE2000 $\Delta E$ using `scikit-image`.
- **Decision**: OpenCV 8-bit LAB is scaled ($L \in [0, 255]$, $a,b \in [0, 255]$). Converted to standard CIELAB ranges ($L^* \in [0, 100]$, $a^* \in [-128, 127]$, $b^* \in [-128, 127]$) before passing to `skimage.color.deltaE_ciede2000`. Threshold $\Delta E > 3.0$ flags "possible repaint" with confidence weighting.

---

## 5. Handover Mode (Baseline vs Return Alignment)
- **PRD/TRD Specification**: TRD 21.1 defines 8 viewpoint pairing, ORB (2000 features), KNN match ratio test (0.75), RANSAC homography ($H$), with gates of $\ge 40$ inliers and inlier ratio $\ge 0.4$. If below gate, marked `UNCERTAIN` with reason `alignment failed`.
- **Decision**: Implement the exact algorithm from TRD 21.1:
  - Return bounding boxes are transformed using `cv2.perspectiveTransform(corners, H)`.
  - Transformed boxes matched against baseline detections using IoU $\ge 0.3$.
  - Classification:
    - Match found $\rightarrow$ `PRE-EXISTING`
    - In return only $\rightarrow$ `NEW`
    - In baseline only $\rightarrow$ `RESOLVED` (possible repair)
    - Low inliers or homography failure $\rightarrow$ `UNCERTAIN`

---

## 6. Trust Layer: Capture Challenge, Hashes & Cryptographic Signing
- **PRD/TRD Specification**: TRD 21.2 defines:
  - Capture challenge: 4-digit nonce and angle sequence, expires in 10 minutes, single use.
  - Video SHA-256: computed in browser via WebCrypto and verified at upload.
  - Hard cuts check: Bhattacharyya distance between consecutive frame histograms ($> 0.5$ threshold).
  - Appearance consistency: body color $\Delta E$ and plate consistency across frames.
  - Report signing: ECDSA P-256 signature over report JSON digest.
  - Trust level rules:
    - `VERIFIED`: challenge passed + no cuts + plate/appearance consistent + in-app capture + hash match.
    - `UNVERIFIED`: challenge failed OR $\ge 2$ consistency checks failed.
    - `PARTIAL`: otherwise.
- **Decision**: Implemented strictly according to TRD 21.2. Public verification endpoint `/reports/{id}/verify` recomputes the report SHA-256 digest and verifies the ECDSA public key signature.

---

## 7. Bedrock Agent & Grounding Guardrails
- **PRD/TRD Specification**: TRD 8.1-8.5 specifies Bedrock Agent tools (`get_quality_summary`, `get_cv_measurements`, `get_damage_findings`, `review_crop`, `save_report`, `get_baseline_diff`, `get_integrity_summary`).
- **Reconciliation Rules**:
  - Final confidence = detector/CV confidence adjusted by review verdict:
    - `agree` raises confidence (+15% up to 98%).
    - `disagree` lowers confidence (-25%).
    - `uncertain` caps confidence at 45%.
  - Every statement in the report MUST cite a finding ID.
  - Max 10 review crops per inspection.
  - Hard disclaimer: "Screening tool only: never claim certification or accident-free; confirm flagged items with a mechanic."
  - Output validated against strict Pydantic JSON schema; on failure, falls back to rule-based report generation.

---

## 8. Condition Scoring Algorithm
- **PRD/TRD Specification**: Condition score = 100 minus confidence-weighted penalties:
  - Body damage: max 30 penalty.
  - Panel gap asymmetry: max 20 penalty.
  - Paint mismatch: max 20 penalty.
  - Tyre wear: max 15 penalty.
  - Glass defects: max 15 penalty.
- **Decision**: Score is calculated deterministically by code (never hallucinated by the LLM) and always accompanied by its underlying evidence and findings.

---

## 9. Machine Learning & Damage Detection Pipeline
- **Problem**: Classical OpenCV filters (Sobel gradients, Canny, contours) reliably measure panel gaps and paint color deltas, but struggle to discriminate nuanced car surface disruptions (dents vs. scratches vs. cracks vs. shattered glass) across specular vehicle reflections and complex lighting.
- **Decision**: Implement a dual-tier detection strategy in `backend/adapters/detector_local.py` and `ml/`:
  1. **Primary Model**: Fine-tuned YOLOv8s trained on the CarDD (Car Damage Dataset) across 6 classes (`dent`, `scratch`, `crack`, `glass_shatter`, `lamp_broken`, `tyre_flat`).
  2. **Serving & Packaging**: Exported to ONNX (`model.ir_version = 10`, opset 17) and executed via `onnxruntime` CPU with 4 intra-op threads. This eliminates heavy PyTorch dependencies (>2 GB) in Lambda container images, ensuring cold starts < 250ms.
  3. **Deterministic Severity Banding**: In compliance with TRD Section 7, severity is deterministically calculated by measuring the ratio of the detected bounding box area to estimated visible vehicle panel area (<2% minor, 2-8% moderate, >8% major), avoiding LLM-invented severity ratings.
  4. **Graceful Fallback**: If the ONNX runtime model is unavailable, the system automatically falls back to OpenCV contour and gradient anomaly detection, ensuring zero downtime and continuous operation.

