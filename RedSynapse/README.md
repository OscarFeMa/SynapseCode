# RedSynapse (Experimental)

Módulo en desarrollo experimental. **No integrado** en el pipeline principal de SynapseCode v2.8.

## Contenido

- `src/Master.py` — Implementación alternativa del nodo Master
- `src/Worker.py` — Implementación alternativa del nodo Worker
- `src/config.py` — Configuración del módulo
- `docs/ANDROID_DEPLOYMENT.md` — Notas de despliegue en Android
- `scripts/build_windows.bat` — Script de build para Windows

## Estado

Este módulo fue un experimento de arquitectura Master/Worker independiente.
El sistema principal de SynapseCode (en `backend/`) ya implementa esta funcionalidad
de forma más completa y estable.

**No eliminar** hasta que se confirme que no se necesita para referencia futura.
