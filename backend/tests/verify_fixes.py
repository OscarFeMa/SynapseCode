import requests
import json
import time

BASE_URL = "http://127.0.0.1:8000/api/v1/debate"

def test_routing():
    print("--- Testing Routing ---")
    # Test /list (should work now)
    try:
        resp = requests.get(f"{BASE_URL}/list")
        print(f"/list: {resp.status_code}")
        if resp.status_code == 200:
            print(f"Sessions: {len(resp.json().get('sessions', []))}")
    except Exception as e:
        print(f"/list failed: {e}")

    # Test /reputation (should work now)
    try:
        resp = requests.get(f"{BASE_URL}/reputation")
        print(f"/reputation: {resp.status_code}")
    except Exception as e:
        print(f"/reputation failed: {e}")

def test_ultra_crossing():
    print("\n--- Testing Ultra Crossing ---")
    payload = {
        "topic": "Prueba de routing y corrección: ¿Pueden los robots tener ética?",
        "mode": "ultra_crossing"
    }
    try:
        print("Creating ultra debate (this might take a while)...")
        resp = requests.post(f"{BASE_URL}/create", json=payload, timeout=300)
        print(f"Status Code: {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            print(f"Session ID: {data.get('session_id')}")
            print(f"Status: {data.get('status')}")
            print(f"Turns: {len(data.get('turns', []))}")
            
            # Test report endpoint for this session
            session_id = data.get('session_id')
            report_resp = requests.get(f"{BASE_URL}/{session_id}/report")
            print(f"Report Status: {report_resp.status_code}")
            if report_resp.status_code == 200:
                print("Report found!")
        else:
            print(f"Error: {resp.text}")
    except Exception as e:
        print(f"Ultra crossing test failed: {e}")

if __name__ == "__main__":
    # Note: Backend must be running for this to work
    test_routing()
    # test_ultra_crossing() # Uncomment to run full test
