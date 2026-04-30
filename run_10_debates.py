"""
Synapse Council v2.0 - Script para ejecutar 10 debates iterativos
Los temas más debatibles del momento con soluciones priorizadas
"""
import asyncio
import json
from datetime import datetime
from typing import List, Dict, Any
import structlog

# Importar el sistema de debate
from backend.engine.sequential_debate_controller import (
    SequentialDebateController,
    DebateAgent,
    AgentRole,
    DebateSession
)

logger = structlog.get_logger()

# =============================================================================
# LOS 10 TEMAS MÁS DEBATIBLES ACTUALMENTE
# =============================================================================

DEBATE_TOPICS = [
    {
        "id": 1,
        "title": "Derechos Legales y Morales de la Inteligencia Artificial",
        "question": "¿Debería la IA avanzada tener derechos morales y estatus legal de persona?",
        "context": "Con el desarrollo de IA cada vez más sofisticada, surge la pregunta fundamental sobre si sistemas con capacidad de razonamiento autónomo merecen consideración moral y protección legal similar a la de personas humanas o corporaciones.",
        "agents": [
            {
                "id": "ethicist_ai",
                "name": "Filósofo de la Ética",
                "role": "analyst",
                "model": "mistral:7b",
                "system_prompt": "Examina el tema desde perspectivas éticas: agencia moral, conciencia, autonomía, sufrimiento capacidad de los sistemas IA. Considera teorías éticas como utilitarismo, deontología y ética de la virtud."
            },
            {
                "id": "legal_scholar",
                "name": "Jurista Constitucional",
                "role": "analyst",
                "model": "llama3:8b",
                "system_prompt": "Analiza implicaciones legales: personalidad jurídica, responsabilidad legal, derechos de propiedad intelectual creada por IA, precedentes históricos (derechos de animales, corporaciones)."
            },
            {
                "id": "tech_skeptic",
                "name": "Crítico Tecnológico",
                "role": "critic",
                "model": "deepseek-r1:7b",
                "system_prompt": "Cuestiona la premisa fundamental: diferencias entre simulación de inteligencia y agencia genuina. Examina si atribuir derechos a IA es una categorial error."
            },
            {
                "id": "sociologist",
                "name": "Sociólogo del Futuro",
                "role": "synthesizer",
                "model": "gemma:7b",
                "system_prompt": "Examina impacto social: cambios en relaciones humano-máquina, desplazamiento laboral, desigualdad potencial, adaptación cultural necesaria."
            }
        ]
    },
    {
        "id": 2,
        "title": "Renta Básica Universal (UBI)",
        "question": "¿Es la Renta Básica Universal una solución viable para la desigualdad económica y la automatización del trabajo?",
        "context": "La automatización amenaza con eliminar millones de empleos. La UBI propone garantizar ingresos a todos los ciudadanos sin condiciones. Se debate su viabilidad económica, efectos psicológicos y sociales, y alternativas.",
        "agents": [
            {
                "id": "economist_ubi",
                "name": "Economista del Trabajo",
                "role": "analyst",
                "model": "mistral:7b",
                "system_prompt": "Analiza desde perspectiva económica: costos fiscales, efectos inflacionarios, comportamiento laboral, experimentos piloto (Finlandia, Kenya, Stockton), viabilidad presupuestaria."
            },
            {
                "id": "social_psychologist",
                "name": "Psicólogo Social",
                "role": "analyst",
                "model": "llama3:8b",
                "system_prompt": "Examina efectos psicológicos y sociales: propósito humano, dignidad a través del trabajo, efectos en salud mental, relaciones sociales, motivación intrínseca vs extrínseca."
            },
            {
                "id": "conservative_critic",
                "name": "Crítico Conservador",
                "role": "critic",
                "model": "deepseek-r1:7b",
                "system_prompt": "Argumenta contra UBI desde perspectiva de responsabilidad individual, ética del trabajo, peligros de dependencia estatal, alternativas como reducción de impuestos."
            },
            {
                "id": "policy_innovator",
                "name": "Innovador de Políticas",
                "role": "synthesizer",
                "model": "gemma:7b",
                "system_prompt": "Explora soluciones híbridas: UBI parcial, servicios universales, impuesto negativo a la renta, economía participativa, modelos alternativos de redistribución."
            }
        ]
    },
    {
        "id": 3,
        "title": "Impuesto a la Riqueza de Multimillonarios",
        "question": "¿Deberían los multimillonarios pagar un impuesto sobre su riqueza total, no solo sobre ingresos?",
        "context": "La concentración de riqueza alcanza niveles históricos. Propuestas como las de Elizabeth Warren sugieren gravar riqueza neta sobre cierto umbral. Se debate sobre justicia fiscal, fuga de capitales, inversión y crecimiento económico.",
        "agents": [
            {
                "id": "tax_economist",
                "name": "Economista Fiscal",
                "role": "analyst",
                "model": "mistral:7b",
                "system_prompt": "Analiza técnicamente: tasas óptimas, efectos recaudatorios, evaluación de activos ilíquidos, costos de administración, implementación internacional coordinada, ejemplos históricos."
            },
            {
                "id": "wealth_defender",
                "name": "Defensor de la Inversión",
                "role": "critic",
                "model": "llama3:8b",
                "system_prompt": "Argumenta contra: fuga de cerebros y capitales, reducción de inversión, efectos en startups, doble tributación, alternativas como impuestos al consumo o carbono."
            },
            {
                "id": "equality_advocate",
                "name": "Defensor de la Igualdad",
                "role": "analyst",
                "model": "deepseek-r1:7b",
                "system_prompt": "Argumenta a favor: desigualdad dañina para democracia, externalidades negativas de la concentración de riqueza, meritocracia vs herencia, beneficios sociales de redistribución."
            },
            {
                "id": "global_coordinator",
                "name": "Coordinador Global",
                "role": "synthesizer",
                "model": "gemma:7b",
                "system_prompt": "Explora soluciones prácticas: coordinación internacional anti-elusión, impuestos mínimos globales, tratados de transparencia financiera, combate a paraísos fiscales."
            }
        ]
    },
    {
        "id": 4,
        "title": "Voto Obligatorio Universal",
        "question": "¿Debería ser obligatorio votar en todas las elecciones, con sanciones por no hacerlo?",
        "context": "Países como Australia y Bélgica tienen voto obligatorio con altas participación. Se debate sobre libertad individual vs deber cívico, calidad del voto, legitimidad democrática, y efectos en la representación.",
        "agents": [
            {
                "id": "democracy_theorist",
                "name": "Teórico de la Democracia",
                "role": "analyst",
                "model": "mistral:7b",
                "system_prompt": "Examina fundamentos democráticos: legitimidad del mandato, representación inclusiva, deber cívico vs libertad negativa, calidad deliberativa vs cantidad de participación."
            },
            {
                "id": "libertarian_critic",
                "name": "Libertario",
                "role": "critic",
                "model": "llama3:8b",
                "system_prompt": "Argumenta contra desde libertad individual: derecho a no participar, votos desinformados, coerción estatal, alternativas como sorteo o democracia líquida."
            },
            {
                "id": "participation_expert",
                "name": "Experto en Participación",
                "role": "synthesizer",
                "model": "deepseek-r1:7b",
                "system_prompt": "Analiza sistemas híbridos: voto facilitado pero no obligatorio, educación cívica obligatoria, incentivos vs sanciones, tecnología para accesibilidad."
            }
        ]
    },
    {
        "id": 5,
        "title": "Prohibición de IA en Industrias Creativas",
        "question": "¿Debería prohibirse o restringirse severamente el uso de IA en arte, música, escritura y otras industrias creativas?",
        "context": "Herramientas como DALL-E, Midjourney y ChatGPT generan obras creativas competitivas. Artistas protestan por destrucción de medios de vida y dilución del valor humano del arte.",
        "agents": [
            {
                "id": "artist_advocate",
                "name": "Defensor de Artistas",
                "role": "analyst",
                "model": "mistral:7b",
                "system_prompt": "Defiende perspectiva creativa: valor del esfuerzo humano, conexión emocional artista-obra, destrucción de industrias, explotación de datasets sin consentimiento."
            },
            {
                "id": "tech_optimist",
                "name": "Optimista Tecnológico",
                "role": "critic",
                "model": "llama3:8b",
                "system_prompt": "Argumenta por IA como herramienta: democratización de la creación, nuevas formas de arte, colaboración humano-IA, imposibilidad de detener progreso tecnológico."
            },
            {
                "id": "ip_lawyer",
                "name": "Abogado de Propiedad Intelectual",
                "role": "analyst",
                "model": "deepseek-r1:7b",
                "system_prompt": "Examina legalidad: copyright de obras generadas por IA, entrenamiento con datos protegidos, derechos de artistas individuales, necesidad de nuevos marcos legales."
            },
            {
                "id": "culture_historian",
                "name": "Historiador Cultural",
                "role": "synthesizer",
                "model": "gemma:7b",
                "system_prompt": "Contextualiza históricamente: fotografía y pintura, sintetizadores y música, adaptación previa de artistas, evolución de la noción de 'arte'. Propone modelos de coexistencia."
            }
        ]
    },
    {
        "id": 6,
        "title": "Colonización Humana de Marte",
        "question": "¿Debería la humanidad priorizar la colonización de Marte, y quién debería financiarla y controlarla?",
        "context": "SpaceX, NASA y otros proponen misiones tripuladas a Marte en décadas. Se debate sobre prioridad frente a problemas terrestres, riesgos éticos para colonos, gobernanza espacial, y distribución de beneficios.",
        "agents": [
            {
                "id": "space_engineer",
                "name": "Ingeniero Espacial",
                "role": "analyst",
                "model": "mistral:7b",
                "system_prompt": "Evalúa viabilidad técnica: tecnologías necesarias, timelines realistas, sostenibilidad de asentamientos, terraformación posible, riesgos de radiación y salud."
            },
            {
                "id": "earth_priority",
                "name": "Defensor de la Tierra",
                "role": "critic",
                "model": "llama3:8b",
                "system_prompt": "Argumenta contra la prioridad: cambio climático, pobreza, enfermedades, costos astronómicos vs ROI social, ética de gastar recursos en escape planetario."
            },
            {
                "id": "space_ethicist",
                "name": "Eticista Espacial",
                "role": "analyst",
                "model": "deepseek-r1:7b",
                "system_prompt": "Examina dilemas éticos: consentimiento informado de colonos, tratado de colonos nacidos en Marte, propiedad de recursos, contaminación planetaria, derechos de Marte como entidad."
            },
            {
                "id": "governance_designer",
                "name": "Diseñador de Gobernanza",
                "role": "synthesizer",
                "model": "gemma:7b",
                "system_prompt": "Propone modelos de gobernanza: Tratado Espacial actual vs nuevo marco, representación de intereses terrestres vs marcianos, economía autosuficiente, resolución de conflictos."
            }
        ]
    },
    {
        "id": 7,
        "title": "Privacidad de Datos vs Beneficios Corporativos",
        "question": "¿Es ético que las corporaciones recolecten, analicen y vendan datos personales de usuarios?",
        "context": "Modelos de negocio de big tech dependen de datos de usuarios. Se debate sobre consentimiento real, transparencia, algoritmos de manipulación, y si los beneficios (servicios gratuitos) justifican el costo de privacidad.",
        "agents": [
            {
                "id": "privacy_advocate",
                "name": "Defensor de la Privacidad",
                "role": "analyst",
                "model": "mistral:7b",
                "system_prompt": "Argumenta por derechos de privacidad: consentimiento no informado, manipulación algorítmica, sesgos en datos, vigilancia corporativa, externalidades negativas de modelos de atención."
            },
            {
                "id": "innovation_economist",
                "name": "Economista de la Innovación",
                "role": "critic",
                "model": "llama3:8b",
                "system_prompt": "Defiende modelo actual: servicios gratuitos financiados por publicidad, personalización beneficiosa, innovación habilitada por datos, imposibilidad económica de alternativas sin publicidad."
            },
            {
                "id": "data_ethicist",
                "name": "Eticista de Datos",
                "role": "synthesizer",
                "model": "deepseek-r1:7b",
                "system_prompt": "Propone marcos intermedios: privacidad diferencial, datos federados, compensación a usuarios, regulación GDPR/CCPA mejorada, estándares éticos corporativos vinculantes."
            }
        ]
    },
    {
        "id": 8,
        "title": "Control de Armas de Fuego",
        "question": "¿Debería prohibirse o restringirse severamente la compra y posesión de armas de fuego para civiles?",
        "context": "Violencia con armas es problema grave en EEUU y otros países. Se debate sobre derecho constitucional (Segunda Enmienda), efectividad de restricciones, defensa personal, y reducción de violencia vs desarme de ciudadanos honrados.",
        "agents": [
            {
                "id": "violence_researcher",
                "name": "Investigador de Violencia",
                "role": "analyst",
                "model": "mistral:7b",
                "system_prompt": "Presenta evidencia empírica: correlación posesión de armas-violencia, efectividad de leyes de control, comparación internacional, suicidios y accidentes, defensa doméstica real."
            },
            {
                "id": "rights_defender",
                "name": "Defensor de Derechos Constitucionales",
                "role": "critic",
                "model": "llama3:8b",
                "system_prompt": "Argumenta por derechos: Segunda Enmienda, defensa contra tiranía, autonomía personal, ineficacia de prohibiciones (mercado negro), desarme selectivo perjudica a ciudadanos honrados."
            },
            {
                "id": "public_health_expert",
                "name": "Experto en Salud Pública",
                "role": "synthesizer",
                "model": "deepseek-r1:7b",
                "system_prompt": "Propone enfoque de salud pública: almacenamiento seguro, verificación universal de antecedentes, prohibición de venta a menores, licencias de capacidad, programs de buyback, sin prohibición total."
            }
        ]
    },
    {
        "id": 9,
        "title": "Abolición de la Pena de Muerte",
        "question": "¿Debería abolirse la pena de muerte en todos los países que aún la practican?",
        "context": "105 países han abolido la pena de muerte. Se debate sobre justicia retributiva vs rehabilitación, inocentes ejecutados, disuasión de crimen, costos vs cadena perpetua, y evolución moral de la sociedad.",
        "agents": [
            {
                "id": "abolitionist",
                "name": "Abolicionista",
                "role": "analyst",
                "model": "mistral:7b",
                "system_prompt": "Argumenta por abolición: inocentes ejecutados, sesgo racial y de clase, costos superiores a cadena perpetua, falta de disuasión demostrable, evolución moral, alternativas como cadena perpetua real."
            },
            {
                "id": "retributive_justice",
                "name": "Defensor de Justicia Retributiva",
                "role": "critic",
                "model": "llama3:8b",
                "system_prompt": "Argumenta a favor: crímenes atroces merecen castigo proporcional, cierre para víctimas, disuasión para crímenes graves, justicia por los caídos, encarcelamiento perpetuo puede ser peor que muerte."
            },
            {
                "id": "restorative_expert",
                "name": "Experto en Justicia Restaurativa",
                "role": "synthesizer",
                "model": "deepseek-r1:7b",
                "system_prompt": "Propone paradigma restaurativo: enfoque en reparación a víctimas, rehabilitación cuando posible, reconocimiento de daño por parte de ofensor, reconciliación, prevención de reincidencia."
            }
        ]
    },
    {
        "id": 10,
        "title": "Abolición de Exámenes Estandarizados",
        "question": "¿Deberían abolirse los exámenes estandarizados (SAT, selectividad) en el proceso educativo?",
        "context": "Los tests estandarizados son criticados por sesgo socioeconómico, reducir educación a memorización, y no medir habilidades importantes. Defensores argumentan predictibilidad, estandarización justa, y méritoocracia objetiva.",
        "agents": [
            {
                "id": "equity_educator",
                "name": "Educador por la Equidad",
                "role": "analyst",
                "model": "mistral:7b",
                "system_prompt": "Argumenta contra tests: sesgo socioeconómico, ventaja de preparación costosa, reducción del currículo a 'enseñar para el test', no miden creatividad ni pensamiento crítico."
            },
            {
                "id": "merit_defender",
                "name": "Defensor del Mérito",
                "role": "critic",
                "model": "llama3:8b",
                "system_prompt": "Argumenta a favor: objetividad vs subjetividad de calificaciones, predictibilidad de éxito académico, estandarización permite comparación justa, alternativas (ensayos, entrevistas) son más sesgables."
            },
            {
                "id": "holistic_assessor",
                "name": "Evaluador Holístico",
                "role": "synthesizer",
                "model": "deepseek-r1:7b",
                "system_prompt": "Propone evaluación holística: portafolios de trabajo, proyectos de largo plazo, evaluación formativa continua, habilidades socioemocionales, múltiples medidas combinadas inteligentemente."
            }
        ]
    }
]


async def run_single_debate(controller: SequentialDebateController, topic_config: Dict[str, Any]) -> DebateSession:
    """Ejecuta un debate individual con el sistema iterativo"""
    
    topic = topic_config["question"]
    session_id = f"debate_{topic_config['id']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    print(f"\n{'='*80}")
    print(f"🎯 DEBATE #{topic_config['id']}: {topic_config['title']}")
    print(f"{'='*80}")
    print(f"📋 Contexto: {topic_config['context'][:150]}...")
    print(f"🤖 Agentes: {len(topic_config['agents'])}")
    print(f"⏳ Iniciando...")
    
    # Crear agentes
    agents = []
    for agent_data in topic_config["agents"]:
        agent = DebateAgent(
            id=agent_data["id"],
            name=agent_data["name"],
            role=AgentRole(agent_data["role"]),
            node="LOCAL",
            engine="ollama",
            model=agent_data["model"],
            provider=agent_data["model"].split(":")[0] if ":" in agent_data["model"] else "unknown",
            system_prompt=agent_data["system_prompt"],
            temperature=0.7,
            max_tokens=800
        )
        agents.append(agent)
    
    # Ejecutar debate iterativo
    session = await controller.run_iterative_debate(
        session_id=session_id,
        topic=topic,
        agents_config=agents,
        max_iterations=3,
        on_iteration_complete=lambda i: print(f"  ✓ Iteración {i.iteration_number} completada ({len(i.turns)} turnos, {len(i.cruzamientos)} cruzamientos)"),
        on_cruzamiento=lambda c: print(f"    ↳ {c.from_agent} → {c.to_agent}")
    )
    
    print(f"✅ Debate #{topic_config['id']} completado: {len(session.turns)} turnos totales")
    
    return session


async def generate_master_report(all_sessions: List[DebateSession], output_path: str):
    """Genera el documento maestro con todos los debates"""
    
    report_lines = [
        "# 📚 REGISTRO MAESTRO: 10 DEBATES SOBRE LOS TEMAS MÁS DEBATIBLES",
        "",
        f"**Generado:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"**Total de Debates:** {len(all_sessions)}",
        f"**Sistema:** Synapse Council v2.0 - Debate Iterativo",
        "",
        "---",
        "",
        "## 📋 ÍNDICE DE DEBATES",
        ""
    ]
    
    # Índice
    for idx, session in enumerate(all_sessions, 1):
        topic_title = DEBATE_TOPICS[idx-1]["title"]
        report_lines.append(f"{idx}. [{topic_title}](#debate-{idx})")
    
    report_lines.extend(["", "---", ""])
    
    # Cada debate en detalle
    for idx, session in enumerate(all_sessions, 1):
        topic_config = DEBATE_TOPICS[idx-1]
        
        report_lines.extend([
            f"## 🎯 DEBATE #{idx}: {topic_config['title']} {{#debate-{idx}}}",
            "",
            f"**Pregunta Central:** {topic_config['question']}",
            "",
            f"**Contexto:** {topic_config['context']}",
            "",
            f"**Estado:** {session.status}",
            f"**Iteraciones:** {len(session.iterations)}",
            f"**Turnos Totales:** {len(session.turns)}",
            f"**Consenso Alcanzado:** {'Sí' if session.consensus_reached else 'No'}",
            "",
            "### 🤖 Participantes",
            ""
        ])
        
        for agent_data in topic_config["agents"]:
            report_lines.append(f"- **{agent_data['name']}** ({agent_data['role']}): {agent_data['model']}")
        
        report_lines.extend(["", "### 🔄 Iteraciones", ""])
        
        for iteration in session.iterations:
            report_lines.extend([
                f"#### Iteración {iteration.iteration_number} ({iteration.phase})",
                f"- **Turnos:** {len(iteration.turns)}",
                f"- **Cruzamientos:** {len(iteration.cruzamientos)}",
                f"- **Puntos de Consenso:** {len(iteration.consensus_points)}",
                f"- **Puntos de Desacuerdo:** {len(iteration.disagreement_points)}",
                ""
            ])
            
            if iteration.cruzamientos:
                report_lines.append("**Cruzamientos Críticos:**")
                for cruz in iteration.cruzamientos[:3]:  # Top 3
                    report_lines.append(f"- {cruz.from_agent} → {cruz.to_agent}: {cruz.response[:100]}...")
                report_lines.append("")
        
        report_lines.extend(["", "### 💡 Soluciones y Conclusiones", ""])
        
        # Veredicto del tribunal
        if session.tribunal_verdict:
            report_lines.extend([
                "**Veredicto del Tribunal:**",
                "",
                f"```json\n{json.dumps(session.tribunal_verdict, indent=2, ensure_ascii=False)}\n```",
                ""
            ])
        
        # Reporte estructurado
        if session.structured_report:
            report_lines.extend([
                "**Reporte Estructurado:**",
                "",
                f"- **Conclusión Principal:** {session.structured_report.get('final_conclusion', 'N/A')[:200]}...",
                f"- **Confianza:** {session.structured_report.get('confidence_score', 0):.0%}",
                ""
            ])
            
            if session.structured_report.get('key_points'):
                report_lines.append("**Puntos Clave:**")
                for point in session.structured_report['key_points'][:5]:
                    report_lines.append(f"- {point}")
                report_lines.append("")
            
            if session.structured_report.get('recommendations'):
                report_lines.append("**💡 Soluciones/Recomendaciones Propuestas:**")
                for rec in session.structured_report['recommendations'][:5]:
                    report_lines.append(f"- {rec}")
                report_lines.append("")
        
        report_lines.extend(["", "---", ""])
    
    # Resumen ejecutivo
    report_lines.extend([
        "",
        "# 📊 RESUMEN EJECUTIVO",
        "",
        "## Métricas Globales",
        "",
        f"- **Total de Debates Completados:** {len([s for s in all_sessions if s.status == 'completed'])}",
        f"- **Total de Turnos Generados:** {sum(len(s.turns) for s in all_sessions)}",
        f"- **Total de Iteraciones:** {sum(len(s.iterations) for s in all_sessions)}",
        f"- **Consensos Alcanzados:** {sum(1 for s in all_sessions if s.consensus_reached)}/{len(all_sessions)}",
        "",
        "## Temas por Nivel de Controversia (Estimado)",
        ""
    ])
    
    # Guardar reporte
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(report_lines))
    
    print(f"\n📄 Reporte maestro generado: {output_path}")
    
    return output_path


async def main():
    """Función principal que ejecuta los 10 debates"""
    
    print("\n" + "="*80)
    print("🚀 SYNAPSE COUNCIL v2.0 - MARATÓN DE 10 DEBATES")
    print("="*80)
    print(f"\n📅 Inicio: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📝 Temas a debatir: {len(DEBATE_TOPICS)}")
    print(f"🔄 Sistema: Iterativo con cruzamientos críticos")
    print(f"⏱️  Estimado: Tiempo variable según complejidad")
    print("\n" + "="*80 + "\n")
    
    # Inicializar controller
    controller = SequentialDebateController()
    
    all_sessions = []
    
    for topic_config in DEBATE_TOPICS:
        try:
            session = await run_single_debate(controller, topic_config)
            all_sessions.append(session)
        except Exception as e:
            print(f"❌ Error en debate #{topic_config['id']}: {e}")
            logger.error(f"Error en debate {topic_config['id']}", error=str(e))
    
    print(f"\n{'='*80}")
    print("✅ TODOS LOS DEBATES COMPLETADOS")
    print(f"{'='*80}\n")
    
    # Generar reporte maestro
    output_path = f"data/debates/MASTER_REPORT_10_DEBATES_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    await generate_master_report(all_sessions, output_path)
    
    print(f"\n{'='*80}")
    print("🎉 PROCESO COMPLETO")
    print(f"{'='*80}")
    print(f"\n📊 Resumen:")
    print(f"   - Debates completados: {len(all_sessions)}")
    print(f"   - Total de turnos: {sum(len(s.turns) for s in all_sessions)}")
    print(f"   - Documento maestro: {output_path}")
    print(f"\n⏰ Fin: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80 + "\n")
    
    return all_sessions


if __name__ == "__main__":
    asyncio.run(main())
