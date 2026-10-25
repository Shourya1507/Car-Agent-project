import pytest
import subprocess
import time
import os
import sys
import httpx

playwright_module = pytest.importorskip("playwright", reason="playwright is not installed in the environment")
from playwright.sync_api import sync_playwright, Page, expect

@pytest.fixture(scope="module")
def api_server():
    """Starts FastAPI server hosting both backend API and static frontend build."""
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "backend.api.main:app", "--port", "8000", "--host", "127.0.0.1"],
        cwd=os.path.abspath(".")
    )
    url = "http://127.0.0.1:8000"
    # Poll until server responds
    for _ in range(30):
        try:
            r = httpx.get(url, timeout=1.0)
            if r.status_code < 500:
                break
        except Exception:
            time.sleep(0.5)
    time.sleep(1.0)
    yield url
    proc.terminate()
    try:
        proc.wait(timeout=3)
    except Exception:
        proc.kill()

def test_pwa_landing_and_features(api_server):
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(channel="msedge", headless=True)
        except Exception:
            browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # 1. Load Landing Page
        page.goto(api_server, wait_until="networkidle")
        
        # Verify Brand and Navigation
        expect(page.locator("text=CarCheck Agent")).to_be_visible()
        expect(page.locator("text=Trust Layer Active")).to_be_visible()

        # Verify Hero Section per UI Design Page 1
        expect(page.locator("text=See what the seller")).to_be_visible()
        expect(page.locator("text=/ TRUST LAYER")).to_be_visible()
        expect(page.locator("text=Condition Score")).to_be_visible()
        expect(page.locator("text=Handover Mode")).to_be_visible()

        # 2. Open Inspection Modal
        page.locator("button:has-text('Start Inspection')").click()
        expect(page.locator("text=Create Vehicle Inspection")).to_be_visible()
        expect(page.locator("text=Trust Layer Mode")).to_be_visible()
        
        # Close modal
        page.locator(".fixed button").first.click()
        time.sleep(0.5)

        # 3. Navigate to Handover Mode Tab via Nav Bar
        page.locator("nav button:has-text('HANDOVER')").click()
        expect(page.locator("text=Baseline vs Return Comparison")).to_be_visible()
        expect(page.locator("text=NEW Damage").first).to_be_visible()
        expect(page.locator("text=PRE-EXISTING").first).to_be_visible()
        expect(page.locator("text=RESOLVED").first).to_be_visible()
        expect(page.locator("text=UNCERTAIN").first).to_be_visible()

        # 4. Navigate to Public Verify Tab via Nav Bar
        page.locator("nav button:has-text('VERIFY')").click()
        expect(page.locator("text=Public Report Verification")).to_be_visible()
        expect(page.locator("input[placeholder*='Enter Inspection ID']")).to_be_visible()

        browser.close()
