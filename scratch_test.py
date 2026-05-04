import requests
payload = {"topic": "Prueba Rápida", "mode": "ultra_crossing"}
print("Enviando POST a /api/v1/debate/create...")
try:
    r = requests.post("http://127.0.0.1:8000/api/v1/debate/create", json=payload)
    print(f"Status: {r.status_code}")
    print(f"Response: {r.text}")
except Exception as e:
    print(f"Exception: {e}")
