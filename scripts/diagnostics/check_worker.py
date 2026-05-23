import socket
host = "<WORKER_IP>"
services = [("Ollama", 11434), ("LM Studio", 1234), ("Jan", 1337)]
for name, port in services:
    try:
        sock = socket.create_connection((host, port), timeout=5)
        sock.close()
        print(f"{name} :{port} -> OPEN")
    except Exception as e:
        print(f"{name} :{port} -> CLOSED ({e})")

# Also test Ollama API
import httpx
try:
    r = httpx.get(f"http://{host}:11434/api/tags", timeout=10)
    if r.status_code == 200:
        models = r.json().get("models", [])
        print(f"\nOllama models ({len(models)}):")
        for m in models:
            print(f"  - {m['name']}")
    else:
        print(f"Ollama API returned {r.status_code}")
except Exception as e:
    print(f"Ollama API failed: {e}")

# Test LM Studio API
try:
    r = httpx.get(f"http://{host}:1234/v1/models", timeout=10)
    if r.status_code == 200:
        data = r.json()
        models = data.get("data", [])
        print(f"\nLM Studio models ({len(models)}):")
        for m in models:
            print(f"  - {m.get('id', 'unknown')}")
    else:
        print(f"LM Studio API returned {r.status_code}")
except Exception as e:
    print(f"LM Studio API failed: {e}")

# Test Jan API
try:
    r = httpx.get(f"http://{host}:1337/v1/models", timeout=10)
    if r.status_code == 200:
        data = r.json()
        models = data.get("data", [])
        print(f"\nJan models ({len(models)}):")
        for m in models:
            print(f"  - {m.get('id', 'unknown')}")
    else:
        print(f"Jan API returned {r.status_code}")
except Exception as e:
    print(f"Jan API failed: {e}")
