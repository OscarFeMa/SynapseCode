-- Synapse Council v2.0 - Supabase Schema for Sequential Debates
-- Ejecutar esto en el SQL Editor de Supabase

-- Tabla: sequential_debates
-- Registro maestro de debates secuenciales multi-modelo
CREATE TABLE IF NOT EXISTS sequential_debates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    topic TEXT NOT NULL,
    mode TEXT DEFAULT 'standard', -- standard, local_only, hybrid
    status TEXT DEFAULT 'created', -- created, running, completed, failed
    total_turns INTEGER DEFAULT 0,
    total_tokens_in INTEGER DEFAULT 0,
    total_tokens_out INTEGER DEFAULT 0,
    total_latency_ms INTEGER DEFAULT 0,
    final_verdict TEXT,
    transcript_path TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    synced_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Habilitar Row Level Security (RLS)
ALTER TABLE sequential_debates ENABLE ROW LEVEL SECURITY;

-- Política: Permitir lectura/escritura anónima (para anon key)
-- Nota: En producción, cambiar a autenticación requerida
CREATE POLICY "Allow anonymous access" ON sequential_debates
    FOR ALL
    TO anon
    USING (true)
    WITH CHECK (true);

-- Índices
CREATE INDEX IF NOT EXISTS idx_debates_status ON sequential_debates(status);
CREATE INDEX IF NOT EXISTS idx_debates_created ON sequential_debates(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_debates_mode ON sequential_debates(mode);

-- Comentarios
COMMENT ON TABLE sequential_debates IS 'Registro maestro de debates secuenciales multi-modelo';
COMMENT ON COLUMN sequential_debates.topic IS 'Tema del debate';
COMMENT ON COLUMN sequential_debates.mode IS 'Modo: standard (3 local + 1 cloud), local_only (4 local), hybrid';
COMMENT ON COLUMN sequential_debates.status IS 'Estado: created, running, completed, failed';
COMMENT ON COLUMN sequential_debates.total_tokens_out IS 'Total de tokens generados por todos los agentes';
COMMENT ON COLUMN sequential_debates.transcript_path IS 'Ruta local al archivo de transcripción Markdown';


-- Tabla: sequential_debate_turns
-- Registro de cada turno/agente en el debate
CREATE TABLE IF NOT EXISTS sequential_debate_turns (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    debate_id UUID NOT NULL REFERENCES sequential_debates(id) ON DELETE CASCADE,
    turn_number INTEGER NOT NULL,
    agent_id TEXT NOT NULL,
    agent_name TEXT NOT NULL,
    agent_role TEXT NOT NULL, -- analyst, critic, synthesizer, refiner
    model TEXT NOT NULL, -- llama3:8b, mistral:7b, etc.
    provider TEXT NOT NULL, -- meta, mistral, alibaba, deepseek, anthropic
    node TEXT NOT NULL, -- LOCAL, CLOUD
    engine TEXT NOT NULL, -- ollama, openrouter
    
    -- Prompt y respuesta
    prompt_sent TEXT NOT NULL,
    response_received TEXT NOT NULL DEFAULT '',
    
    -- Métricas
    tokens_in INTEGER DEFAULT 0,
    tokens_out INTEGER DEFAULT 0,
    latency_ms INTEGER DEFAULT 0,
    
    -- Estado
    status TEXT DEFAULT 'pending', -- pending, running, completed, failed, completed (fallback)
    error_message TEXT,
    
    -- Timestamps
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    synced_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Constraint único para evitar duplicados
    UNIQUE(debate_id, turn_number)
);

-- Habilitar RLS
ALTER TABLE sequential_debate_turns ENABLE ROW LEVEL SECURITY;

-- Política anónima
CREATE POLICY "Allow anonymous access" ON sequential_debate_turns
    FOR ALL
    TO anon
    USING (true)
    WITH CHECK (true);

-- Índices
CREATE INDEX IF NOT EXISTS idx_turns_debate_id ON sequential_debate_turns(debate_id);
CREATE INDEX IF NOT EXISTS idx_turns_number ON sequential_debate_turns(debate_id, turn_number);
CREATE INDEX IF NOT EXISTS idx_turns_status ON sequential_debate_turns(status);
CREATE INDEX IF NOT EXISTS idx_turns_model ON sequential_debate_turns(model);

-- Comentarios
COMMENT ON TABLE sequential_debate_turns IS 'Registro de cada turno/agente en debates secuenciales';
COMMENT ON COLUMN sequential_debate_turns.prompt_sent IS 'Prompt completo enviado al agente (con contexto acumulado)';
COMMENT ON COLUMN sequential_debate_turns.response_received IS 'Respuesta completa del agente';
COMMENT ON COLUMN sequential_debate_turns.latency_ms IS 'Tiempo de respuesta en milisegundos';


-- Vista: debate_summary
-- Resumen de debates con estadísticas agregadas
CREATE OR REPLACE VIEW debate_summary AS
SELECT 
    d.id,
    d.topic,
    d.mode,
    d.status,
    d.total_turns,
    d.total_tokens_in,
    d.total_tokens_out,
    d.total_latency_ms,
    d.created_at,
    d.completed_at,
    -- Agente más rápido
    (SELECT t.agent_name 
     FROM sequential_debate_turns t 
     WHERE t.debate_id = d.id 
     ORDER BY t.latency_ms ASC 
     LIMIT 1) as fastest_agent,
    -- Agente más lento
    (SELECT t.agent_name 
     FROM sequential_debate_turns t 
     WHERE t.debate_id = d.id 
     ORDER BY t.latency_ms DESC 
     LIMIT 1) as slowest_agent,
    -- Total de agentes locales
    (SELECT COUNT(*) 
     FROM sequential_debate_turns t 
     WHERE t.debate_id = d.id AND t.node = 'LOCAL') as local_agents,
    -- Total de agentes cloud
    (SELECT COUNT(*) 
     FROM sequential_debate_turns t 
     WHERE t.debate_id = d.id AND t.node = 'CLOUD') as cloud_agents
FROM sequential_debates d;

-- Función: get_debate_with_turns
-- Función RPC para obtener debate completo con turns en una sola llamada
CREATE OR REPLACE FUNCTION get_debate_with_turns(debate_uuid UUID)
RETURNS JSON AS $$
DECLARE
    result JSON;
BEGIN
    SELECT json_build_object(
        'debate', row_to_json(d.*),
        'turns', (
            SELECT json_agg(row_to_json(t.*) ORDER BY t.turn_number)
            FROM sequential_debate_turns t
            WHERE t.debate_id = debate_uuid
        )
    ) INTO result
    FROM sequential_debates d
    WHERE d.id = debate_uuid;
    
    RETURN result;
END;
$$ LANGUAGE plpgsql;


-- Configuración de replicación en tiempo real (opcional)
-- Para suscribirse a cambios en tiempo real desde el frontend
COMMENT ON TABLE sequential_debates IS E'@realtime';
COMMENT ON TABLE sequential_debate_turns IS E'@realtime';


-- Datos de ejemplo (opcional, para pruebas)
-- Descomentar para insertar datos de prueba
/*
INSERT INTO sequential_debates (id, topic, mode, status, total_turns, total_tokens_out, final_verdict)
VALUES (
    '00000000-0000-0000-0000-000000000001',
    'Ejemplo: El futuro de la IA',
    'local_only',
    'completed',
    4,
    1500,
    'Veredicto de ejemplo del debate sobre IA'
);

INSERT INTO sequential_debate_turns (debate_id, turn_number, agent_id, agent_name, agent_role, model, provider, node, engine, prompt_sent, response_received, tokens_out, latency_ms, status)
VALUES 
    ('00000000-0000-0000-0000-000000000001', 1, 'agent1', 'Analista Meta', 'analyst', 'llama3:8b', 'meta', 'LOCAL', 'ollama', 'Prompt ejemplo...', 'Respuesta ejemplo...', 300, 5000, 'completed'),
    ('00000000-0000-0000-0000-000000000001', 2, 'agent2', 'Crítico Mistral', 'critic', 'mistral:7b', 'mistral', 'LOCAL', 'ollama', 'Prompt ejemplo...', 'Respuesta ejemplo...', 400, 8000, 'completed');
*/

-- Mensaje de confirmación
SELECT 'Tablas creadas exitosamente en Supabase' as result;
