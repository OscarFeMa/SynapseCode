# Troubleshooting Guide — SynapseCode

## Index

1. [Server won't start](#server-wont-start)
2. [Ollama not responding](#ollama-not-responding)
3. [Agent errors](#agent-errors)
4. [Debate not saving](#debate-not-saving)
5. [Supabase not syncing](#supabase-not-syncing)
6. [Web interface not loading](#web-interface-not-loading)
7. [Performance issues](#performance-issues)

---

## Server won't start

### Symptoms
- Backend script exits immediately
- "No virtual environment found" error
- Port 8000 already in use

### Solutions

#### 1. Create virtual environment
```bash
cd <path-to-SynapseCode>
python -m venv venv
venv\Scripts\pip install -r backend\requirements.txt
```

#### 2. Port busy
```bash
# Find process using port 8000
netstat -ano | findstr :8000

# Kill it (replace PID)
taskkill /PID [PID_NUMBER] /F
```

#### 3. Check Python
```bash
python --version
# Must show Python 3.11+
```

---

## Ollama not responding

### Solutions

#### 1. Verify Ollama is running
```bash
curl http://<WORKER_IP>:11434/api/tags
```

#### 2. Check Worker connectivity
```bash
# From Master
curl http://<WORKER_IP>:11434/api/generate -d '{"model":"llama3","prompt":"hi"}'
```

#### 3. Restart Ollama on Worker
```bash
ollama serve
```

---

## Agent errors

### Common issues
- **"ollama.generate.error"**: Ollama not running or model not found
- **"Connection timeout"**: Worker unreachable or network issue
- **"Model not available"**: Run `ollama pull <model>` on Worker

### Check model availability
```bash
curl http://<WORKER_IP>:11434/api/tags
```

---

## Debate not saving

### Solutions
- Check `data/` directory exists and is writable
- Verify SQLite path in `.env` (`DATABASE_URL`)
- Check logs for database errors:
```bash
.\venv\Scripts\python -c "from backend.database.local_db import get_db; print('DB ok')"
```

---

## Supabase not syncing

### Check connection
```bash
curl http://localhost:8000/api/v1/debate/cloud/status
```

### Verify env vars
- `SUPABASE_URL` and `SUPABASE_ANON_KEY` must be set in `.env`
- Tables must exist (run `supabase_schema.sql` via Supabase SQL Editor)

### Force sync
```bash
curl -X POST http://localhost:8000/api/v1/debate/cloud/sync/all
```

---

## Web interface not loading

### Check backend is running
```bash
curl http://localhost:8000/health
```

### In production (nginx)
- Verify nginx is running: `systemctl status nginx`
- Check nginx config: `nginx -t`
- Check tunnel: `cloudflared tunnel list`

---

## Performance issues

### Symptoms
- Slow debate generation
- High RAM/CPU usage
- Timeouts

### Solutions
1. **Reduce concurrent debates**: Set `MAX_CONCURRENT_SESSIONS=2` in `.env`
2. **Use smaller models**: Prefer 7B over 13B+ models for faster inference
3. **Enable semantic cache**: Set `AGENT_REPUTATION_ENABLED=true`
4. **Worker optimization**: Run `scripts/windows/optimize-worker.bat` on Worker PC
