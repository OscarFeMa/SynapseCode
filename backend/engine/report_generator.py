"""
Synapse Council v2.0 - Professional Debate Report Generator
Genera informes HTML profesionales y vendibles para debates completados.
"""

import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

import structlog

logger = structlog.get_logger()

REPORTS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data", "reports")
os.makedirs(REPORTS_DIR, exist_ok=True)


def _escape_html(text: str) -> str:
    """Escapa caracteres especiales HTML"""
    if not text:
        return ""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#x27;")
    )


def _format_latency(ms: int) -> str:
    """Formatea latencia en formato legible"""
    if ms < 1000:
        return f"{ms}ms"
    return f"{ms / 1000:.1f}s"


def _format_tokens(tokens: int) -> str:
    """Formatea tokens en formato legible"""
    if tokens >= 1000:
        return f"{tokens / 1000:.1f}k"
    return str(tokens)


def _get_role_color(role: str) -> str:
    """Retorna color por rol"""
    colors = {
        "analyst": "#3B82F6",
        "critic": "#EF4444",
        "synthesizer": "#10B981",
        "refiner": "#8B5CF6",
        "moderator": "#F59E0B",
    }
    return colors.get(role, "#6B7280")


def _get_role_icon(role: str) -> str:
    """Retorna icono por rol"""
    icons = {
        "analyst": "🔍",
        "critic": "⚡",
        "synthesizer": "🔗",
        "refiner": "✨",
        "moderator": "🎯",
    }
    return icons.get(role, "🤖")


def _get_quality_badge(score: float) -> tuple[str, str]:
    """Retorna badge de calidad"""
    if score >= 0.8:
        return "Excelente", "#10B981"
    elif score >= 0.6:
        return "Buena", "#3B82F6"
    elif score >= 0.4:
        return "Aceptable", "#F59E0B"
    else:
        return "Baja", "#EF4444"


def generate_professional_report(
    debate_data: Dict[str, Any],
    turns: List[Dict[str, Any]],
    verdict: str = "",
    structured_report: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Genera un informe HTML profesional y vendible para un debate.

    Args:
        debate_data: Datos del debate (topic, status, tokens, etc.)
        turns: Lista de turnos con prompts y respuestas
        verdict: Veredicto final del tribunal
        structured_report: Reporte estructurado JSON opcional

    Returns:
        HTML string completo
    """
    topic = debate_data.get("topic", "Sin tema")
    status = debate_data.get("status", "completed")
    total_tokens_in = debate_data.get("total_tokens_in", 0)
    total_tokens_out = debate_data.get("total_tokens_out", 0)
    total_latency = debate_data.get("total_latency_ms", 0)
    created_at = debate_data.get("created_at", "")
    completed_at = debate_data.get("completed_at", "")
    web_context = debate_data.get("web_context")

    # Parsear fechas
    try:
        dt_created = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        dt_completed = datetime.fromisoformat(completed_at.replace("Z", "+00:00"))
        duration = (dt_completed - dt_created).total_seconds()
    except Exception:
        duration = total_latency / 1000 if total_latency else 0

    # Preparar datos de turnos para charts
    turn_labels = []
    turn_tokens = []
    turn_latencies = []
    turn_scores = []
    for t in turns:
        role = t.get("agent_role", "unknown")
        name = t.get("agent_name", "Unknown")
        turn_labels.append(f"{_get_role_icon(role)} {name}")
        turn_tokens.append(t.get("tokens_out", 0))
        turn_latencies.append(t.get("latency_ms", 0))
        turn_scores.append(t.get("quality_score", 0) * 100 if t.get("quality_score") else 50)

    # Web context summary
    web_summary = ""
    if web_context:
        try:
            ctx = json.loads(web_context) if isinstance(web_context, str) else web_context
            searches = ctx.get("searches", [])
            successful = [s for s in searches if s.get("success")]
            if successful:
                web_summary = f"✅ {len(successful)} fuente(s) consultada(s) exitosamente"
                for s in successful:
                    preview = s.get("response", "")[:200]
                    if preview:
                        web_summary += (
                            f"<br><strong>{_escape_html(s.get('site_label', ''))}:</strong> {_escape_html(preview)}..."
                        )
        except Exception:
            web_summary = "Contexto web disponible"

    # Structured report data
    consensus_level = 50
    key_findings = []
    risks = []
    if structured_report:
        try:
            sr = json.loads(structured_report) if isinstance(structured_report, str) else structured_report
            consensus_level = sr.get("consensus_level", 50)
            key_findings = sr.get("key_findings", [])
            risks = sr.get("risks_identified", [])
        except Exception:
            pass

    # Generar HTML
    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Synapse Council - Debate Report</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
    <style>
        :root {{
            --primary: #1e3a5f;
            --primary-light: #2d5a8e;
            --accent: #3B82F6;
            --success: #10B981;
            --warning: #F59E0B;
            --danger: #EF4444;
            --bg: #0f172a;
            --bg-card: #1e293b;
            --bg-card-hover: #334155;
            --text: #f1f5f9;
            --text-muted: #94a3b8;
            --border: #334155;
        }}

        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
            background: var(--bg);
            color: var(--text);
            line-height: 1.6;
            padding: 0;
        }}

        .container {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 2rem;
        }}

        /* Header */
        .header {{
            background: linear-gradient(135deg, var(--primary) 0%, var(--primary-light) 100%);
            padding: 3rem 2rem;
            border-radius: 1rem;
            margin-bottom: 2rem;
            box-shadow: 0 20px 40px rgba(0,0,0,0.3);
            position: relative;
            overflow: hidden;
        }}

        .header::before {{
            content: '';
            position: absolute;
            top: -50%;
            right: -20%;
            width: 400px;
            height: 400px;
            background: radial-gradient(circle, rgba(59,130,246,0.2) 0%, transparent 70%);
            border-radius: 50%;
        }}

        .header h1 {{
            font-size: 2.5rem;
            font-weight: 700;
            margin-bottom: 0.5rem;
            position: relative;
        }}

        .header .subtitle {{
            font-size: 1.1rem;
            color: var(--text-muted);
            position: relative;
        }}

        .header .badge {{
            display: inline-block;
            padding: 0.25rem 0.75rem;
            background: rgba(16, 185, 129, 0.2);
            color: var(--success);
            border-radius: 9999px;
            font-size: 0.875rem;
            font-weight: 600;
            margin-top: 1rem;
            position: relative;
        }}

        /* Stats Grid */
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1rem;
            margin-bottom: 2rem;
        }}

        .stat-card {{
            background: var(--bg-card);
            padding: 1.5rem;
            border-radius: 0.75rem;
            border: 1px solid var(--border);
            transition: transform 0.2s, box-shadow 0.2s;
        }}

        .stat-card:hover {{
            transform: translateY(-2px);
            box-shadow: 0 10px 20px rgba(0,0,0,0.2);
        }}

        .stat-card .label {{
            font-size: 0.875rem;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-bottom: 0.5rem;
        }}

        .stat-card .value {{
            font-size: 2rem;
            font-weight: 700;
            color: var(--accent);
        }}

        .stat-card .unit {{
            font-size: 0.875rem;
            color: var(--text-muted);
            margin-left: 0.25rem;
        }}

        /* Section */
        .section {{
            background: var(--bg-card);
            border-radius: 0.75rem;
            border: 1px solid var(--border);
            padding: 2rem;
            margin-bottom: 2rem;
        }}

        .section-title {{
            font-size: 1.5rem;
            font-weight: 600;
            margin-bottom: 1.5rem;
            padding-bottom: 0.75rem;
            border-bottom: 2px solid var(--border);
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }}

        /* Web Context */
        .web-context {{
            background: rgba(59, 130, 246, 0.1);
            border: 1px solid rgba(59, 130, 246, 0.3);
            border-radius: 0.5rem;
            padding: 1.5rem;
            margin-bottom: 1rem;
        }}

        .web-context h4 {{
            color: var(--accent);
            margin-bottom: 0.5rem;
        }}

        /* Turn Cards */
        .turn-card {{
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 0.75rem;
            margin-bottom: 1.5rem;
            overflow: hidden;
            transition: box-shadow 0.2s;
        }}

        .turn-card:hover {{
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
        }}

        .turn-header {{
            padding: 1.25rem 1.5rem;
            background: linear-gradient(90deg, var(--bg-card-hover) 0%, var(--bg-card) 100%);
            border-bottom: 1px solid var(--border);
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 0.5rem;
        }}

        .turn-header .agent-info {{
            display: flex;
            align-items: center;
            gap: 0.75rem;
        }}

        .turn-header .agent-icon {{
            font-size: 1.5rem;
        }}

        .turn-header .agent-name {{
            font-weight: 600;
            font-size: 1.1rem;
        }}

        .turn-header .agent-role {{
            padding: 0.25rem 0.5rem;
            border-radius: 0.25rem;
            font-size: 0.75rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }}

        .turn-header .metrics {{
            display: flex;
            gap: 1rem;
            font-size: 0.875rem;
            color: var(--text-muted);
        }}

        .turn-header .metric {{
            display: flex;
            align-items: center;
            gap: 0.25rem;
        }}

        .turn-body {{
            padding: 1.5rem;
        }}

        .turn-section {{
            margin-bottom: 1.5rem;
        }}

        .turn-section:last-child {{
            margin-bottom: 0;
        }}

        .turn-section h5 {{
            font-size: 0.875rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: var(--text-muted);
            margin-bottom: 0.75rem;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }}

        .prompt-box {{
            background: rgba(0, 0, 0, 0.3);
            border: 1px solid var(--border);
            border-radius: 0.5rem;
            padding: 1rem;
            font-size: 0.9rem;
            line-height: 1.5;
            max-height: 200px;
            overflow-y: auto;
            white-space: pre-wrap;
            word-wrap: break-word;
        }}

        .response-box {{
            background: rgba(16, 185, 129, 0.05);
            border: 1px solid rgba(16, 185, 129, 0.2);
            border-radius: 0.5rem;
            padding: 1rem;
            font-size: 0.95rem;
            line-height: 1.6;
            white-space: pre-wrap;
            word-wrap: break-word;
        }}

        /* Charts */
        .charts-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
            gap: 1.5rem;
            margin-bottom: 2rem;
        }}

        .chart-container {{
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 0.75rem;
            padding: 1.5rem;
        }}

        .chart-container h4 {{
            margin-bottom: 1rem;
            font-size: 1rem;
            color: var(--text-muted);
        }}

        /* Scoring Table */
        .scoring-table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 1rem;
        }}

        .scoring-table th {{
            background: var(--bg-card-hover);
            padding: 0.75rem 1rem;
            text-align: left;
            font-size: 0.875rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: var(--text-muted);
            border-bottom: 2px solid var(--border);
        }}

        .scoring-table td {{
            padding: 0.75rem 1rem;
            border-bottom: 1px solid var(--border);
        }}

        .scoring-table tr:hover {{
            background: rgba(59, 130, 246, 0.05);
        }}

        .quality-badge {{
            display: inline-block;
            padding: 0.25rem 0.5rem;
            border-radius: 0.25rem;
            font-size: 0.75rem;
            font-weight: 600;
        }}

        /* Verdict */
        .verdict-box {{
            background: linear-gradient(135deg, rgba(59, 130, 246, 0.1) 0%, rgba(139, 92, 246, 0.1) 100%);
            border: 1px solid rgba(59, 130, 246, 0.3);
            border-radius: 0.75rem;
            padding: 2rem;
            font-size: 1.05rem;
            line-height: 1.7;
            white-space: pre-wrap;
            word-wrap: break-word;
        }}

        /* Consensus Bar */
        .consensus-bar {{
            height: 8px;
            background: var(--border);
            border-radius: 9999px;
            overflow: hidden;
            margin-top: 0.5rem;
        }}

        .consensus-fill {{
            height: 100%;
            border-radius: 9999px;
            transition: width 0.5s ease;
        }}

        /* Footer */
        .footer {{
            text-align: center;
            padding: 2rem;
            color: var(--text-muted);
            font-size: 0.875rem;
            border-top: 1px solid var(--border);
            margin-top: 2rem;
        }}

        /* Print styles */
        @media print {{
            body {{ background: white; color: black; }}
            .header {{ background: #1e3a5f !important; -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
            .section, .stat-card, .turn-card, .chart-container {{
                background: white;
                border: 1px solid #ddd;
                -webkit-print-color-adjust: exact;
                print-color-adjust: exact;
            }}
        }}

        /* Responsive */
        @media (max-width: 768px) {{
            .container {{ padding: 1rem; }}
            .header h1 {{ font-size: 1.75rem; }}
            .stats-grid {{ grid-template-columns: repeat(2, 1fr); }}
            .charts-grid {{ grid-template-columns: 1fr; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <!-- Header -->
        <div class="header">
            <h1>🏛️ Synapse Council</h1>
            <div class="subtitle">Informe de Debate Multi-Modelo con IA</div>
            <div class="badge">✅ {status.upper()}</div>
            <p style="margin-top: 1rem; font-size: 1.25rem; position: relative;">
                <strong>Tema:</strong> {_escape_html(topic)}
            </p>
            <p style="margin-top: 0.5rem; color: var(--text-muted); position: relative;">
                📅 {dt_created.strftime("%d/%m/%Y %H:%M")} → {dt_completed.strftime("%H:%M")} UTC
            </p>
        </div>

        <!-- Stats Grid -->
        <div class="stats-grid">
            <div class="stat-card">
                <div class="label">Turnos</div>
                <div class="value">{len(turns)}<span class="unit">agentes</span></div>
            </div>
            <div class="stat-card">
                <div class="label">Tokens Generados</div>
                <div class="value">{_format_tokens(total_tokens_out)}<span class="unit">out</span></div>
            </div>
            <div class="stat-card">
                <div class="label">Tokens Consumidos</div>
                <div class="value">{_format_tokens(total_tokens_in)}<span class="unit">in</span></div>
            </div>
            <div class="stat-card">
                <div class="label">Duración Total</div>
                <div class="value">{_format_latency(int(duration * 1000))}</div>
            </div>
            <div class="stat-card">
                <div class="label">Consenso</div>
                <div class="value">{consensus_level}<span class="unit">%</span></div>
                <div class="consensus-bar">
                    <div class="consensus-fill" style="width: {consensus_level}%; background: {"#10B981" if consensus_level >= 70 else "#F59E0B" if consensus_level >= 50 else "#EF4444"}"></div>
                </div>
            </div>
        </div>

        <!-- Web Context -->
        <div class="section">
            <h2 class="section-title">🌐 Contexto Web en Tiempo Real</h2>
            <div class="web-context">
                <h4>Fuentes Consultadas</h4>
                <p>{web_summary if web_summary else "No se realizó búsqueda web para este debate."}</p>
            </div>
        </div>

        <!-- Charts -->
        <div class="section">
            <h2 class="section-title">📊 Métricas de Rendimiento</h2>
            <div class="charts-grid">
                <div class="chart-container">
                    <h4>Tokens Generados por Agente</h4>
                    <canvas id="tokensChart"></canvas>
                </div>
                <div class="chart-container">
                    <h4>Latencia por Agente (ms)</h4>
                    <canvas id="latencyChart"></canvas>
                </div>
            </div>
        </div>

        <!-- Scoring Table -->
        <div class="section">
            <h2 class="section-title">🏆 Puntuación de Agentes</h2>
            <table class="scoring-table">
                <thead>
                    <tr>
                        <th>Agente</th>
                        <th>Rol</th>
                        <th>Modelo</th>
                        <th>Tokens Out</th>
                        <th>Latencia</th>
                        <th>Calidad</th>
                    </tr>
                </thead>
                <tbody>"""

    # Add scoring table rows
    for t in turns:
        role = t.get("agent_role", "unknown")
        name = t.get("agent_name", "Unknown")
        model = t.get("model", "Unknown")
        tokens_out = t.get("tokens_out", 0)
        latency = t.get("latency_ms", 0)

        # Quality score: use stored value or estimate from response length
        raw_quality = t.get("quality_score")
        if raw_quality is not None:
            quality = raw_quality * 100
        else:
            # Estimate quality based on response length (simple heuristic)
            resp_len = len(t.get("response_received", ""))
            if resp_len > 1500:
                quality = 85
            elif resp_len > 1000:
                quality = 75
            elif resp_len > 500:
                quality = 65
            elif resp_len > 200:
                quality = 50
            else:
                quality = 30

        quality_label, quality_color = _get_quality_badge(quality / 100)

        html += f"""
                    <tr>
                        <td>{_get_role_icon(role)} {_escape_html(name)}</td>
                        <td><span style="color: {_get_role_color(role)}; font-weight: 600;">{role.upper()}</span></td>
                        <td>{_escape_html(model)}</td>
                        <td>{_format_tokens(tokens_out)}</td>
                        <td>{_format_latency(latency)}</td>
                        <td><span class="quality-badge" style="background: {quality_color}20; color: {quality_color};">{quality_label} ({quality:.0f}%)</span></td>
                    </tr>"""

    html += """
                </tbody>
            </table>
        </div>

        <!-- Debate Turns -->
        <div class="section">
            <h2 class="section-title">💬 Desarrollo del Debate</h2>"""

    # Add turn cards
    for t in turns:
        role = t.get("agent_role", "unknown")
        name = t.get("agent_name", "Unknown")
        model = t.get("model", "Unknown")
        tokens_out = t.get("tokens_out", 0)
        latency = t.get("latency_ms", 0)
        prompt = t.get("prompt_sent", "")
        response = t.get("response_received", "")

        # Clean up prompt: remove web context repetition for readability
        # Keep only the essential parts
        prompt_display = prompt
        if "## Información Actualizada (Búsqueda Web)" in prompt:
            # Show a truncated version of the web context
            parts = prompt.split("## Historial del Debate")
            if len(parts) > 1:
                header_part = parts[0]
                # Truncate web context to first 300 chars
                web_marker = "## Información Actualizada (Búsqueda Web)"
                if web_marker in header_part:
                    web_start = header_part.index(web_marker)
                    web_section = header_part[web_start : web_start + 300]
                    header_part = (
                        header_part[:web_start] + web_section + "\\n... [contexto web truncado para legibilidad]"
                    )
                prompt_display = header_part + "\\n\\n## Historial del Debate" + parts[1]

        html += f"""
            <div class="turn-card">
                <div class="turn-header">
                    <div class="agent-info">
                        <span class="agent-icon">{_get_role_icon(role)}</span>
                        <span class="agent-name">{_escape_html(name)}</span>
                        <span class="agent-role" style="background: {_get_role_color(role)}20; color: {_get_role_color(role)};">{role}</span>
                    </div>
                    <div class="metrics">
                        <span class="metric">📝 {_format_tokens(tokens_out)} tokens</span>
                        <span class="metric">⏱️ {_format_latency(latency)}</span>
                        <span class="metric">🤖 {_escape_html(model)}</span>
                    </div>
                </div>
                <div class="turn-body">
                    <div class="turn-section">
                        <h5>📤 Prompt Enviado ({len(prompt)} chars)</h5>
                        <div class="prompt-box">{_escape_html(prompt_display)}</div>
                    </div>
                    <div class="turn-section">
                        <h5>📥 Respuesta ({len(response)} chars)</h5>
                        <div class="response-box">{_escape_html(response)}</div>
                    </div>
                </div>
            </div>"""

    html += """
        </div>

        <!-- Verdict -->
        <div class="section">
            <h2 class="section-title">⚖️ Veredicto Final del Tribunal</h2>
            <div class="verdict-box">
                {_escape_html(verdict) if verdict else '<em>Veredicto no disponible para este debate.</em>'}
            </div>
        </div>"""

    # Key findings if available
    if key_findings:
        html += """
        <div class="section">
            <h2 class="section-title">🔑 Hallazgos Clave</h2>
            <ul style="list-style: none; padding: 0;">"""
        for finding in key_findings:
            html += f"""
                <li style="padding: 0.75rem 1rem; background: rgba(59, 130, 246, 0.1); border-left: 3px solid var(--accent); margin-bottom: 0.5rem; border-radius: 0 0.25rem 0.25rem 0;">
                    ✅ {_escape_html(finding)}
                </li>"""
        html += """
            </ul>
        </div>"""

    if risks:
        html += """
        <div class="section">
            <h2 class="section-title">⚠️ Riesgos Identificados</h2>
            <ul style="list-style: none; padding: 0;">"""
        for risk in risks:
            html += f"""
                <li style="padding: 0.75rem 1rem; background: rgba(239, 68, 68, 0.1); border-left: 3px solid var(--danger); margin-bottom: 0.5rem; border-radius: 0 0.25rem 0.25rem 0;">
                    🚨 {_escape_html(risk)}
                </li>"""
        html += """
            </ul>
        </div>"""

    # Footer
    html += f"""
        <div class="footer">
            <p><strong>Synapse Council v2.0</strong> - Sistema de Debate Multi-Modelo con IA</p>
            <p>Informe generado el {datetime.now().strftime("%d/%m/%Y %H:%M:%S")} | Debate ID: {debate_data.get("id", "N/A")}</p>
            <p style="margin-top: 0.5rem; font-size: 0.75rem;">
                Powered by Ollama, DuckDuckGo Search, y Trafilatura
            </p>
        </div>
    </div>

    <script>
        // Tokens Chart
        const tokensCtx = document.getElementById('tokensChart').getContext('2d');
        new Chart(tokensCtx, {{
            type: 'bar',
            data: {{
                labels: {json.dumps(turn_labels)},
                datasets: [{{
                    label: 'Tokens Generados',
                    data: {json.dumps(turn_tokens)},
                    backgroundColor: [
                        'rgba(59, 130, 246, 0.7)',
                        'rgba(239, 68, 68, 0.7)',
                        'rgba(16, 185, 129, 0.7)',
                        'rgba(139, 92, 246, 0.7)',
                        'rgba(245, 158, 11, 0.7)',
                    ],
                    borderColor: [
                        '#3B82F6', '#EF4444', '#10B981', '#8B5CF6', '#F59E0B'
                    ],
                    borderWidth: 2,
                    borderRadius: 8,
                }}]
            }},
            options: {{
                responsive: true,
                plugins: {{
                    legend: {{ display: false }},
                    tooltip: {{
                        backgroundColor: '#1e293b',
                        titleColor: '#f1f5f9',
                        bodyColor: '#94a3b8',
                        borderColor: '#334155',
                        borderWidth: 1,
                        cornerRadius: 8,
                    }}
                }},
                scales: {{
                    y: {{
                        beginAtZero: true,
                        grid: {{ color: 'rgba(148, 163, 184, 0.1)' }},
                        ticks: {{ color: '#94a3b8' }}
                    }},
                    x: {{
                        grid: {{ display: false }},
                        ticks: {{ color: '#94a3b8' }}
                    }}
                }}
            }}
        }});

        // Latency Chart
        const latencyCtx = document.getElementById('latencyChart').getContext('2d');
        new Chart(latencyCtx, {{
            type: 'line',
            data: {{
                labels: {json.dumps(turn_labels)},
                datasets: [{{
                    label: 'Latencia (ms)',
                    data: {json.dumps(turn_latencies)},
                    borderColor: '#8B5CF6',
                    backgroundColor: 'rgba(139, 92, 246, 0.1)',
                    fill: true,
                    tension: 0.4,
                    pointBackgroundColor: '#8B5CF6',
                    pointBorderColor: '#fff',
                    pointBorderWidth: 2,
                    pointRadius: 6,
                }}]
            }},
            options: {{
                responsive: true,
                plugins: {{
                    legend: {{ display: false }},
                    tooltip: {{
                        backgroundColor: '#1e293b',
                        titleColor: '#f1f5f9',
                        bodyColor: '#94a3b8',
                        borderColor: '#334155',
                        borderWidth: 1,
                        cornerRadius: 8,
                        callbacks: {{
                            label: function(context) {{
                                return context.parsed.y + 'ms (' + (context.parsed.y / 1000).toFixed(1) + 's)';
                            }}
                        }}
                    }}
                }},
                scales: {{
                    y: {{
                        beginAtZero: true,
                        grid: {{ color: 'rgba(148, 163, 184, 0.1)' }},
                        ticks: {{ color: '#94a3b8' }}
                    }},
                    x: {{
                        grid: {{ display: false }},
                        ticks: {{ color: '#94a3b8' }}
                    }}
                }}
            }}
        }});
    </script>
</body>
</html>"""

    return html


def save_report(
    debate_id: str,
    debate_data: Dict[str, Any],
    turns: List[Dict[str, Any]],
    verdict: str = "",
    structured_report: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Genera y guarda un informe HTML profesional.

    Returns:
        Path al archivo HTML generado
    """
    html = generate_professional_report(debate_data, turns, verdict, structured_report)

    filename = f"debate_{debate_id[:8]}.html"
    filepath = os.path.join(REPORTS_DIR, filename)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html)

    logger.info("report.generated", debate_id=debate_id, filepath=filepath)
    return filepath


def generate_report_from_db(debate_id: str) -> Optional[str]:
    """
    Genera un informe HTML desde la base de datos.

    Returns:
        Path al archivo HTML o None si falla
    """
    import sqlite3

    db_path = os.path.join(os.path.dirname(__file__), "..", "..", "data", "synapse.db")

    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()

        # Get debate data
        c.execute("SELECT * FROM sequential_debates WHERE id = ?", (debate_id,))
        debate_row = c.fetchone()
        if not debate_row:
            logger.warning("report.debate_not_found", debate_id=debate_id)
            conn.close()
            return None

        debate_data = dict(debate_row)

        # Get turns
        c.execute(
            "SELECT * FROM sequential_debate_turns WHERE debate_id = ? ORDER BY turn_number",
            (debate_id,),
        )
        turns = [dict(row) for row in c.fetchall()]

        conn.close()

        # Generate report
        filepath = save_report(
            debate_id=debate_id,
            debate_data=debate_data,
            turns=turns,
            verdict=debate_data.get("final_verdict", ""),
            structured_report=debate_data.get("structured_report"),
        )

        return filepath

    except Exception as e:
        logger.error("report.generation_failed", debate_id=debate_id, error=str(e))
        return None


def _generate_bar_chart_svg(labels: List[str], data: List[int], colors: List[str], title: str) -> str:
    """Genera un gráfico de barras como SVG inline para PDF"""
    if not data:
        return ""

    max_val = max(data) if data else 1
    bar_width = 60
    gap = 20
    chart_width = len(data) * (bar_width + gap) + 40
    chart_height = 200
    padding_top = 30
    padding_bottom = 60

    bars = ""
    for i, (label, val, color) in enumerate(zip(labels, data, colors)):
        x = 20 + i * (bar_width + gap)
        bar_height = (val / max_val) * (chart_height - padding_top - padding_bottom) if max_val > 0 else 0
        y = chart_height - padding_bottom - bar_height
        bars += f'<rect x="{x}" y="{y}" width="{bar_width}" height="{bar_height}" fill="{color}" rx="4"/>'
        bars += f'<text x="{x + bar_width / 2}" y="{y - 5}" text-anchor="middle" fill="#f1f5f9" font-size="11" font-weight="600">{val}</text>'
        bars += f'<text x="{x + bar_width / 2}" y="{chart_height - 10}" text-anchor="middle" fill="#94a3b8" font-size="9">{label[:15]}</text>'

    return f"""<svg width="{chart_width}" height="{chart_height}" xmlns="http://www.w3.org/2000/svg">
        <text x="{chart_width / 2}" y="18" text-anchor="middle" fill="#f1f5f9" font-size="13" font-weight="600">{title}</text>
        {bars}
    </svg>"""


def _generate_line_chart_svg(labels: List[str], data: List[int], color: str, title: str) -> str:
    """Genera un gráfico de línea como SVG inline para PDF"""
    if not data:
        return ""

    max_val = max(data) if data else 1
    chart_width = len(data) * 80 + 40
    chart_height = 200
    padding_top = 30
    padding_bottom = 60
    padding_left = 20

    points = []
    for i, val in enumerate(data):
        x = padding_left + i * 80 + 30
        y = (
            chart_height - padding_bottom - (val / max_val) * (chart_height - padding_top - padding_bottom)
            if max_val > 0
            else chart_height - padding_bottom
        )
        points.append((x, y))

    line_path = " ".join(f"{x},{y}" for x, y in points)
    area_path = (
        f"{points[0][0]},{chart_height - padding_bottom} "
        + line_path
        + f" {points[-1][0]},{chart_height - padding_bottom}"
    )

    dots = ""
    labels_svg = ""
    for i, ((x, y), label) in enumerate(zip(points, labels)):
        dots += f'<circle cx="{x}" cy="{y}" r="5" fill="{color}" stroke="#fff" stroke-width="2"/>'
        dots += f'<text x="{x}" y="{y - 12}" text-anchor="middle" fill="#f1f5f9" font-size="11" font-weight="600">{data[i]}ms</text>'
        labels_svg += f'<text x="{x}" y="{chart_height - 10}" text-anchor="middle" fill="#94a3b8" font-size="9">{label[:15]}</text>'

    return f"""<svg width="{chart_width}" height="{chart_height}" xmlns="http://www.w3.org/2000/svg">
        <text x="{chart_width / 2}" y="18" text-anchor="middle" fill="#f1f5f9" font-size="13" font-weight="600">{title}</text>
        <polyline points="{area_path}" fill="rgba(139, 92, 246, 0.15)"/>
        <polyline points="{line_path}" fill="none" stroke="{color}" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>
        {dots}
        {labels_svg}
    </svg>"""


def _generate_bar_chart_svg_light(labels: List[str], data: List[int], colors: List[str], title: str) -> str:
    """Genera un gráfico de barras como SVG inline para PDF (tema claro)"""
    if not data:
        return ""

    max_val = max(data) if data else 1
    bar_width = 50
    gap = 15
    chart_width = len(data) * (bar_width + gap) + 50
    chart_height = 180
    padding_top = 35
    padding_bottom = 50
    padding_left = 30

    bars = ""
    for i, (label, val, color) in enumerate(zip(labels, data, colors)):
        x = padding_left + i * (bar_width + gap)
        bar_height = (val / max_val) * (chart_height - padding_top - padding_bottom) if max_val > 0 else 0
        y = chart_height - padding_bottom - bar_height
        bars += (
            f'<rect x="{x}" y="{y}" width="{bar_width}" height="{bar_height}" fill="{color}" rx="3" opacity="0.85"/>'
        )
        bars += f'<text x="{x + bar_width / 2}" y="{y - 5}" text-anchor="middle" fill="#1e293b" font-size="10" font-weight="600">{val}</text>'
        bars += f'<text x="{x + bar_width / 2}" y="{chart_height - 8}" text-anchor="middle" fill="#64748b" font-size="8">{label[:12]}</text>'

    # Grid lines
    grid_lines = ""
    for i in range(5):
        y = padding_top + i * (chart_height - padding_top - padding_bottom) / 4
        grid_lines += (
            f'<line x1="{padding_left}" y1="{y}" x2="{chart_width - 10}" y2="{y}" stroke="#e2e8f0" stroke-width="0.5"/>'
        )

    return f"""<svg width="{chart_width}" height="{chart_height}" xmlns="http://www.w3.org/2000/svg">
        <text x="{chart_width / 2}" y="16" text-anchor="middle" fill="#1e3a5f" font-size="12" font-weight="700">{title}</text>
        {grid_lines}
        {bars}
    </svg>"""


def _generate_line_chart_svg_light(labels: List[str], data: List[int], color: str, title: str) -> str:
    """Genera un gráfico de línea como SVG inline para PDF (tema claro)"""
    if not data:
        return ""

    max_val = max(data) if data else 1
    chart_width = len(data) * 80 + 50
    chart_height = 180
    padding_top = 35
    padding_bottom = 50
    padding_left = 30

    points = []
    for i, val in enumerate(data):
        x = padding_left + i * 80 + 30
        y = (
            chart_height - padding_bottom - (val / max_val) * (chart_height - padding_top - padding_bottom)
            if max_val > 0
            else chart_height - padding_bottom
        )
        points.append((x, y))

    line_path = " ".join(f"{x},{y}" for x, y in points)
    area_path = (
        f"{points[0][0]},{chart_height - padding_bottom} "
        + line_path
        + f" {points[-1][0]},{chart_height - padding_bottom}"
    )

    # Grid lines
    grid_lines = ""
    for i in range(5):
        y = padding_top + i * (chart_height - padding_top - padding_bottom) / 4
        grid_lines += (
            f'<line x1="{padding_left}" y1="{y}" x2="{chart_width - 10}" y2="{y}" stroke="#e2e8f0" stroke-width="0.5"/>'
        )

    dots = ""
    labels_svg = ""
    for i, ((x, y), label) in enumerate(zip(points, labels)):
        dots += f'<circle cx="{x}" cy="{y}" r="4" fill="{color}" stroke="#fff" stroke-width="2"/>'
        dots += f'<text x="{x}" y="{y - 10}" text-anchor="middle" fill="#1e293b" font-size="9" font-weight="600">{data[i]}ms</text>'
        labels_svg += f'<text x="{x}" y="{chart_height - 8}" text-anchor="middle" fill="#64748b" font-size="8">{label[:12]}</text>'

    return f"""<svg width="{chart_width}" height="{chart_height}" xmlns="http://www.w3.org/2000/svg">
        <text x="{chart_width / 2}" y="16" text-anchor="middle" fill="#1e3a5f" font-size="12" font-weight="700">{title}</text>
        {grid_lines}
        <polyline points="{area_path}" fill="rgba(99, 102, 241, 0.1)"/>
        <polyline points="{line_path}" fill="none" stroke="{color}" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
        {dots}
        {labels_svg}
    </svg>"""


def generate_pdf_report(
    debate_data: Dict[str, Any],
    turns: List[Dict[str, Any]],
    verdict: str = "",
    structured_report: Optional[Dict[str, Any]] = None,
) -> bytes:
    """
    Genera un PDF profesional optimizado para impresión.
    Diseño limpio, tema claro, estilo reporte empresarial.
    """
    import io

    from xhtml2pdf import pisa

    topic = debate_data.get("topic", "Sin tema")
    status = debate_data.get("status", "completed")
    total_tokens_in = debate_data.get("total_tokens_in", 0)
    total_tokens_out = debate_data.get("total_tokens_out", 0)
    total_latency = debate_data.get("total_latency_ms", 0)
    created_at = debate_data.get("created_at", "")
    completed_at = debate_data.get("completed_at", "")

    try:
        dt_created = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        dt_completed = datetime.fromisoformat(completed_at.replace("Z", "+00:00"))
        duration = (dt_completed - dt_created).total_seconds()
    except Exception:
        duration = total_latency / 1000 if total_latency else 0

    # Prepare chart data
    turn_labels = []
    turn_tokens = []
    turn_latencies = []
    turn_colors = []
    for t in turns:
        role = t.get("agent_role", "unknown")
        name = t.get("agent_name", "Unknown")
        turn_labels.append(name)
        turn_tokens.append(t.get("tokens_out", 0))
        turn_latencies.append(t.get("latency_ms", 0))
        turn_colors.append(_get_role_color(role))

    # Consensus
    consensus_level = 50
    key_findings = []
    risks = []
    if structured_report:
        try:
            sr = json.loads(structured_report) if isinstance(structured_report, str) else structured_report
            consensus_level = sr.get("consensus_level", 50)
            key_findings = sr.get("key_findings", [])
            risks = sr.get("risks_identified", [])
        except Exception:
            pass

    # Generate SVG charts (light theme)
    tokens_chart = _generate_bar_chart_svg_light(turn_labels, turn_tokens, turn_colors, "Tokens Generados por Agente")
    latency_chart = _generate_line_chart_svg_light(turn_labels, turn_latencies, "#6366f1", "Latencia por Agente (ms)")

    # Build turns HTML
    turns_html = ""
    for t in turns:
        role = t.get("agent_role", "unknown")
        name = t.get("agent_name", "Unknown")
        model = t.get("model", "Unknown")
        tokens_out_val = t.get("tokens_out", 0)
        latency = t.get("latency_ms", 0)
        prompt = t.get("prompt_sent", "")
        response = t.get("response_received", "")

        # Simplify prompt
        prompt_display = prompt
        if "## Información Actualizada (Búsqueda Web)" in prompt:
            parts = prompt.split("## Historial del Debate")
            if len(parts) > 1:
                header_part = parts[0]
                web_marker = "## Información Actualizada (Búsqueda Web)"
                if web_marker in header_part:
                    web_start = header_part.index(web_marker)
                    web_section = header_part[web_start : web_start + 150]
                    header_part = header_part[:web_start] + web_section + "\n\n[... contexto web resumido ...]\n"
                prompt_display = header_part + "\n## Historial del Debate" + parts[1]

        quality = t.get("quality_score", 0) * 100 if t.get("quality_score") else 50
        quality_label, quality_color = _get_quality_badge(quality / 100)
        role_color = _get_role_color(role)

        turns_html += f"""
        <div class="turn-card">
            <div class="turn-header" style="border-left: 4px solid {role_color};">
                <span class="turn-number">Turno {t.get("turn_number", "?")}</span>
                <span class="agent-name">{_escape_html(name)}</span>
                <span class="agent-role" style="color: {role_color};">{role.upper()}</span>
                <span class="agent-model">{_escape_html(model)}</span>
                <span class="turn-metrics">{_format_tokens(tokens_out_val)} tokens | {_format_latency(latency)} | {quality_label}</span>
            </div>
            <div class="turn-body">
                <div class="turn-section">
                    <div class="section-label">Prompt Enviado</div>
                    <div class="prompt-box">{_escape_html(prompt_display)}</div>
                </div>
                <div class="turn-section">
                    <div class="section-label">Respuesta</div>
                    <div class="response-box">{_escape_html(response)}</div>
                </div>
            </div>
        </div>"""

    # Findings HTML
    findings_html = ""
    if key_findings:
        findings_html = (
            '<div class="section"><div class="section-title">Hallazgos Clave</div><ul class="findings-list">'
        )
        for finding in key_findings:
            findings_html += f'<li class="finding-item">{_escape_html(finding)}</li>'
        findings_html += "</ul></div>"

    risks_html = ""
    if risks:
        risks_html = (
            '<div class="section"><div class="section-title">Riesgos Identificados</div><ul class="risks-list">'
        )
        for risk in risks:
            risks_html += f'<li class="risk-item">{_escape_html(risk)}</li>'
        risks_html += "</ul></div>"

    # Scoring table rows
    scoring_rows = ""
    for i, t in enumerate(turns):
        role = t.get("agent_role", "unknown")
        name = t.get("agent_name", "Unknown")
        model = t.get("model", "Unknown")
        tokens_out_val = t.get("tokens_out", 0)
        latency = t.get("latency_ms", 0)
        raw_quality = t.get("quality_score")
        if raw_quality is not None:
            quality = raw_quality * 100
        else:
            resp_len = len(t.get("response_received", ""))
            if resp_len > 1500:
                quality = 85
            elif resp_len > 1000:
                quality = 75
            elif resp_len > 500:
                quality = 65
            elif resp_len > 200:
                quality = 50
            else:
                quality = 30
        quality_label, quality_color = _get_quality_badge(quality / 100)
        role_color = _get_role_color(role)
        row_bg = "#f8fafc" if i % 2 == 0 else "#ffffff"

        scoring_rows += f"""
                    <tr style="background: {row_bg};">
                        <td><strong>{_escape_html(name)}</strong></td>
                        <td style="color: {role_color}; font-weight: 600;">{role.upper()}</td>
                        <td>{_escape_html(model)}</td>
                        <td style="text-align: right;">{_format_tokens(tokens_out_val)}</td>
                        <td style="text-align: right;">{_format_latency(latency)}</td>
                        <td style="text-align: center;"><span class="quality-badge" style="background: {quality_color}; color: #fff;">{quality_label} {quality:.0f}%</span></td>
                    </tr>"""

    consensus_color = "#10b981" if consensus_level >= 70 else "#f59e0b" if consensus_level >= 50 else "#ef4444"

    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>Synapse Council - Debate Report</title>
    <style>
        @page {{
            size: A4;
            margin: 1.5cm;
        }}
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Segoe UI', Arial, sans-serif;
            background: #ffffff;
            color: #1e293b;
            line-height: 1.5;
            font-size: 10pt;
        }}

        /* Header */
        .report-header {{
            background: linear-gradient(135deg, #1e3a5f 0%, #2563eb 100%);
            color: #ffffff;
            padding: 2rem;
            margin: -1.5cm -1.5cm 1.5rem -1.5cm;
        }}
        .report-header h1 {{
            font-size: 2rem;
            font-weight: 700;
            margin-bottom: 0.25rem;
            letter-spacing: -0.5px;
        }}
        .report-header .report-subtitle {{
            font-size: 1rem;
            opacity: 0.9;
            margin-bottom: 0.75rem;
        }}
        .report-header .report-meta {{
            font-size: 0.85rem;
            opacity: 0.8;
        }}
        .status-badge {{
            display: inline-block;
            padding: 0.2rem 0.6rem;
            background: #10b981;
            color: #fff;
            border-radius: 0.25rem;
            font-size: 0.75rem;
            font-weight: 600;
            text-transform: uppercase;
        }}

        /* Stats */
        .stats-table {{
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 1.5rem;
        }}
        .stats-table td {{
            padding: 1rem;
            text-align: center;
            border: 1px solid #e2e8f0;
            background: #f8fafc;
        }}
        .stats-table .stat-label {{
            font-size: 0.7rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: #64748b;
            margin-bottom: 0.25rem;
        }}
        .stats-table .stat-value {{
            font-size: 1.5rem;
            font-weight: 700;
            color: #1e3a5f;
        }}
        .consensus-bar {{
            height: 6px;
            background: #e2e8f0;
            border-radius: 3px;
            overflow: hidden;
            margin-top: 0.25rem;
        }}
        .consensus-fill {{
            height: 100%;
            background: {consensus_color};
        }}

        /* Sections */
        .section {{
            margin-bottom: 1.5rem;
            page-break-inside: avoid;
        }}
        .section-title {{
            font-size: 1.1rem;
            font-weight: 700;
            color: #1e3a5f;
            padding-bottom: 0.5rem;
            margin-bottom: 1rem;
            border-bottom: 2px solid #2563eb;
        }}

        /* Charts */
        .charts-row {{
            margin-bottom: 1.5rem;
        }}
        .chart-box {{
            display: inline-block;
            width: 48%;
            margin-right: 2%;
            vertical-align: top;
            text-align: center;
            border: 1px solid #e2e8f0;
            border-radius: 0.5rem;
            padding: 1rem;
            background: #f8fafc;
        }}

        /* Scoring Table */
        .scoring-table {{
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 1rem;
        }}
        .scoring-table th {{
            background: #1e3a5f;
            color: #ffffff;
            padding: 0.6rem 0.75rem;
            text-align: left;
            font-size: 0.75rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }}
        .scoring-table td {{
            padding: 0.5rem 0.75rem;
            border-bottom: 1px solid #e2e8f0;
            font-size: 0.9rem;
        }}
        .quality-badge {{
            display: inline-block;
            padding: 0.15rem 0.4rem;
            border-radius: 0.2rem;
            font-size: 0.7rem;
            font-weight: 600;
        }}

        /* Turn Cards */
        .turn-card {{
            border: 1px solid #e2e8f0;
            border-radius: 0.5rem;
            margin-bottom: 1rem;
            page-break-inside: avoid;
            overflow: hidden;
        }}
        .turn-header {{
            background: #f1f5f9;
            padding: 0.75rem 1rem;
            display: block;
        }}
        .turn-number {{
            font-weight: 700;
            color: #1e3a5f;
            margin-right: 0.5rem;
        }}
        .agent-name {{
            font-weight: 600;
            margin-right: 0.5rem;
        }}
        .agent-role {{
            font-size: 0.7rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-right: 0.5rem;
        }}
        .agent-model {{
            font-size: 0.8rem;
            color: #64748b;
            margin-right: 0.5rem;
        }}
        .turn-metrics {{
            font-size: 0.8rem;
            color: #64748b;
        }}
        .turn-body {{
            padding: 1rem;
        }}
        .turn-section {{
            margin-bottom: 1rem;
        }}
        .turn-section:last-child {{
            margin-bottom: 0;
        }}
        .section-label {{
            font-size: 0.7rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: #64748b;
            font-weight: 600;
            margin-bottom: 0.4rem;
        }}
        .prompt-box {{
            background: #f8fafc;
            border: 1px solid #e2e8f0;
            border-radius: 0.35rem;
            padding: 0.75rem;
            font-size: 0.8rem;
            line-height: 1.4;
            max-height: 120px;
            overflow: auto;
            white-space: pre-wrap;
            word-wrap: break-word;
            color: #334155;
        }}
        .response-box {{
            background: #f0fdf4;
            border: 1px solid #bbf7d0;
            border-radius: 0.35rem;
            padding: 0.75rem;
            font-size: 0.85rem;
            line-height: 1.5;
            white-space: pre-wrap;
            word-wrap: break-word;
            color: #1e293b;
        }}

        /* Verdict */
        .verdict-box {{
            background: #eff6ff;
            border: 1px solid #bfdbfe;
            border-left: 4px solid #2563eb;
            border-radius: 0.35rem;
            padding: 1.25rem;
            font-size: 0.95rem;
            line-height: 1.6;
            white-space: pre-wrap;
            word-wrap: break-word;
            color: #1e3a5f;
        }}

        /* Findings & Risks */
        .findings-list, .risks-list {{
            list-style: none;
            padding: 0;
        }}
        .finding-item {{
            padding: 0.5rem 0.75rem;
            background: #eff6ff;
            border-left: 3px solid #3b82f6;
            margin-bottom: 0.4rem;
            border-radius: 0 0.25rem 0.25rem 0;
        }}
        .risk-item {{
            padding: 0.5rem 0.75rem;
            background: #fef2f2;
            border-left: 3px solid #ef4444;
            margin-bottom: 0.4rem;
            border-radius: 0 0.25rem 0.25rem 0;
        }}

        /* Footer */
        .report-footer {{
            text-align: center;
            padding: 1rem 0;
            color: #94a3b8;
            font-size: 0.75rem;
            border-top: 1px solid #e2e8f0;
            margin-top: 1rem;
        }}
    </style>
</head>
<body>
    <div class="report-header">
        <h1>Synapse Council</h1>
        <div class="report-subtitle">Informe de Debate Multi-Modelo con Inteligencia Artificial</div>
        <div>
            <span class="status-badge">{status.upper()}</span>
        </div>
        <div class="report-meta" style="margin-top: 0.75rem;">
            <strong>Tema:</strong> {_escape_html(topic)}<br>
            <strong>Fecha:</strong> {dt_created.strftime("%d/%m/%Y %H:%M")} UTC &mdash; {dt_completed.strftime("%H:%M")} UTC &nbsp;|&nbsp; <strong>Duracion:</strong> {_format_latency(int(duration * 1000))}
        </div>
    </div>

    <table class="stats-table">
        <tr>
            <td><div class="stat-label">Agentes</div><div class="stat-value">{len(turns)}</div></td>
            <td><div class="stat-label">Tokens Generados</div><div class="stat-value">{_format_tokens(total_tokens_out)}</div></td>
            <td><div class="stat-label">Tokens Consumidos</div><div class="stat-value">{_format_tokens(total_tokens_in)}</div></td>
            <td><div class="stat-label">Duracion Total</div><div class="stat-value">{_format_latency(int(duration * 1000))}</div></td>
            <td><div class="stat-label">Nivel de Consenso</div><div class="stat-value">{consensus_level}%</div><div class="consensus-bar"><div class="consensus-fill" style="width: {consensus_level}%"></div></div></td>
        </tr>
    </table>

    <div class="section">
        <div class="section-title">Metricas de Rendimiento</div>
        <div class="charts-row">
            <div class="chart-box">{tokens_chart}</div>
            <div class="chart-box">{latency_chart}</div>
        </div>
    </div>

    <div class="section">
        <div class="section-title">Puntuacion de Agentes</div>
        <table class="scoring-table">
            <thead>
                <tr>
                    <th>Agente</th>
                    <th>Rol</th>
                    <th>Modelo</th>
                    <th style="text-align: right;">Tokens</th>
                    <th style="text-align: right;">Latencia</th>
                    <th style="text-align: center;">Calidad</th>
                </tr>
            </thead>
            <tbody>
                {scoring_rows}
            </tbody>
        </table>
    </div>

    <div class="section">
        <div class="section-title">Desarrollo del Debate</div>
        {turns_html}
    </div>

    <div class="section">
        <div class="section-title">Veredicto Final del Tribunal</div>
        <div class="verdict-box">{_escape_html(verdict) if verdict else "Veredicto no disponible para este debate."}</div>
    </div>

    {findings_html}
    {risks_html}

    <div class="report-footer">
        <strong>Synapse Council v2.0</strong> &mdash; Sistema de Debate Multi-Modelo con IA<br>
        Informe generado el {datetime.now().strftime("%d/%m/%Y %H:%M:%S")} &nbsp;|&nbsp; Debate ID: {debate_data.get("id", "N/A")}
    </div>
</body>
</html>"""

    result = io.BytesIO()
    pisa_status = pisa.CreatePDF(io.StringIO(html), dest=result)

    if pisa_status.err:
        logger.error("report.pdf_conversion_errors", errors=pisa_status.err)

    return result.getvalue()


def save_pdf_report(
    debate_id: str,
    debate_data: Dict[str, Any],
    turns: List[Dict[str, Any]],
    verdict: str = "",
    structured_report: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Genera y guarda un PDF profesional.

    Returns:
        Path al archivo PDF generado
    """
    pdf_bytes = generate_pdf_report(debate_data, turns, verdict, structured_report)

    filename = f"debate_{debate_id[:8]}.pdf"
    filepath = os.path.join(REPORTS_DIR, filename)

    with open(filepath, "wb") as f:
        f.write(pdf_bytes)

    logger.info("report.pdf_generated", debate_id=debate_id, filepath=filepath)
    return filepath


def generate_pdf_from_db(debate_id: str) -> Optional[str]:
    """
    Genera un PDF desde la base de datos.

    Returns:
        Path al archivo PDF o None si falla
    """
    import sqlite3

    db_path = os.path.join(os.path.dirname(__file__), "..", "..", "data", "synapse.db")

    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()

        c.execute("SELECT * FROM sequential_debates WHERE id = ?", (debate_id,))
        debate_row = c.fetchone()
        if not debate_row:
            logger.warning("report.debate_not_found", debate_id=debate_id)
            conn.close()
            return None

        debate_data = dict(debate_row)

        c.execute(
            "SELECT * FROM sequential_debate_turns WHERE debate_id = ? ORDER BY turn_number",
            (debate_id,),
        )
        turns = [dict(row) for row in c.fetchall()]

        conn.close()

        filepath = save_pdf_report(
            debate_id=debate_id,
            debate_data=debate_data,
            turns=turns,
            verdict=debate_data.get("final_verdict", ""),
            structured_report=debate_data.get("structured_report"),
        )

        return filepath

    except Exception as e:
        logger.error("report.pdf_generation_failed", debate_id=debate_id, error=str(e))
        return None
