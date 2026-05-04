# 🌐 PROPUESTA: WEB AGENT + ARQUITECTURA DOS CAPAS

**Documento:** PROPUESTA_WEB_AGENT_20260503_1444.md  
**Fecha:** 3 de Mayo de 2026  
**Hora:** 14:44 UTC+2  
**Proyecto:** Synapse Council v2.1.0  
**Autor:** Óscar Fernández Martínez

---

## 📋 RESUMEN EJECUTIVO

**Objetivo:** Extender Synapse Council para incluir IAs Web gratuitas (Gemini, Claude, ChatGPT, Kimi, Deepseek, Copilot) trabajando en paralelo con el Worker Local, maximizando la calidad del debate mediante arquitectura de "Dos Capas" en la primera iteración.

**Motivación:** Los modelos Web tienen información actualizada (2024-2025) que los modelos locales no poseen. Combinar ambas fuentes crea debates de mayor riqueza factual y dialéctica.

**Alcance:** 15-25 agentes por debate (mezcla Web + Local), iteraciones cruzadas, validación masiva, consenso ponderado.

---

## 🎯 ARQUITECTURA PROPUESTA

### **Visión General: "Consejo Ampliado"**

```
┌─────────────────────────────────────────────────────────────────┐
│                    SYNAPSE COUNCIL v3.0                         │
│                     Web + Local Hybrid                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ITERACIÓN 1: EXPLORACIÓN MASIVA (Dos Capas)                      │
│  ┌─────────────────────────────────────────────────────────┐     │
│  │ CAPA A: FUNDAMENTO LOCAL (0-15s)                        │     │
│  │ ├─ 5-8 Analistas Locales (Mistral, Llama3, Deepseek-7B) │     │
│  │ ├─ Paralelo completo                                    │     │
│  │ ├─ Input: Tema limpio                                   │     │
│  │ └─ Output: Síntesis Local (estructura base)             │     │
│  └─────────────────────────────────────────────────────────┘     │
│                              ↓                                    │
│  ┌─────────────────────────────────────────────────────────┐     │
│  │ CAPA B: CONSTRUCCIÓN WEB (15-40s)                       │     │
│  │ ├─ 5-8 Analistas Web (Gemini, Claude, GPT, Kimi...)     │     │
│  │ ├─ Paralelo enriquecido                                 │     │
│  │ ├─ Input: Tema + Síntesis Local                         │     │
│  │ └─ Output: Síntesis Web (info actualizada 2024)         │     │
│  └─────────────────────────────────────────────────────────┘     │
│                              ↓                                    │
│              CONTEXT CORAL V1 = Local + Web                     │
│                                                                   │
│  ITERACIÓN 2: CRÍTICA CRUZADA (Paralelo puro)                    │
│  ├─ 5 Críticos Web + 5 Críticos Local                           │
│  ├─ Contexto: Coral V1 completo                                 │
│  └─ 10 perspectivas de crítica                                  │
│                                                                   │
│  ITERACIÓN 3: VALIDACIÓN MASIVA                                  │
│  ├─ 3 Validadores Web (hechos actuales)                         │
│  ├─ 2 Validadores Local (lógica)                                │
│  └─ Jurado extendido 5 miembros                                 │
│                                                                   │
│  ITERACIÓN 4: SÍNTESIS Y CONSENSO                               │
│  ├─ 5 Síntesis Web + 3 Síntesis Local                           │
│  ├─ Votación ponderada (Web x1.5, Local x1.0)                   │
│  └─ Veredicto final con ≥70% consenso                         │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🏗️ COMPONENTES DEL SISTEMA

### **1. Web Agent Service (Nuevo Módulo)**

```
backend/
└── engine/
    └── web_agent/
        ├── __init__.py
        ├── base.py                    # Interfaz BaseWebAgent
        ├── adapter_manager.py           # Gestor de adapters
        ├── adapters/
        │   ├── __init__.py
        │   ├── gemini_adapter.py      # Google Gemini Web
        │   ├── claude_adapter.py      # Anthropic Claude Web
        │   ├── chatgpt_adapter.py     # OpenAI ChatGPT Web
        │   ├── kimi_adapter.py        # Moonshot Kimi Web
        │   ├── deepseek_adapter.py    # Deepseek Web
        │   ├── copilot_adapter.py     # Microsoft Copilot
        │   └── perplexity_adapter.py  # Perplexity AI
        ├── context_manager.py         # Gestión de contexto híbrido
        ├── rate_limiter.py            # Control de límites por plataforma
        └── health_monitor.py          # Monitor de disponibilidad
```

**Responsabilidades:**
- Abstracción de cada IA Web (APIs no oficiales o browser automation)
- Rate limiting por cuenta/plataforma
- Rotación de credenciales
- Fallback automático entre IAs

---

### **2. Hybrid Engine Manager (Extensión)**

```python
class HybridEngineManager:
    """
    Unifica Local (Worker) + Web en interfaz única
    """
    
    def __init__(self):
        # Engines existentes
        self.local_engines = {
            'ollama': OllamaClient(),
            'lm_studio': LMStudioClient(),
        }
        
        # Nuevos: Web Engines
        self.web_engines = {
            'gemini': GeminiAdapter(),
            'claude': ClaudeAdapter(),
            'chatgpt': ChatGPTAdapter(),
            'kimi': KimiAdapter(),
            'deepseek': DeepseekWebAdapter(),
            'copilot': CopilotAdapter(),
        }
    
    async def generate(self, agent_config: AgentConfig, 
                      prompt: str, context: Context) -> Response:
        """
        Interfaz unificada: no importa si es Worker o Web
        """
        if agent_config.source == 'local':
            return await self.local_engines[agent_config.engine].generate(...)
        elif agent_config.source == 'web':
            return await self.web_engines[agent_config.platform].generate(...)
```

---

### **3. Sistema de Dos Capas (Iteración 1)**

```python
class TwoLayerIterationController:
    """
    Controlador especial para Iteración 1:
    Capa A (Local) → Merge → Capa B (Web enriquecido)
    """
    
    async def execute_first_iteration(self, topic: str, config: DebateConfig):
        # === CAPA A: FUNDAMENTO LOCAL ===
        local_agents = config.get_local_agents()  # 5-8 modelos
        
        # Lanzar todos en paralelo
        local_tasks = [
            self.local_engine.generate(agent, topic) 
            for agent in local_agents
        ]
        local_responses = await asyncio.gather(*local_tasks)
        
        # Generar Síntesis Local
        local_synthesis = await self.generate_synthesis(
            responses=local_responses,
            source="local",
            method="consensos_y_disputas"
        )
        
        # === CAPA B: CONSTRUCCIÓN WEB ===
        web_agents = config.get_web_agents()  # 5-8 modelos
        
        # Preparar prompts enriquecidos
        enriched_prompts = [
            self.build_enriched_prompt(
                topic=topic,
                local_synthesis=local_synthesis,
                agent_role=agent.role
            )
            for agent in web_agents
        ]
        
        # Lanzar Web en paralelo (con contexto Local)
        web_tasks = [
            self.web_engine.generate(agent, prompt)
            for agent, prompt in zip(web_agents, enriched_prompts)
        ]
        web_responses = await asyncio.gather(*web_tasks)
        
        # Generar Síntesis Web
        web_synthesis = await self.generate_synthesis(
            responses=web_responses,
            source="web",
            context=local_synthesis,  # Web sobre base Local
            method="aportes_novedosos"
        )
        
        # === MERGE FINAL: CONTEXT CORAL V1 ===
        coral_context = CoralContext(
            iteration=1,
            local_layer=local_synthesis,
            web_layer=web_synthesis,
            merge_strategy="web_enriquece_local"
        )
        
        return coral_context
```

---

## 🤖 AGENTES PROPUESTOS (15-25 total)

### **Capa A: Fundamento Local (5-8 agentes)**

| Modelo | Rol Primario | Fortaleza |
|--------|--------------|-----------|
| **Mistral-7B** | ANALYST | Razonamiento estructurado |
| **Llama3-8B** | ANALYST | Perspectiva equilibrada |
| **Deepseek-7B** | CRITIC | Lógica profunda |
| **Qwen-7B** | VALIDATOR | Validación técnica |
| **Gemma-7B** | SYNTHESIS | Síntesis clara |
| **Phi3** | ANALYST | Velocidad, análisis rápido |
| **Deepseek-R1-7B** | CRITIC | Razonamiento chain-of-thought |
| **Qwen2.5-7B** | VALIDATOR | Multilingüe, precisión |

**Ventaja:** Todos locales, respuestas en 5-10s, no dependen de internet.

---

### **Capa B: Construcción Web (5-10 agentes)**

| Plataforma | Rol Primario | Fortaleza | Info Actualizada |
|------------|--------------|-----------|------------------|
| **Gemini** | ANALYST | Google Search integrado | ⭐⭐⭐⭐⭐ |
| **Claude 3.5** | VALIDATOR | Hechos y precisión | ⭐⭐⭐⭐ |
| **ChatGPT-4o** | CRITIC | Contra-argumentos | ⭐⭐⭐⭐ |
| **Kimi** | ANALYST | Análisis técnico profundo | ⭐⭐⭐ |
| **Deepseek Web** | CRITIC | Razonamiento lógico | ⭐⭐⭐ |
| **Perplexity** | VALIDATOR | Citas y fuentes | ⭐⭐⭐⭐⭐ |
| **Copilot** | ANALYST | Perspectiva práctica | ⭐⭐⭐ |

**Ventaja:** Acceso a información 2024-2025, hechos actualizados, tendencias actuales.

---

## 📊 FLUJO DE CONTEXTO

### **Context Coral (Estructura Híbrida)**

```
Cada agente (Web o Local) recibe:

┌─────────────────────────────────────────────────────────┐
│ 🧠 CONTEXT CORAL ITERACIÓN [N]                           │
├─────────────────────────────────────────────────────────┤
│                                                          │
│ 📋 TEMA DEL DEBATE                                       │
│    [Título + descripción del problema]                   │
│                                                          │
│ 🎯 TU IDENTIDAD                                          │
│    • Nombre: {agent_name}                                │
│    • Fuente: {local/web}                                 │
│    • Rol: {ANALYST/CRITIC/VALIDATOR/SYNTHESIS}           │
│    • Modelo: {mistral/gemini/claude...}                   │
│                                                          │
│ 🏛️ CONSENSOS ACUMULADOS (≥60% acuerdo)                  │
│    • Punto 1: [descripción] (apoyado por: A, B, C)       │
│    • Punto 2: [descripción] (apoyado por: D, E, F)       │
│                                                          │
│ ⚔️ DISPUTAS ACTIVAS                                      │
│    • Disputa 1: [tema]                                   │
│      - Posición A (Web:Gemini): [argumento]              │
│      - Posición B (Local:Mistral): [contra-argumento]    │
│                                                          │
│ 💡 APORTES CLAVE RECIENTES                               │
│    Web destacados:                                       │
│    • [Punto de Gemini sobre tendencia 2024]              │
│    • [Validación de Perplexity con fuente]               │
│                                                          │
│    Local destacados:                                     │
│    • [Lógica de Deepseek sobre X]                        │
│    • [Síntesis de Gemma estructurando Y]                  │
│                                                          │
│ 📝 TU MISIÓN                                             │
│    [Instrucción específica según rol]                    │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

---

## ⏱️ TIMING Y RENDIMIENTO

### **Iteración 1 (Dos Capas)**

| Fase | Duración | Agentes | Paralelismo |
|------|----------|---------|-------------|
| Capa A (Local) | 10-15s | 5-8 | Completo |
| Merge A | 1-2s | - | Síntesis automática |
| Capa B (Web) | 20-25s | 5-8 | Completo con contexto A |
| Merge B | 1-2s | - | Síntesis automática |
| **Total** | **35-45s** | **10-16** | **Óptimo** |

### **Iteraciones 2-4**

| Iteración | Agentes | Tiempo | Contexto |
|-----------|---------|--------|----------|
| 2 (Crítica) | 8-10 | 40-60s | Coral V1 completo |
| 3 (Validación) | 5 | 30-45s | Coral V2 |
| 4 (Síntesis) | 8 | 40-60s | Coral V3 |
| **Total Debate** | **15-25** | **3-4 horas** | - |

**Nota:** 3-4 horas aceptables para calidad máxima con 15-25 agentes.

---

## 🔐 GESTIÓN DE CREDENCIALES

### **Opción A: Environment Variables (Inicial)**
```bash
# .env
WEB_AGENT_GEMINI_COOKIES="..."
WEB_AGENT_CLAUDE_SESSION="..."
WEB_AGENT_CHATGPT_TOKEN="..."
WEB_AGENT_KIMI_API_KEY="..."
```

### **Opción B: Supabase Vault (Futuro)**
- Credenciales encriptadas en Supabase
- Rotación automática
- Múltiples cuentas por plataforma

---

## 📈 MÉTRICAS DE ÉXITO

### **KPIs del Web Agent**

| Métrica | Target | Medición |
|---------|--------|----------|
| Disponibilidad Web | >90% | % de requests exitosos |
| Tiempo respuesta Web | <30s | Latencia promedio |
| Rate limit hits | <5% | Cuántas veces se alcanza límite |
| Fallback a Local | <10% | Cuándo Web falla |
| Info actualizada | Cualitativo | Comparación con modelos locales |

---

## 🚀 ROADMAP DE IMPLEMENTACIÓN

### **Fase 1: Fundamentos (1-2 semanas)**
- [ ] Crear estructura `backend/engine/web_agent/`
- [ ] Implementar `BaseWebAgent` interface
- [ ] Gemini Adapter (API más estable)
- [ ] Integración con `HybridEngineManager`
- [ ] Primer debate híbrido (5 Local + 1 Web)

### **Fase 2: Expansión (2-3 semanas)**
- [ ] Claude Adapter
- [ ] Kimi Adapter
- [ ] Sistema de Dos Capas (Iteración 1)
- [ ] Context Coral compartido
- [ ] Debate completo (5 Local + 5 Web)

### **Fase 3: Escalado (3-4 semanas)**
- [ ] ChatGPT Adapter
- [ ] Deepseek Web Adapter
- [ ] Perplexity/Copilot opcionales
- [ ] 15-25 agentes simultáneos
- [ ] UI para agregar nuevas IAs Web

### **Fase 4: Optimización (Futuro)**
- [ ] Redis para caché de respuestas Web
- [ ] Múltiples cuentas por plataforma
- [ ] Proxy rotation
- [ ] Kubernetes para Web Agent Service

---

## 🎯 IMPACTO ESPERADO

### **Antes (v2.1.0 - Solo Local)**
```
4-6 agentes locales
Info hasta 2023 (training cutoff)
Tiempo: ~1 hora
Calidad: Buena, pero desactualizada
```

### **Después (v3.0 - Híbrido Web+Local)**
```
15-25 agentes (Web + Local)
Info 2024-2025 en tiempo real
Tiempo: 3-4 horas
Calidad: Superior, factualmente actualizada
```

---

## 📝 NOTAS DE IMPLEMENTACIÓN

### **Consideraciones Técnicas**

1. **Rate Limiting agresivo:** Las IAs Web tienen límites estrictos. Necesitamos:
   - Cola de requests por plataforma
   - Exponential backoff
   - Fallback inmediato a Local si Web falla

2. **Contexto mutable:** Web y Local deben ver el mismo Coral Context, generado dinámicamente.

3. **Sesiones persistentes:** Algunas IAs Web requieren cookies/sesiones. Necesitamos:
   - Cookie jar persistente
   - Renovable automático
   - Múltiples sesiones por plataforma

4. **Error handling:** Las IAs Web son frágiles (cambios de UI, bans, etc.).
   - Circuit breaker pattern
   - Health checks cada 60s
   - Degradación elegante a Local

---

## 🔗 RELACIÓN CON OTRAS MEJORAS

Esta propuesta (Web Agent) se integra con:

| Mejora | Relación |
|--------|----------|
| **Redis + FAISS** | Caché de respuestas Web frecuentes |
| **Context Coral** | Estructura de contexto híbrido Web+Local |
| **Hybrid Memory** | Sync de debates Web+Local a Supabase |
| **Multi-Worker** | Web Agent como "Worker virtual" adicional |
| **Dialectic Entropy** | Medir convergencia con diversidad Web+Local |

---

## ✅ CHECKLIST DE DECISIONES

- [x] Arquitectura: Dos Capas (Local primero, Web después)
- [x] 15-25 agentes simultáneos
- [x] Iteración 1: Local (rápido) → Web (enriquecido)
- [x] Iteraciones 2+: Paralelo puro Web+Local
- [x] Context Coral compartido
- [x] Prioridad: Calidad sobre velocidad
- [ ] Implementación: Por fases (Gemini primero)

---

**Fin de la Propuesta**

*Documento generado: 3 de Mayo de 2026, 14:44*  
*Synapse Council - Fase Web Agent*
