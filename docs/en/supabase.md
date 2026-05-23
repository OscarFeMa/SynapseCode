# Supabase Setup for SynapseCode

## Step 1: Create Tables in Supabase

1. Go to [Supabase SQL Editor](https://supabase.com/dashboard/project/jdbzjapshomatwyasmig/sql)
2. Copy and paste the contents of `supabase_schema.sql`
3. Execute the script

## Step 2: Verify Connection

After restarting the Master, test the connection:

```bash
curl http://localhost:8000/api/v1/debate/cloud/status
```

Expected response:
```json
{
  "enabled": true,
  "url": "https://jdbzjapshomatwyasmig.supabase.co",
  "status": "connected",
  "tables_accessible": true
}
```

## Step 3: Run a Test Debate

```bash
curl -X POST http://localhost:8000/api/v1/debate/create \
  -H "Content-Type: application/json" \
  -d '{"topic":"Sync test","mode":"local_only"}'
```

The debate will sync automatically with Supabase upon completion.

## Step 4: Verify in Supabase

1. Go to [Table Editor](https://supabase.com/dashboard/project/jdbzjapshomatwyasmig/editor)
2. Check the tables:
   - `sequential_debates` — should contain the created debate
   - `sequential_debate_turns` — should contain the 4 turns

## Supabase Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /api/v1/debate/cloud/status` | Connection status |
| `GET /api/v1/debate/cloud/list` | List cloud debates |
| `GET /api/v1/debate/cloud/{id}` | Get specific debate from cloud |
| `POST /api/v1/debate/cloud/sync/{id}` | Force manual sync |

## Table Schema

### sequential_debates
- `id` (UUID, PK)
- `topic` (Text)
- `mode` (Text: standard, local_only, hybrid)
- `status` (Text: created, running, completed, failed)
- `total_turns`, `total_tokens_in`, `total_tokens_out`, `total_latency_ms`
- `final_verdict` (Text)
- `created_at`, `completed_at`, `synced_at`

### sequential_debate_turns
- `id` (UUID, PK)
- `debate_id` (UUID, FK)
- `turn_number` (Integer)
- `agent_id`, `agent_name`, `agent_role`
- `model`, `provider`, `node`, `engine`
- `prompt_sent`, `response_received`
- `tokens_in`, `tokens_out`, `latency_ms`
- `status`, `error_message`
- `started_at`, `completed_at`

## Available RPC Functions

- `get_debate_with_turns(debate_uuid)` — Get full debate with turns

## Views

- `debate_summary` — Summary with aggregated stats

## Important Notes

1. **Auto-sync**: Debates sync automatically on completion
2. **Background task**: Sync does not block the user response
3. **Limits**: Prompts and responses are capped at 10KB and 20KB respectively
4. **Fallback**: If sync fails, the debate remains available locally

## Troubleshooting

### Error: "Tables not accessible"
- Verify you executed the SQL script in Supabase
- Verify tables have RLS enabled with policies for "anon"

### Error: "Connection failed"
- Check `SUPABASE_URL` and `SUPABASE_ANON_KEY` in `.env`
- Verify the Supabase project is active

### Sync not working
- Check Master logs for `supabase_sync` messages
- Verify connection with `/api/v1/debate/cloud/status`
