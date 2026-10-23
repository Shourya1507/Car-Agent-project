from typing import List, Tuple
from backend.core.models import Finding

def calculate_condition_score(findings: List[Finding]) -> Tuple[int, str]:
    """
    Computes condition score: 100 minus confidence-weighted penalties per category.
    Max penalties:
      - Body damage (dent, scratch, rust, crack): 30
      - Panel-gap asymmetry: 20
      - Paint mismatch: 20
      - Tyres: 15
      - Glass: 15
    """
    body_damage_penalty = 0.0
    panel_gap_penalty = 0.0
    paint_penalty = 0.0
    tyre_penalty = 0.0
    glass_penalty = 0.0

    severity_weight = {
        "minor": 0.4,
        "moderate": 0.7,
        "major": 1.0
    }

    for f in findings:
        conf = max(0.0, min(1.0, f.confidence))
        sev = severity_weight.get(f.severity, 0.5)
        raw_penalty = conf * sev

        if f.type in ["dent", "scratch", "rust", "crack"]:
            # each body damage finding contributes up to 15 points towards max 30
            body_damage_penalty += raw_penalty * 15.0
        elif f.type == "panel_gap_asymmetry":
            panel_gap_penalty += raw_penalty * 20.0
        elif f.type == "paint_mismatch":
            paint_penalty += raw_penalty * 20.0
        elif f.type == "tyre_wear":
            tyre_penalty += raw_penalty * 15.0
        elif f.type == "glass_chip":
            glass_penalty += raw_penalty * 15.0

    # Cap at category maximums
    body_damage_penalty = min(30.0, body_damage_penalty)
    panel_gap_penalty = min(20.0, panel_gap_penalty)
    paint_penalty = min(20.0, paint_penalty)
    tyre_penalty = min(15.0, tyre_penalty)
    glass_penalty = min(15.0, glass_penalty)

    total_penalty = body_damage_penalty + panel_gap_penalty + paint_penalty + tyre_penalty + glass_penalty
    final_score = int(round(max(0.0, 100.0 - total_penalty)))

    # Generate one-line summary
    if final_score >= 90:
        summary = "Excellent visual condition with negligible detected imperfections."
    elif final_score >= 80:
        summary = "Good overall condition with minor cosmetic or localized wear items."
    elif final_score >= 65:
        summary = "Fair condition with noticeable surface wear or alignment variance requiring review."
    else:
        summary = "Significant physical wear, panel misalignment, or paint differences detected."

    return final_score, summary
