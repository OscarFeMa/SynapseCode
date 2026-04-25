-- Synapse Council v2.0 - Consensus Debate Schema for Supabase
-- Tablas para debates de consenso multi-modelo

-- ============================================
-- Tabla principal: Debates de Consenso
-- ============================================
CREATE TABLE IF NOT EXISTS consensus_debates (
    id UUID PRIMARY KEY,
    topic TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('running', 'consensus_reached', 'partial_consensus', 'max_rounds_reached', 'failed')),
    total_agents INTEGER DEFAULT 0,
    max_rounds INTEGER DEFAULT 5,
    consensus_score NUMERIC(3,2) CHECK (consensus_score >= 0 AND consensus_score <= 1),
    final_consensus TEXT,
    bias_analysis JSONB,
    transcript_path TEXT,
    total_tokens_in INTEGER DEFAULT 0,
    total_tokens_out INTEGER DEFAULT 0,
    total_latency_ms INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    synced_at TIMESTAMPTZ DEFAULT NOW()
);

-- Políticas de seguridad RLS para consensus_debates
ALTER TABLE consensus_debates ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow anonymous read access" ON consensus_debates
    FOR SELECT USING (true);

CREATE POLICY "Allow anonymous insert access" ON consensus_debates
    FOR INSERT WITH CHECK (true);

CREATE POLICY "Allow anonymous update access" ON consensus_debates
    FOR UPDATE USING (true);

-- Índices
CREATE INDEX idx_consensus_debates_status ON consensus_debates(status);
CREATE INDEX idx_consensus_debates_created ON consensus_debates(created_at DESC);
CREATE INDEX idx_consensus_debates_score ON consensus_debates(consensus_score);

-- ============================================
-- Tabla: Rondas de Consenso
-- ============================================
CREATE TABLE IF NOT EXISTS consensus_rounds (
    id SERIAL PRIMARY KEY,
    debate_id UUID NOT NULL REFERENCES consensus_debates(id) ON DELETE CASCADE,
    round_number INTEGER NOT NULL,
    round_type TEXT NOT NULL CHECK (round_type IN ('proposal', 'refutation', 'synthesis', 'validation', 'convergence')),
    global_consensus_score NUMERIC(3,2) CHECK (global_consensus_score >= 0 AND global_consensus_score <= 1),
    converged BOOLEAN DEFAULT FALSE,
    dissent_topics TEXT[],
    created_at TIMESTAMPTZ DEFAULT NOW(),
    synced_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(debate_id, round_number)
);

-- Políticas de seguridad
ALTER TABLE consensus_rounds ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow anonymous read access" ON consensus_rounds
    FOR SELECT USING (true);

CREATE POLICY "Allow anonymous insert access" ON consensus_rounds
    FOR INSERT WITH CHECK (true);

CREATE POLICY "Allow anonymous update access" ON consensus_rounds
    FOR UPDATE USING (true);

-- Índices
CREATE INDEX idx_consensus_rounds_debate ON consensus_rounds(debate_id, round_number);
CREATE INDEX idx_consensus_rounds_type ON consensus_rounds(round_type);

-- ============================================
-- Tabla: Posiciones de Agentes
-- ============================================
CREATE TABLE IF NOT EXISTS consensus_agent_positions (
    id SERIAL PRIMARY KEY,
    debate_id UUID NOT NULL REFERENCES consensus_debates(id) ON DELETE CASCADE,
    round_number INTEGER NOT NULL,
    agent_id TEXT NOT NULL,
    agent_name TEXT NOT NULL,
    agent_role TEXT NOT NULL CHECK (agent_role IN ('analyst', 'critic', 'synthesizer', 'refiner', 'validator')),
    position_text TEXT NOT NULL,
    confidence NUMERIC(3,2) DEFAULT 0 CHECK (confidence >= 0 AND confidence <= 1),
    consensus_score NUMERIC(3,2) DEFAULT 0 CHECK (consensus_score >= 0 AND consensus_score <= 1),
    supporting_points TEXT[],
    objections_raised TEXT[],
    logical_fallacies TEXT[],
    created_at TIMESTAMPTZ DEFAULT NOW(),
    synced_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(debate_id, round_number, agent_id)
);

-- Políticas de seguridad
ALTER TABLE consensus_agent_positions ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow anonymous read access" ON consensus_agent_positions
    FOR SELECT USING (true);

CREATE POLICY "Allow anonymous insert access" ON consensus_agent_positions
    FOR INSERT WITH CHECK (true);

CREATE POLICY "Allow anonymous update access" ON consensus_agent_positions
    FOR UPDATE USING (true);

-- Índices
CREATE INDEX idx_consensus_positions_debate ON consensus_agent_positions(debate_id);
CREATE INDEX idx_consensus_positions_agent ON consensus_agent_positions(agent_id);
CREATE INDEX idx_consensus_positions_round ON consensus_agent_positions(debate_id, round_number);

-- ============================================
-- Vistas útiles
-- ============================================

-- Vista: Resumen de debates de consenso
CREATE OR REPLACE VIEW consensus_debates_summary AS
SELECT 
    d.id,
    d.topic,
    d.status,
    d.consensus_score,
    d.total_agents,
    d.max_rounds,
    d.created_at,
    d.completed_at,
    COUNT(DISTINCT r.round_number) as completed_rounds,
    COUNT(DISTINCT p.agent_id) as total_positions
FROM consensus_debates d
LEFT JOIN consensus_rounds r ON d.id = r.debate_id
LEFT JOIN consensus_agent_positions p ON d.id = p.debate_id
GROUP BY d.id, d.topic, d.status, d.consensus_score, d.total_agents, d.max_rounds, d.created_at, d.completed_at;

-- Vista: Score de consenso por ronda
CREATE OR REPLACE VIEW consensus_rounds_progress AS
SELECT 
    debate_id,
    round_number,
    round_type,
    global_consensus_score,
    converged,
    array_length(dissent_topics, 1) as dissent_count
FROM consensus_rounds
ORDER BY debate_id, round_number;

-- ============================================
-- Funciones RPC
-- ============================================

-- Función: Obtener debates con alto consenso
CREATE OR REPLACE FUNCTION get_high_consensus_debates(min_score NUMERIC)
RETURNS SETOF consensus_debates AS $$
BEGIN
    RETURN QUERY
    SELECT * FROM consensus_debates
    WHERE consensus_score >= min_score
    ORDER BY consensus_score DESC;
END;
$$ LANGUAGE plpgsql;

-- Función: Estadísticas de debates
CREATE OR REPLACE FUNCTION get_consensus_statistics()
RETURNS TABLE (
    total_debates BIGINT,
    avg_consensus_score NUMERIC,
    debates_with_consensus BIGINT,
    debates_partial_consensus BIGINT,
    total_rounds BIGINT,
    total_positions BIGINT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        COUNT(DISTINCT d.id) as total_debates,
        AVG(d.consensus_score)::NUMERIC(3,2) as avg_consensus_score,
        COUNT(DISTINCT CASE WHEN d.status = 'consensus_reached' THEN d.id END) as debates_with_consensus,
        COUNT(DISTINCT CASE WHEN d.status = 'partial_consensus' THEN d.id END) as debates_partial_consensus,
        COUNT(DISTINCT r.id) as total_rounds,
        COUNT(DISTINCT p.id) as total_positions
    FROM consensus_debates d
    LEFT JOIN consensus_rounds r ON d.id = r.debate_id
    LEFT JOIN consensus_agent_positions p ON d.id = p.debate_id;
END;
$$ LANGUAGE plpgsql;

-- ============================================
-- Comentarios
-- ============================================
COMMENT ON TABLE consensus_debates IS 'Debates de consenso multi-modelo con validación cruzada';
COMMENT ON TABLE consensus_rounds IS 'Rondas individuales de cada debate de consenso';
COMMENT ON TABLE consensus_agent_positions IS 'Posiciones de cada agente por ronda';
