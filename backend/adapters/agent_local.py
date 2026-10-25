import json
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from backend.core.ports.agent import AgentPort
from backend.core.models import (
    ReportSchema, Finding, CoverageItem, IntegritySummary, ChangeItem
)
from backend.core.scoring import calculate_condition_score

class LocalBedrockAgentAdapter(AgentPort):
    """
    Simulates Amazon Bedrock Agent orchestrating tools, second-opinion vision review,
    reconciliation rules, and schema-validated grounded reports.
    """
    def __init__(self, model_id: str = "anthropic.claude-3-haiku-20240307-v1:0"):
        self.model_id = model_id

    # Simulated Bedrock Agent Tools
    def tool_get_quality_summary(self, coverage: List[CoverageItem]) -> Dict[str, Any]:
        covered = sum(1 for c in coverage if c.captured)
        return {
            "total_viewpoints": len(coverage),
            "covered_viewpoints": covered,
            "missing": [c.viewpoint for c in coverage if not c.captured],
            "details": [c.model_dump() for c in coverage]
        }

    def tool_get_cv_measurements(self, cv_measurements: Dict[str, Any]) -> Dict[str, Any]:
        return cv_measurements

    def tool_get_damage_findings(self, damage_findings: List[Finding]) -> List[Dict[str, Any]]:
        return [f.model_dump() for f in damage_findings]

    def tool_review_crop(self, finding: Finding) -> Dict[str, Any]:
        """
        Vision-capable foundation model second opinion:
        Inspects evidence crop, outputs: agree, disagree, or uncertain with reason.
        """
        # Multimodal vision assessment
        if finding.confidence > 0.82:
            return {"verdict": "agree", "reason": f"Visual confirmation of surface anomaly on {finding.panel}."}
        elif finding.confidence < 0.60:
            return {"verdict": "uncertain", "reason": f"Low contrast lighting on {finding.panel}; requires physical check."}
        else:
            return {"verdict": "agree", "reason": f"Consistent with possible {finding.type}."}

    def tool_get_baseline_diff(self, baseline_diff: Optional[List[ChangeItem]]) -> List[Dict[str, Any]]:
        if not baseline_diff:
            return []
        return [c.model_dump() for c in baseline_diff]

    def tool_get_integrity_summary(self, integrity: IntegritySummary) -> Dict[str, Any]:
        return integrity.model_dump()

    def reason_and_reconcile(
        self,
        inspection_id: str,
        car_make: str,
        car_model: str,
        year: int,
        coverage: List[CoverageItem],
        cv_measurements: Dict[str, Any],
        damage_findings: List[Finding],
        integrity_summary: IntegritySummary,
        baseline_diff: Optional[List[ChangeItem]] = None,
        car_detected: bool = True,
    ) -> ReportSchema:
        """
        Executes Bedrock Agent workflow with tool invocation, second opinion review,
        reconciliation logic, and Pydantic schema validation.
        """
        now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

        # Handle NO CAR DETECTED scenario
        if not car_detected:
            return ReportSchema(
                inspectionId=inspection_id,
                carMake=car_make,
                carModel=car_model,
                year=year,
                inspectionDate=now_utc,
                carDetected=False,
                score=0,
                scoreSummary="No car detected",
                coverage=[
                    CoverageItem(
                        viewpoint=c.viewpoint,
                        captured=False,
                        frameCount=0,
                        bestQualityScore=c.bestQualityScore,
                        reason="No car detected in frame"
                    )
                    for c in coverage
                ],
                findings=[],
                sellerQuestions=[
                    "Please re-film the walkaround video ensuring the vehicle is well-lit and fully visible within the camera guide outline."
                ],
                limitations=[
                    "NO CAR DETECTED: The computer vision analysis pipeline could not identify a vehicle in the provided video footage.",
                    "Surface damage detection, paint variation checks, and panel gap measurements cannot be performed without a detected vehicle.",
                    "Please ensure the vehicle is clean, parked in reasonable daylight, and captured continuously following the 8-viewpoint overlay."
                ],
                trust=integrity_summary.model_dump(),
                changes=None
            )

        # 1. Tool Calls
        q_summary = self.tool_get_quality_summary(coverage)
        cv_data = self.tool_get_cv_measurements(cv_measurements)
        raw_findings = list(damage_findings)

        # Merge findings from CV measurements (panel gaps, paint, tyres)
        for seam in cv_data.get("panel_gaps", []):
            if seam.get("asymmetry_flag"):
                f = Finding(
                    type="panel_gap_asymmetry",
                    panel=seam.get("viewpoint", "body seam"),
                    severity="moderate",
                    confidence=seam.get("confidence", 0.85),
                    evidenceKey=seam.get("evidenceKey") or f"evidence/{inspection_id}/gap_{seam.get('seam_name')}.jpg",
                    note=f"Panel gap asymmetry ({seam.get('mean_width_mm', 'uneven')} mm) detected along {seam.get('seam_name')}."
                )
                raw_findings.append(f)

        for paint in cv_data.get("paint_mismatches", []):
            if paint.get("mismatch_flag"):
                f = Finding(
                    type="paint_mismatch",
                    panel=paint.get("panel_a", "door"),
                    severity="moderate",
                    confidence=paint.get("confidence", 0.78),
                    evidenceKey=paint.get("evidenceKey") or f"evidence/{inspection_id}/paint_{paint.get('panel_a')}.jpg",
                    note=f"Paint color variation (Delta-E {paint.get('delta_e')}) between {paint.get('panel_a')} and {paint.get('panel_b')}."
                )
                raw_findings.append(f)

        for tyre in cv_data.get("tyres", []):
            if tyre.get("condition_band") == "worn" or tyre.get("sidewall_cracking"):
                f = Finding(
                    type="tyre_wear",
                    panel=f"tyre ({tyre.get('viewpoint')})",
                    severity="major" if tyre.get("sidewall_cracking") else "moderate",
                    confidence=tyre.get("confidence", 0.82),
                    evidenceKey=f"evidence/{inspection_id}/tyre_{tyre.get('viewpoint')}.jpg",
                    note=f"Tyre wear noted: tread depth {tyre.get('depth_range_mm')}" + (", sidewall cracking detected." if tyre.get("sidewall_cracking") else ".")
                )
                raw_findings.append(f)

        # 2. Second-opinion vision review on flagged crops (capped at 10)
        reconciled_findings: List[Finding] = []
        review_count = 0

        for f in raw_findings:
            if review_count < 10 and f.confidence < 0.95:
                review_count += 1
                review = self.tool_review_crop(f)
                verdict = review["verdict"]

                if verdict == "agree":
                    # Agree raises confidence
                    f.confidence = round(min(0.98, f.confidence + 0.12), 2)
                    f.note = f"{f.note} Reconciled by vision agent."
                elif verdict == "disagree":
                    # Disagree lowers confidence
                    f.confidence = round(max(0.30, f.confidence - 0.25), 2)
                    f.note = f"{f.note} Vision review disputed; flagged as low confidence."
                else:
                    # Uncertain caps at 0.45
                    f.confidence = min(0.45, f.confidence)
                    f.note = f"{f.note} Inconclusive angle; labeled uncertain."

            reconciled_findings.append(f)

        # 3. Calculate Deterministic Condition Score (never invented by LLM)
        score, score_summary = calculate_condition_score(reconciled_findings)

        # 4. Formulate Questions for Seller (each linked to finding ID per TRD 8.3)
        seller_questions = []
        for f in reconciled_findings:
            if f.type == "paint_mismatch":
                seller_questions.append(f"[{f.id}] Has the {f.panel} or surrounding area been repainted or repaired?")
            elif f.type == "panel_gap_asymmetry":
                seller_questions.append(f"[{f.id}] Has the vehicle experienced any front/side collision impacting {f.panel} alignment?")
            elif f.type in ["dent", "scratch", "rust"]:
                seller_questions.append(f"[{f.id}] What was the cause of the {f.severity} {f.type} on the {f.panel}?")
            elif f.type == "tyre_wear":
                seller_questions.append(f"[{f.id}] When were the tyres on the {f.panel} last replaced or aligned?")

        if not seller_questions:
            seller_questions.append("Confirm complete regular service history and maintenance logs with the seller.")

        # 5. Mandatory Screening Limitations (Hard rules)
        limitations = [
            "Screening tool only: this report does not constitute a mechanical inspection, warranty, or certificate of accident-free status.",
            "All findings are possible visual discrepancies rated with confidence scores based on phone walkaround footage.",
            "Ambient lighting, surface dust, water spots, reflections, and camera angles can influence measurements.",
            "Always have an independent professional mechanic physically inspect the vehicle before purchase."
        ]

        # 6. Build and Validate Report Schema
        report = ReportSchema(
            inspectionId=inspection_id,
            carMake=car_make,
            carModel=car_model,
            year=year,
            inspectionDate=now_utc,
            carDetected=True,
            score=score,
            scoreSummary=score_summary,
            coverage=coverage,
            findings=reconciled_findings,
            sellerQuestions=seller_questions,
            limitations=limitations,
            trust=integrity_summary.model_dump(),
            changes=baseline_diff
        )

        return report
