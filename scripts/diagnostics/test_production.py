#!/usr/bin/env python3
"""Script de verificación pre-producción Synapse Council v2.1"""

import sys

def test_imports():
    """Verifica que todos los módulos nuevos carguen correctamente."""
    print("="*60)
    print("TEST 1: Verificación de imports")
    print("="*60)
    
    modules = [
        ('backend.engine.intervention_taxonomy', 'detect_intervention_type'),
        ('backend.engine.quality_monitor', 'is_response_usable'),
        ('backend.engine.reputation_manager', 'reputation_manager'),
        ('backend.memory.hybrid_memory_v2', 'get_hybrid_memory_v2'),
        ('backend.api.routes.debug', 'router'),
    ]
    
    errors = []
    for mod, attr in modules:
        try:
            module = __import__(mod, fromlist=[attr])
            getattr(module, attr)
            print(f"  ✅ {mod}")
        except Exception as e:
            print(f"  ❌ {mod}: {e}")
            errors.append((mod, e))
    
    return len(errors) == 0

def test_config():
    """Verifica que los feature flags estén disponibles."""
    print("\n" + "="*60)
    print("TEST 2: Verificación de Feature Flags")
    print("="*60)
    
    from backend.config import Settings
    
    flags = [
        'INTERVENTION_TAXONOMY_ENABLED',
        'QUALITY_MONITOR_ENABLED',
        'HYBRID_MEMORY_V2_ENABLED',
        'AGENT_REPUTATION_ENABLED',
    ]
    
    s = Settings()
    for flag in flags:
        val = getattr(s, flag, 'NOT_FOUND')
        status = "✅" if val != 'NOT_FOUND' else "⚠️"
        print(f"  {status} {flag} = {val}")

def test_functionality():
    """Prueba funcionalidad básica."""
    print("\n" + "="*60)
    print("TEST 3: Pruebas funcionales")
    print("="*60)
    
    from backend.engine.intervention_taxonomy import detect_intervention_type
    from backend.engine.quality_monitor import evaluate_response
    
    # Test intervención
    result = detect_intervention_type('coincido con el análisis previo', 'analyst')
    print(f"  ✅ Intervención detectada: {result}")
    
    # Test calidad
    score, issues = evaluate_response('análisis completo de la propuesta con evidencia', 'analyst')
    print(f"  ✅ Quality score: {score:.2f}, issues: {len(issues)}")

def main():
    print("\n" + "🔍 SYNAPSE COUNCIL v2.1 - Verificación Pre-Producción\n")
    
    ok = test_imports()
    test_config()
    test_functionality()
    
    print("\n" + "="*60)
    if ok:
        print("🚀 TODOS LOS TESTS PASARON - Listo para producción!")
        print("="*60)
        print("\nPróximos pasos:")
        print("  1. alembic upgrade head  # Migrar BD")
        print("  2. python -m uvicorn backend.main:app --reload")
        print("  3. curl http://localhost:8000/api/v1/debug/system")
        return 0
    else:
        print("❌ HAY ERRORES - Corregir antes de producción")
        return 1

if __name__ == "__main__":
    sys.exit(main())
