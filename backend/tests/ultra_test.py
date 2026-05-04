import requests
import time

BASE_URL = "http://127.0.0.1:8000/api/v1/debate"

def log(msg):
    print(f"[*] {msg}")

def run_ultra_test():
    log("=== Synapse Council Ultra Crossing Test ===")
    
    payload = {
        "topic": "Test Ultra: ¿Es el libre albedrío una ilusión neuroquímica?",
        "mode": "ultra_crossing"
    }
    
    resp = requests.post(f"{BASE_URL}/create", json=payload)
    if resp.status_code not in (200, 202):
        log(f"[-] Failed to create ultra debate: {resp.status_code}")
        return
    
    session_id = resp.json().get("session_id")
    log(f"[+] Ultra Session created: {session_id}")
    
    start_time = time.time()
    while time.time() - start_time < 600: # 10 mins timeout
        resp = requests.get(f"{BASE_URL}/{session_id}")
        if resp.status_code == 200:
            data = resp.json()
            status = data.get("status")
            turns = len(data.get("turns", []))
            log(f"  Status: {status} ({turns} turns)")
            if status == "completed":
                log("[+] ULTRA DEBATE SUCCESSFUL")
                return
            if status == "failed":
                log("[-] ULTRA DEBATE FAILED")
                return
        time.sleep(20)
    
    log("[-] Timeout reached")

if __name__ == "__main__":
    run_ultra_test()
