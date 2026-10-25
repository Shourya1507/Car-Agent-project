import io
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether, HRFlowable
)
from backend.core.models import ReportSchema

def generate_report_pdf(report: ReportSchema, verify_url: str = "") -> bytes:
    """
    Generates professional tamper-evident vehicle condition report PDF using ReportLab.
    Includes vehicle metadata, score, screening disclaimer, findings, trust indicators,
    SHA-256 report hash, and ECDSA P-256 digital signature.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Heading1"],
        fontSize=20,
        leading=24,
        textColor=colors.HexColor("#0F172A")
    )
    subtitle_style = ParagraphStyle(
        "DocSubtitle",
        parent=styles["Normal"],
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#475569")
    )
    h2_style = ParagraphStyle(
        "Heading2Custom",
        parent=styles["Heading2"],
        fontSize=13,
        leading=16,
        textColor=colors.HexColor("#0F172A"),
        spaceBefore=10,
        spaceAfter=6
    )
    body_style = ParagraphStyle(
        "BodyCustom",
        parent=styles["Normal"],
        fontSize=9,
        leading=13,
        textColor=colors.HexColor("#1E293B")
    )
    disclaimer_style = ParagraphStyle(
        "DisclaimerCustom",
        parent=styles["Normal"],
        fontSize=8,
        leading=11,
        textColor=colors.HexColor("#991B1B"),
        backColor=colors.HexColor("#FEF2F2"),
        borderPadding=6
    )
    trust_style = ParagraphStyle(
        "TrustCustom",
        parent=styles["Normal"],
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#065F46"),
        backColor=colors.HexColor("#ECFDF5"),
        borderPadding=6
    )

    story = []

    # 1. Header
    header_data = [
        [
            Paragraph("<b>CARCHECK AGENT</b><br/><font size='8'>CONDITION SCREENING REPORT</font>", title_style),
            Paragraph(f"<b>Inspection ID:</b> {report.inspectionId}<br/><b>Date:</b> {report.inspectionDate}", subtitle_style)
        ]
    ]
    header_table = Table(header_data, colWidths=[340, 200])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(header_table)
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#0F172A"), spaceAfter=10))

    # 2. Mandatory Screening Disclaimer Banner
    disclaimer_text = (
        "<b>MANDATORY SCREENING DISCLAIMER:</b> Screening tool only. Never claim certification or accident-free status. "
        "This automated report identifies possible cosmetic, paint, and panel alignment discrepancies from smartphone video. "
        "Always confirm all flagged items with an independent professional mechanic prior to purchase or settlement."
    )
    story.append(Paragraph(disclaimer_text, disclaimer_style))
    story.append(Spacer(1, 10))

    # 3. Vehicle Overview & Score Box
    if not getattr(report, "carDetected", True):
        score_html = "<font size='22' color='#DC2626'><b>N/A</b></font><br/><font size='8' color='#991B1B'><b>No Car Detected</b></font>"
        trust_level = "UNVERIFIED"
        trust_color = "#DC2626"
        trust_html = f"<font size='14' color='{trust_color}'><b>{trust_level}</b></font><br/><font size='8'>No Vehicle Found</font>"
        summary_text = "<font color='#DC2626'><b>NO CAR DETECTED:</b> Computer vision analysis found no vehicle in the submitted footage. Defect scanning was aborted.</font>"
    else:
        score_color = "#16A34A" if report.score >= 80 else ("#D97706" if report.score >= 60 else "#DC2626")
        score_html = f"<font size='26' color='{score_color}'><b>{report.score}/100</b></font><br/><font size='9'>Condition Score</font>"
        trust_level = report.trust.get("trustLevel", "UNVERIFIED")
        trust_color = "#16A34A" if trust_level == "VERIFIED" else ("#D97706" if trust_level == "PARTIAL" else "#DC2626")
        trust_html = f"<font size='14' color='{trust_color}'><b>{trust_level}</b></font><br/><font size='8'>Trust Layer Integrity</font>"
        summary_text = report.scoreSummary

    overview_data = [
        [
            Paragraph(f"<b>Vehicle:</b> {report.year} {report.carMake} {report.carModel}<br/><b>Summary:</b> {summary_text}", body_style),
            Paragraph(score_html, body_style),
            Paragraph(trust_html, body_style)
        ]
    ]
    overview_table = Table(overview_data, colWidths=[320, 110, 110])
    overview_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#FEF2F2") if not getattr(report, "carDetected", True) else colors.HexColor("#F8FAFC")),
        ('BOX', (0,0), (-1,-1), 1 if not getattr(report, "carDetected", True) else 0.5, colors.HexColor("#FCA5A5") if not getattr(report, "carDetected", True) else colors.HexColor("#E2E8F0")),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor("#FCA5A5") if not getattr(report, "carDetected", True) else colors.HexColor("#E2E8F0")),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
        ('ALIGN', (1,0), (2,0), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(overview_table)
    story.append(Spacer(1, 12))

    # 4. Trust Layer Details
    trust_reasons = "<br/>• ".join(report.trust.get("reasons", ["Verified walkaround"]))
    trust_summary_text = (
        f"<b>Trust Layer Verification Details:</b><br/>• {trust_reasons}<br/>"
        f"<b>Video SHA-256:</b> <font face='Courier' size='7'>{report.trust.get('videoSha256', 'N/A')}</font>"
    )
    story.append(Paragraph(trust_summary_text, trust_style))
    story.append(Spacer(1, 10))

    # 5. Handover Mode Changes (if comparison)
    if report.changes:
        story.append(Paragraph("<b>Handover Mode: Baseline vs Return Comparison</b>", h2_style))
        changes_rows = [["Change Status", "Item / Panel", "Confidence", "Alignment / Note"]]
        for ch in report.changes:
            status_color = "#DC2626" if ch.changeStatus == "NEW" else ("#16A34A" if ch.changeStatus == "PRE-EXISTING" else "#475569")
            changes_rows.append([
                Paragraph(f"<font color='{status_color}'><b>{ch.changeStatus}</b></font>", body_style),
                Paragraph(f"{ch.type.replace('_', ' ').capitalize()} ({ch.panel})", body_style),
                Paragraph(f"{int(ch.confidence*100)}%", body_style),
                Paragraph(f"{ch.note} (align: {int(ch.alignmentQuality*100)}%)", body_style)
            ])
        changes_table = Table(changes_rows, colWidths=[90, 130, 60, 260])
        changes_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#E2E8F0")),
            ('BOTTOMPADDING', (0,0), (-1,-1), 4),
            ('TOPPADDING', (0,0), (-1,-1), 4),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#CBD5E1")),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ]))
        story.append(changes_table)
        story.append(Spacer(1, 10))

    # 6. Flagged Findings Table
    story.append(Paragraph(f"<b>Flagged Findings ({len(report.findings)})</b>", h2_style))
    if report.findings:
        findings_rows = [["ID", "Type", "Panel", "Severity", "Conf.", "Agent Note"]]
        for f in report.findings:
            findings_rows.append([
                Paragraph(f"<font face='Courier' size='7'>{f.id}</font>", body_style),
                Paragraph(f.type.replace('_', ' ').capitalize(), body_style),
                Paragraph(f.panel, body_style),
                Paragraph(f.severity.capitalize(), body_style),
                Paragraph(f"{int(f.confidence*100)}%", body_style),
                Paragraph(f.note, body_style)
            ])
        findings_table = Table(findings_rows, colWidths=[55, 85, 100, 50, 45, 205])
        findings_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#F1F5F9")),
            ('BOTTOMPADDING', (0,0), (-1,-1), 4),
            ('TOPPADDING', (0,0), (-1,-1), 4),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#E2E8F0")),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ]))
        story.append(findings_table)
    else:
        story.append(Paragraph("No significant visual defects or anomalies detected on examined panels.", body_style))
    story.append(Spacer(1, 10))

    # 7. Recommended Questions for the Seller
    story.append(Paragraph("<b>Recommended Questions for Seller / Inspector</b>", h2_style))
    questions_html = "<br/>".join([f"• {q}" for q in report.sellerQuestions])
    story.append(Paragraph(questions_html, body_style))
    story.append(Spacer(1, 14))

    # 8. Cryptographic Integrity & Public Verification Footer
    sig_short = (report.reportSignature[:48] + "...") if report.reportSignature else "UNAVAILABLE"
    hash_short = report.reportHash or "PENDING"
    footer_text = (
        f"<b>Cryptographic Report Integrity (ECDSA P-256):</b><br/>"
        f"<b>Report Digest (SHA-256):</b> <font face='Courier' size='7'>{hash_short}</font><br/>"
        f"<b>ECDSA Signature:</b> <font face='Courier' size='7'>{sig_short}</font><br/>"
        f"<b>Public Verification URL:</b> {verify_url or f'/reports/{report.inspectionId}/verify'}"
    )
    story.append(Paragraph(footer_text, subtitle_style))

    # Build PDF
    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()
