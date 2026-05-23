# Configuración de Supabase para Synapse Council

## Paso 1: Crear Tablas en Supabase

1. Ve al [SQL Editor de Supabase](https://supabase.com/dashboard/project/jdbzjapshomatwyasmig/sql)
2. Copia y pega el contenido del archivo `supabase_schema.sql`
3. Ejecuta el script

## Paso 2: Verificar Conexión

Después de reiniciar el Master, prueba la conexión:

```bash
curl http://localhost:8000/api/v1/debate/cloud/status
```

Debería retornar:
```json
{
  "enabled": true,
  "url": "https://jdbzjapshomatwyasmig.supabase.co",
  "status": "connected",
  "tables_accessible": true
}
```

## Paso 3: Ejecutar un Debate de Prueba

```bash
curl -X POST http://localhost:8000/api/v1/debate/create \
  -H "Content-Type: application/json" \
  -d '{"topic":"Test de sincronización","mode":"local_only"}'
```

El debate se sincronizará automáticamente con Supabase al completarse.

## Paso 4: Verificar en Supabase

1. Ve a [Table Editor](https://supabase.com/dashboard/project/jdbzjapshomatwyasmig/editor)
2. Revisa las tablas:
   - `sequential_debates` - Debe tener el debate creado
   - `sequential_debate_turns` - Debe tener los 4 turnos

## Endpoints de Supabase

| Endpoint | Descripción |
|----------|-------------|
| `GET /api/v1/debate/cloud/status` | Estado de conexión |
| `GET /api/v1/debate/cloud/list` | Listar debates en la nube |
| `GET /api/v1/debate/cloud/{id}` | Obtener debate específico de la nube |
| `POST /api/v1/debate/cloud/sync/{id}` | Forzar sincronización manual |

## Esquema de Tablas

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

## Funciones RPC Disponibles

- `get_debate_with_turns(debate_uuid)` - Obtiene debate completo con turns

## Vistas

- `debate_summary` - Resumen con estadísticas agregadas

## Notas Importantes

1. **Sincronización automática**: Los debates se sincronizan automáticamente al completarse
2. **Background task**: La sincronización no bloquea la respuesta al usuario
3. **Límites**: Los prompts y respuestas se limitan a 10KB y 20KB respectivamente
4. **Fallback**: Si falla la sincronización, el debate sigue disponible localmente

## Troubleshooting

### Error: "Tables not accessible"
- Verifica que ejecutaste el script SQL en Supabase
- Verifica que las tablas tienen RLS habilitado con políticas para "anon"

### Error: "Connection failed"
- Verifica `SUPABASE_URL` y `SUPABASE_ANON_KEY` en `.env`
- Verifica que el proyecto Supabase esté activo

### Sincronización no funciona
- Revisa los logs del Master para ver mensajes de `supabase_sync`
- Verifica la conexión con `/api/v1/debate/cloud/status`
