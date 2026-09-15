"""
Phase 14 End-to-End Validation & Smoke Test Script
Executes full digital forensics workflow and validates zero-workspace storage.
"""

import hashlib
import os
from pathlib import Path
from starlette.testclient import TestClient

from backend.app.main import app

def run_phase14_smoke_test():
    print("=================================================================")
    print("      ARTIFACTX PHASE 14 END-TO-END SMOKE TEST                   ")
    print("=================================================================")
    
    client = TestClient(app)
    workspace_dir = Path("D:/ArtifactX").resolve()
    
    def count_workspace_pdfs():
        # Exclude .venv or external node_modules if any
        pdfs = []
        for p in workspace_dir.rglob("*.pdf"):
            if ".venv" not in str(p) and "node_modules" not in str(p):
                pdfs.append(p)
        return pdfs

    initial_pdfs = count_workspace_pdfs()
    print(f"[*] Initial workspace PDF count (excluding venv/node_modules): {len(initial_pdfs)}")

    # 1. Health Check
    print("\n[Step 1] Verifying System Health...")
    resp = client.get("/api/health")
    assert resp.status_code == 200, f"Health check failed: {resp.text}"
    health_data = resp.json()
    print(f"  -> Health: {health_data.get('status')}, Demo Mode: {health_data.get('demo_mode')}")
    assert health_data.get("demo_mode") is True, "Demo mode must be enabled for smoke testing"

    # 2. Create Demo Case
    print("\n[Step 2] Creating Demo Forensic Case...")
    resp = client.post("/api/demo/create-demo-case", json={
        "case_name": "Phase 14 E2E Test Case",
        "has_whatsapp": True,
        "has_telegram": True,
        "message_count": 50,
        "contact_count": 10
    })
    assert resp.status_code == 200, f"Failed to create demo case: {resp.text}"
    demo_res = resp.json()
    case_id = demo_res["case_id"]
    wa_evidence_id = demo_res.get("whatsapp", {}).get("evidence_id")
    tg_evidence_id = demo_res.get("telegram", {}).get("evidence_id")
    print(f"  -> Created Case ID: {case_id}")
    print(f"  -> WhatsApp Evidence ID: {wa_evidence_id}, Telegram Evidence ID: {tg_evidence_id}")
    print(f"  -> Correlation Edges: {demo_res.get('correlation_edges')}")

    try:
        # 3. Case Workspace & 4-Stage Stepper
        print("\n[Step 3] Verifying Case Workspace State & Pipeline Stage...")
        resp = client.get(f"/api/cases/{case_id}/workspace")
        assert resp.status_code == 200, f"Failed to get workspace: {resp.text}"
        ws = resp.json()
        print(f"  -> Case Name: {ws['case']['name']}")
        print(f"  -> Hash Integrity Score: {ws['hash_integrity_score']}%")
        print(f"  -> Analysis Stage: #{ws['analysis_stage']['stage_number']} - {ws['analysis_stage']['stage_name']}")
        print(f"  -> Summary: {ws['summary_counts']}")
        assert ws['summary_counts']['total_messages'] > 0
        assert ws['summary_counts']['timeline_events'] > 0

        # 4. Evidence List & Multi-Hash Verification
        print("\n[Step 4] Verifying Evidence and Multi-Hash Integrity Verification...")
        resp = client.get(f"/api/evidence?case_id={case_id}")
        assert resp.status_code == 200, f"Failed to fetch evidence list: {resp.text}"
        evidence_list = resp.json()
        print(f"  -> Found {len(evidence_list)} evidence items")
        assert len(evidence_list) >= 2, "Expected at least WhatsApp and Telegram evidence items"

        for ev in evidence_list:
            ev_id = ev["id"]
            resp = client.post(f"/api/evidence/{ev_id}/verify-hashes")
            assert resp.status_code == 200, f"Hash verification failed for evidence {ev_id}: {resp.text}"
            hash_res = resp.json()
            v_status = hash_res.get('verification_status')
            print(f"  -> Evidence {ev_id} ({ev['original_filename']}) Verification: status={v_status}")
            print(f"     Recorded SHA-256: {hash_res.get('main_file', {}).get('expected_sha256')}")
            assert hash_res.get("is_valid") is True, f"Evidence {ev_id} hash verification failed: {hash_res}"

        # 5. Artifact Inspection: EXIF & SQLite Inspector Endpoints
        print("\n[Step 5] Verifying Artifact Extraction & Inspector Endpoints...")
        if wa_evidence_id:
            resp = client.get(f"/api/evidence/{wa_evidence_id}/exif")
            assert resp.status_code == 200, f"EXIF extraction failed: {resp.text}"
            exif_data = resp.json()
            print(f"  -> EXIF response: total_images_inspected={exif_data.get('total_images_inspected', 0)}")

            resp = client.get(f"/api/evidence/{wa_evidence_id}/sqlite-inspect")
            assert resp.status_code == 200, f"SQLite inspect failed: {resp.text}"
            sqlite_data = resp.json()
            print(f"  -> SQLite inspect: status={sqlite_data.get('status')}, table_count={sqlite_data.get('table_count', 0)}")

        # 6. Interactive Chat Viewer & Deletions Detection
        print("\n[Step 6] Verifying Chat Thread Viewer and Inline Deletion Indicators...")
        resp = client.get(f"/api/cases/{case_id}/chats")
        assert resp.status_code == 200, f"Failed to fetch chats: {resp.text}"
        threads = resp.json()
        assert isinstance(threads, list), f"Expected list of threads, got: {type(threads)}"
        print(f"  -> Retrieved {len(threads)} chat threads across WhatsApp and Telegram")
        assert len(threads) > 0, "Expected chat threads to be populated"
        
        first_thread = threads[0]
        thread_jid = first_thread["jid"]
        app_name = first_thread.get("source_app") or first_thread.get("app")
        print(f"  -> Inspecting thread '{first_thread.get('name')}' ({thread_jid}) [App: {app_name}, Messages: {first_thread.get('message_count')}]")
        
        resp = client.get(f"/api/cases/{case_id}/chats/{thread_jid}/messages")
        assert resp.status_code == 200, f"Failed to fetch messages for thread {thread_jid}: {resp.text}"
        msgs_data = resp.json()
        messages_stream = msgs_data.get("messages", [])
        deletions = [m for m in messages_stream if m.get("is_deletion_marker")]
        print(f"  -> Merged message stream items: {len(messages_stream)}")
        print(f"  -> Inline deletion markers detected: {len(deletions)}")
        assert len(messages_stream) > 0, "Expected messages in thread"

        # 7. Timeline Density Histogram & Chronological Event Stream
        print("\n[Step 7] Verifying Chronological Timeline & Density Histogram...")
        resp = client.get(f"/api/timeline/cases/{case_id}/histogram")
        assert resp.status_code == 200, f"Failed to fetch histogram: {resp.text}"
        hist_data = resp.json()
        print(f"  -> Histogram: Total Events={hist_data.get('total_events')}, Buckets={len(hist_data.get('buckets', []))}")
        print(f"  -> App Breakdown: {hist_data.get('apps')}")
        assert hist_data.get("total_events", 0) > 0

        resp = client.get(f"/api/cases/{case_id}/timeline")
        assert resp.status_code == 200, f"Failed to fetch timeline events: {resp.text}"
        timeline_events = resp.json()
        print(f"  -> Retrieved {len(timeline_events)} chronological timeline events")
        assert len(timeline_events) > 0

        # 8. Correlation Engine & Cross-App Matrix
        print("\n[Step 8] Verifying Evidence Correlation Engine & Visualizer...")
        resp = client.get(f"/api/cases/{case_id}/correlation/entities")
        assert resp.status_code == 200, f"Failed to fetch correlation entities: {resp.text}"
        entities = resp.json()
        print(f"  -> Correlated Entities: {len(entities)}")

        resp = client.get(f"/api/cases/{case_id}/correlation/matrix")
        assert resp.status_code == 200, f"Failed to fetch correlation matrix: {resp.text}"
        matrix = resp.json()
        print(f"  -> Cross-App Correlated Message Pairs: {len(matrix)}")

        # 9. In-Memory Court-Ready Streaming PDF Generator & Zero-Workspace Check
        print("\n[Step 9] Verifying Court-Ready PDF Streaming & Zero-Workspace Storage...")
        report_payload = {
            "report_type": "full",
            "options": {
                "includeEvidence": True,
                "includeCustodyLog": True,
                "includeTimeline": True,
                "includeDeleted": True,
                "includeCorrelations": True
            },
            "leadAnalyst": "Special Agent J. Vance, EnCE",
            "agency": "Cyber Crime & Digital Forensics Unit",
            "caseNotes": "Phase 14 Comprehensive Validation Run. Zero workspace disk storage verified.",
            "swornDeclaration": True
        }
        resp = client.post(f"/api/cases/{case_id}/reports", json=report_payload)
        assert resp.status_code == 200, f"Report generation failed: {resp.text}"
        assert resp.headers.get("content-type") == "application/pdf", f"Invalid content type: {resp.headers.get('content-type')}"
        
        pdf_bytes = resp.content
        pdf_size = len(pdf_bytes)
        assert pdf_size > 5000, f"Generated PDF unexpectedly small: {pdf_size} bytes"
        assert pdf_bytes.startswith(b"%PDF-"), "Generated content does not have a valid PDF magic header"
        
        pdf_sha256 = hashlib.sha256(pdf_bytes).hexdigest()
        print(f"  -> Streamed Court PDF Size: {pdf_size:,} bytes")
        print(f"  -> Streamed PDF SHA-256: {pdf_sha256}")
        
        # CRITICAL VERIFICATION: Confirm Zero Workspace Storage
        post_pdfs = count_workspace_pdfs()
        print(f"  -> Post-generation workspace PDF count: {len(post_pdfs)}")
        new_pdfs = [p for p in post_pdfs if p not in initial_pdfs]
        if new_pdfs:
            raise AssertionError(f"VIOLATION: PDF files were written to workspace: {new_pdfs}")
        print("  -> CONFIRMED: Zero PDF files were written to project workspace!")

        # 10. In-App Report History Tracker
        print("\n[Step 10] Verifying In-App Report History Tracker...")
        resp = client.get(f"/api/cases/{case_id}/reports/history")
        assert resp.status_code == 200, f"Failed to get report history: {resp.text}"
        history_data = resp.json()
        reports_list = history_data.get("reports", []) if isinstance(history_data, dict) else history_data
        print(f"  -> Recorded Report History Items: {len(reports_list)}")
        assert len(reports_list) >= 1, "Expected at least one report history entry"
        latest_report = reports_list[0]
        print(f"  -> Report ID: {latest_report['report_id']}")
        print(f"  -> Filename: {latest_report['filename']}")
        print(f"  -> Total Pages: {latest_report.get('total_pages')}")
        db_sha256 = latest_report.get('sha256') or latest_report.get('sha256_hash')
        print(f"  -> DB Recorded SHA-256: {db_sha256}")
        assert db_sha256 == pdf_sha256, (
            f"SHA-256 mismatch between streamed PDF ({pdf_sha256}) and DB history ({db_sha256})"
        )
        print("  -> CONFIRMED: Cryptographic SHA-256 byte signature matches DB history record!")

        # 11. Re-Download from Report History Endpoint
        print("\n[Step 11] Verifying Re-Download Endpoint from Report History...")
        report_id = latest_report['report_id']
        resp = client.get(f"/api/cases/{case_id}/reports/{report_id}/download")
        assert resp.status_code == 200, f"Re-download failed: {resp.text}"
        assert resp.headers.get("content-type") == "application/pdf"
        redownload_sha256 = hashlib.sha256(resp.content).hexdigest()
        assert redownload_sha256 == pdf_sha256, "Re-downloaded PDF SHA-256 does not match original"
        print("  -> CONFIRMED: Re-download stream verified intact!")

        print("\n=================================================================")
        print("     ALL PHASE 14 SMOKE TESTS PASSED SUCCESSFULLY! (11/11)      ")
        print("=================================================================")

    finally:
        # Cleanup test case
        print(f"\n[Cleanup] Deleting test case {case_id}...")
        del_resp = client.delete(f"/api/demo/demo-case/{case_id}")
        if del_resp.status_code == 200:
            print(f"  -> Case {case_id} deleted successfully.")
        else:
            print(f"  -> Note: delete response code {del_resp.status_code}")

if __name__ == "__main__":
    run_phase14_smoke_test()
