import requests
import time
import json
import sys

BASE_URL = "http://127.0.0.1:8000/api/v1/debate"

def log(msg):
    print(f"[*] {msg}")

def test_endpoint(name, method, path, payload=None):
    log(f"Testing {name} ({method} {path})...")
    url = f"{BASE_URL}{path}"
    try:
        if method == "GET":
            resp = requests.get(url, timeout=30)
        else:
            resp = requests.post(url, json=payload, timeout=300)
        
        if resp.status_code < 400:
            print(f"  [+] Success: {resp.status_code}")
            return resp.json()
        else:
            print(f"  [-] Failed: {resp.status_code} - {resp.text}")
            return None
    except Exception as e:
        print(f"  [!] Exception: {e}")
        return None

def wait_for_session(session_id, timeout_mins=10):
    log(f"Waiting for session {session_id} to complete...")
    start_time = time.time()
    while time.time() - start_time < timeout_mins * 60:
        resp = requests.get(f"{BASE_URL}/{session_id}")
        if resp.status_code == 200:
            data = resp.json()
            status = data.get("status")
            log(f"  Status: {status} ({len(data.get('turns', []))} turns)")
            if status == "completed":
                return data
            if status == "failed":
                log("  [-] Session FAILED")
                return data
        time.sleep(10)
    log("  [-] Timeout reached")
    return None

def run_suite():
    log("=== Synapse Council Exhaustive Test Suite ===")
    
    # 1. Test Static Routing
    test_endpoint("List Sessions", "GET", "/list")
    test_endpoint("Reputations", "GET", "/reputation")
    
    # 2. Test Standard Debate (Sequential)
    std_payload = {
        "topic": "Test Exhaustivo: Impacto de la computación cuántica en la criptografía actual.",
        "mode": "standard",
        "max_turns": 2 # Shortened for test speed
    }
    std_data = test_endpoint("Create Standard Debate", "POST", "/create", std_payload)
    if std_data:
        session_id = std_data.get("session_id")
        completed_data = wait_for_session(session_id)
        
        if completed_data:
            # Check report
            test_endpoint("Get Report", "GET", f"/{session_id}/report")
    
    # 3. Test Ultra Crossing (Parallel/Stages)
    ultra_payload = {
        "topic": "Test Ultra: ¿Es posible la consciencia artificial sin sustrato biológico?",
        "mode": "ultra_crossing"
    }
    # Note: Ultra crossing might take long
    ultra_data = test_endpoint("Create Ultra Debate", "POST", "/create", ultra_payload)
    if ultra_data:
        u_session_id = ultra_data.get("session_id")
        log(f"Ultra Session ID: {u_session_id}")
        # We don't wait for ultra in this script to avoid blocking forever if it's slow
        # but we check if it was created successfully
    
    log("=== Test Suite Finished ===")

if __name__ == "__main__":
    run_suite()
