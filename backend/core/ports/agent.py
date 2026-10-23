from abc import ABC, abstractmethod
from typing import Dict, Any, List
from backend.core.models import ReportSchema, Finding, CoverageItem, IntegritySummary, ChangeItem

class AgentPort(ABC):
    @abstractmethod
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
    ) -> ReportSchema:
        """
        Orchestrates Bedrock Agent reasoning:
        1. Calls review_crop on flagged crops for second-opinion review.
        2. Applies reconciliation rules (adjust confidence, flag uncertainty).
        3. Formulates seller questions referencing finding IDs.
        4. Validates output against ReportSchema.
        5. Falls back to rule-based generation if needed.
        """
        pass
