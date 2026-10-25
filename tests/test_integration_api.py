import pytest
import time
from fastapi.testclient import TestClient
from backend.api.main import app

client = TestClient(app)

def test_full_inspection_lifecycle():
    # 1. Create Inspection (STANDARD)
    create_payload = {
        "carMake": "Toyota",
        "carModel": "CH-R",
        "year": 2026,
        "type": "STANDARD",
        "trustMode": True
    }
    res = client.post("/inspections", json=create_payload)
    assert res.status_code == 201
    data = res.json()
    inspection_id = data["inspectionId"]
    upload_url = data["uploadUrl"]
    assert "insp_" in inspection_id
    assert data["challenge"] is not None
    assert len(data["challenge"]["nonce"]) == 4

    # 2. Upload Video to direct upload route
    test_video_bytes = b"Sample video content for CarCheck integration testing"
    put_res = client.put(upload_url, content=test_video_bytes)
    assert put_res.status_code == 200

    # 3. Start Workflow
    start_res = client.post(f"/inspections/{inspection_id}/start")
    assert start_res.status_code == 202

    # Wait for async workflow execution with polling
    insp_data = {}
    for _ in range(30):
        get_res = client.get(f"/inspections/{inspection_id}")
        assert get_res.status_code == 200
        insp_data = get_res.json()
        if insp_data["status"] in ["DONE", "NEEDS_RETAKE"]:
            break
        time.sleep(0.5)

    if insp_data.get("status") == "NEEDS_RETAKE":
        # Test Retake Loop
        retake_res = client.post(
            f"/inspections/{inspection_id}/retake",
            json={"viewpoints": ["rear-left"]}
        )
        assert retake_res.status_code == 200
        for _ in range(30):
            insp_data = client.get(f"/inspections/{inspection_id}").json()
            if insp_data["status"] == "DONE":
                break
            time.sleep(0.5)

    assert insp_data["status"] == "DONE"
    assert insp_data["report"] is not None
    assert 0 <= insp_data["score"] <= 100
    assert insp_data["trustLevel"] in ["VERIFIED", "PARTIAL", "UNVERIFIED"]

    # Screening Disclaimer check (HARD RULE)
    limitations = insp_data["report"]["limitations"]
    assert any("Screening tool only" in l for l in limitations)

    # 5. Download Report PDF
    pdf_res = client.get(f"/inspections/{inspection_id}/report.pdf")
    assert pdf_res.status_code == 200
    assert pdf_res.headers["content-type"] == "application/pdf"
    assert len(pdf_res.content) > 1000

    # 6. Public Verification Endpoint (TRD 9 / 21.2)
    verify_res = client.get(f"/reports/{inspection_id}/verify")
    assert verify_res.status_code == 200
    v_data = verify_res.json()
    assert v_data["hashMatches"] is True
    assert v_data["signatureValid"] is True
    assert v_data["trustLevel"] in ["VERIFIED", "PARTIAL", "UNVERIFIED"]

    # 7. Create Share Link
    share_res = client.post(f"/inspections/{inspection_id}/share", json={"expiryHours": 48})
    assert share_res.status_code == 200
    token = share_res.json()["token"]

    # Access shared report without auth
    shared_report_res = client.get(f"/share/{token}")
    assert shared_report_res.status_code == 200
    assert shared_report_res.json()["inspectionId"] == inspection_id

    # 8. Delete Inspection
    del_res = client.delete(f"/inspections/{inspection_id}")
    assert del_res.status_code == 204

def test_handover_mode_comparison():
    # 1. Create and complete BASELINE inspection
    base_res = client.post("/inspections", json={
        "carMake": "Honda",
        "carModel": "Civic",
        "year": 2025,
        "type": "BASELINE",
        "trustMode": True
    })
    base_id = base_res.json()["inspectionId"]
    client.put(base_res.json()["uploadUrl"], content=b"Baseline walkaround video")
    client.post(f"/inspections/{base_id}/start")
    
    # Wait for baseline completion
    for _ in range(30):
        b_data = client.get(f"/inspections/{base_id}").json()
        if b_data.get("status") in ["DONE", "NEEDS_RETAKE"]:
            break
        time.sleep(0.5)

    # 2. Create COMPARISON inspection linked to baseline
    comp_res = client.post("/inspections", json={
        "carMake": "Honda",
        "carModel": "Civic",
        "year": 2025,
        "type": "COMPARISON",
        "baselineId": base_id,
        "trustMode": True
    })
    assert comp_res.status_code == 201
    comp_id = comp_res.json()["inspectionId"]
    client.put(comp_res.json()["uploadUrl"], content=b"Return walkaround video")
    client.post(f"/inspections/{comp_id}/start")

    # Wait for comparison completion
    for _ in range(30):
        c_data = client.get(f"/inspections/{comp_id}").json()
        if c_data.get("status") in ["DONE", "NEEDS_RETAKE"]:
            break
        time.sleep(0.5)

    # 3. Retrieve Comparison Diff
    comp_diff_res = client.get(f"/inspections/{comp_id}/comparison")
    assert comp_diff_res.status_code == 200
    diff_data = comp_diff_res.json()
    assert diff_data["baselineId"] == base_id
    assert "changes" in diff_data

def test_no_car_detected_workflow():
    # 1. Create inspection with NoCar make (triggers non-car walkaround simulation)
    create_res = client.post("/inspections", json={
        "carMake": "NoCar",
        "carModel": "BlankTest",
        "year": 2026,
        "type": "STANDARD",
        "trustMode": True
    })
    assert create_res.status_code == 201
    data = create_res.json()
    inspection_id = data["inspectionId"]
    upload_url = data["uploadUrl"]

    # 2. Upload dummy video
    client.put(upload_url, content=b"Non-car dummy video content")

    # 3. Start workflow
    start_res = client.post(f"/inspections/{inspection_id}/start")
    assert start_res.status_code == 202

    # 4. Poll until DONE
    insp_data = {}
    for _ in range(30):
        get_res = client.get(f"/inspections/{inspection_id}")
        assert get_res.status_code == 200
        insp_data = get_res.json()
        if insp_data.get("status") in ["DONE", "FAILED"]:
            break
        time.sleep(0.5)

    assert insp_data["status"] == "DONE"
    assert insp_data["carDetected"] is False
    assert insp_data["score"] == 0

    # 5. Check report details
    report = insp_data["report"]
    assert report is not None
    assert report["carDetected"] is False
    assert "No car detected" in report["scoreSummary"]
    assert len(report["findings"]) == 0

    # 6. Check PDF download
    pdf_res = client.get(f"/inspections/{inspection_id}/report.pdf")
    assert pdf_res.status_code == 200
    assert pdf_res.headers["content-type"] == "application/pdf"
    assert len(pdf_res.content) > 500

