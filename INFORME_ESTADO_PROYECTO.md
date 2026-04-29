# Informe de Estado del Proyecto Synapse Council

**Fecha:** 26 de abril de 2026  
**Versión:** 3.0.0

---

## Resumen Ejecutivo

El proyecto Synapse Council es una aplicación desktop (Electron + React) que gestiona la conexión entre un proceso Master y un proceso Worker distribuidos en dos ordenadores de la misma red. El objetivo principal es permitir el descubrimiento automático del Worker y su arranque remoto sin intervención manual.

**Estado actual:** La aplicación está funcional pero el enlace Master/Worker no se establece correctamente. El descubrimiento de IP funciona, pero la conexión entre Master y Worker falla.

---

## Componentes Implementados

### 1. Aplicación Desktop (Electron + React)

**Ubicación:** `d:\proyectos\Synapse\desktop\`

#### Frontend (React + Vite)
- **Ubicación:** `desktop\frontend\`
- **Tecnologías:** React, Vite, TailwindCSS, Lucide Icons
- **Componentes principales:**
  - `ConnectionWindow.jsx`: Ventana de gestión de conexión Master/Worker
  - `Dashboard.jsx`: Panel de visualización de estado y métricas
  - `Chatbox.jsx`: Chat directo a modelos
  - `ModelConfig.jsx`: Panel de configuración de modelos/engines
  - `DatabaseViewer.jsx`: Visualización de debates históricos
  - `DebateModeSelector.jsx`: Selector de modos de debate

#### Backend Electron (Node.js)
- **Ubicación:** `desktop\electron\`
- **Funcionalidades:**
  - Servidor Express local para servir frontend en producción (puerto 5174)
  - Descubrimiento UDP compatible con backend Python (protocolo SYNAPSE_V2)
  - Escaneo de red local para encontrar Worker por puerto
  - Descubrimiento por dirección MAC usando ARP (para IPs dinámicas)
  - Arranque remoto de Worker vía WinRM
  - Apertura de RDP manual como fallback
  - Monitoreo de procesos Master/Worker
  - Comunicación IPC con renderer process

### 2. Backend Python (FastAPI)

**Ubicación:** `d:\proyectos\Synapse\backend\`

#### Componentes principales
- **API REST:** Endpoints para configuración, chat, métricas y health checks
- **Engine:** Sistema de tribunales para debates entre modelos
- **Memory:** Sistema de memoria vectorial para contexto
- **Network:** Sistema de descubrimiento UDP peer-to-peer
- **Database:** Almacenamiento de debates históricos

#### Endpoints API
- `POST /api/v1/system/chat/direct`: Chat directo a modelos
- `GET /api/v1/system/settings`: Configuración del sistema
- `GET /api/v1/system/metrics`: Métricas de rendimiento
- `GET /api/v1/system/health`: Health check

---

## Configuración Actual

### Master (Ordenador `sobremesa`)
- **Usuario:** `sobremesa\usuario`
- **IP dinámica:** Detectada automáticamente
- **Puerto API:** 8000
- **Puerto descubrimiento UDP:** 54321

### Worker (Ordenador `makederpc`)
- **Usuario:** `MAKEDER\maked`
- **MAC:** `E0:0A:F6:9E:CB:01`
- **IP dinámica:** Detectada por MAC/ARP
- **Puerto API:** 8000
- **Puerto descubrimiento UDP:** 54321
- **Carpeta compartida:** `\\MAKEDERPC\Synapse` (permisos para Todos)
- **WinRM:** Configurado (TrustedHosts = *, puerto 5985 abierto)

### Archivo RDP
- **Ubicación:** `D:\proyectos\Synapse\Escritorio.rdp`
- **Función:** Acceso manual al Worker como fallback

---

## Sistema de Descubrimiento Implementado

### 1. Descubrimiento por MAC (Prioridad 1)
- **Método:** ARP table scanning
- **Proceso:**
  1. Ping a toda la subred (192.168.1.x)
  2. Consulta tabla ARP
  3. Busca MAC `E0:0A:F6:9E:CB:01`
  4. Retorna IP asociada
- **Ventaja:** Funciona con IPs dinámicas (DHCP)
- **Estado:** ✅ Implementado y funcional

### 2. Descubrimiento UDP (Prioridad 2)
- **Protocolo:** SYNAPSE_V2
- **Formato mensaje:**
  ```json
  {
    "magic": "SYNAPSE_V2",
    "node_id": "master-{timestamp}",
    "role": "MASTER",
    "port": 8000,
    "timestamp": 1234567890.123
  }
  ```
- **Proceso:**
  1. Master broadcast a 255.255.255.255:54321
  2. Worker responde con su IP y rol
  3. Master filtra mensajes de `role: "WORKER"`
- **Estado:** ✅ Implementado, compatible con backend Python

### 3. Escaneo de Red (Fallback)
- **Método:** Port scanning TCP
- **Proceso:**
  1. Escanea IPs en subred local
  2. Verifica puerto 8000 abierto
  3. Retorna IP del Worker
- **Estado:** ✅ Implementado

---

## Problemas Identificados

### 1. Enlace Master/Worker No Funciona ⚠️

**Síntoma:**
- El descubrimiento de IP funciona correctamente
- La IP del Worker se detecta por MAC
- Al iniciar Master/Worker, no se establece el enlace
- El Worker no responde al Master

**Causas posibles:**
1. **Worker no iniciado correctamente:** El arranque remoto vía WinRM puede estar fallando
2. **Problema de configuración del Worker:** `NODE_ROLE=WORKER` no se está estableciendo correctamente
3. **Firewall del Worker:** Puerto 8000 puede estar bloqueado
4. **Ruta de red incorrecta:** `\\MAKEDERPC\Synapse\backend` puede no ser accesible
5. **Problema de credenciales WinRM:** Usuario `MAKEDER\maked` puede no tener permisos suficientes

**Evidencia:**
- WinRM configurado correctamente (TrustedHosts = *, puerto 5985 abierto)
- Carpeta compartida configurada con permisos para Todos
- RDP funciona correctamente
- Descubrimiento de IP funciona

### 2. Arranque Remoto vía WinRM No Verificado

**Estado:** ❌ No se ha verificado que el arranque remoto funcione

**Comando ejecutado:**
```powershell
cd "\\MAKEDERPC\Synapse\backend" && set NODE_ROLE=WORKER && python -m backend.main
```

**Posibles problemas:**
1. La ruta de red UNC puede no funcionar con `cd`
2. `set NODE_ROLE=WORKER` puede no persistir en el contexto remoto
3. Python puede no estar en el PATH del Worker
4. Dependencias de Python pueden no estar instaladas en `C:\Synapse\backend`

---

## Próximos Pasos

### Prioridad Alta: Corregir Enlace Master/Worker

#### 1. Verificar Arranque Remoto WinRM
- **Acción:** Probar el comando WinRM manualmente desde PowerShell
- **Comando:**
  ```powershell
  winrs -r:MAKEDERPC -u:MAKEDER\maked -p:PASSWORD "cd C:\Synapse\backend && set NODE_ROLE=WORKER && python -m backend.main"
  ```
- **Objetivo:** Verificar que el comando funciona fuera de la aplicación

#### 2. Mejorar Comando de Arranque Remoto
- **Problema actual:** Uso de ruta UNC (`\\MAKEDERPC\...`) que puede no funcionar
- **Solución:** Usar ruta local en el Worker (`C:\Synapse\backend`)
- **Cambio en `electron/main.js`:**
  ```javascript
  const command = `cd C:\\Synapse\\backend && set NODE_ROLE=WORKER && python -m backend.main`;
  ```

#### 3. Verificar Instalación de Dependencias en Worker
- **Acción:** Asegurar que `requirements.txt` está instalado en `C:\Synapse\backend`
- **Comando:**
  ```powershell
  cd C:\Synapse\backend
  pip install -r requirements.txt
  ```

#### 4. Verificar Configuración de Firewall en Worker
- **Acción:** Asegurar que puerto 8000 está abierto en el Worker
- **Comando:**
  ```powershell
  netsh advfirewall firewall add rule name="Synapse API" dir=in action=allow protocol=TCP localport=8000
  ```

#### 5. Agregar Logs Detallados de WinRM
- **Acción:** Capturar salida del comando WinRM para debugging
- **Implementación:** Modificar `startWorkerRemotely` para capturar stdout/stderr

#### 6. Verificar Configuración de NODE_ROLE
- **Problema:** `set NODE_ROLE=WORKER` puede no persistir
- **Solución:** Pasar variable de entorno directamente en el comando
- **Comando alternativo:**
  ```powershell
  $env:NODE_ROLE="WORKER"; python -m backend.main
  ```

### Prioridad Media: Mejoras de UX

#### 1. Indicador Visual de Estado de WinRM
- **Acción:** Mostrar estado de conexión WinRM en la UI
- **Implementación:** Agregar indicador de "Conectado/Desconectado" para WinRM

#### 2. Guardar Credenciales de Forma Segura
- **Acción:** Usar `electron-store` para guardar credenciales encriptadas
- **Beneficio:** No tener que ingresar contraseña cada vez

#### 3. Agregar Logs de Debugging Avanzados
- **Acción:** Agregar toggle para mostrar logs detallados
- **Implementación:** Checkbox "Mostrar logs de debugging"

### Prioridad Baja: Optimizaciones

#### 1. Optimizar Escaneo de MAC
- **Problema:** Escaneo de 254 IPs puede ser lento
- **Solución:** Limitar rango de escaneo o usar técnicas más eficientes

#### 2. Agregar Sistema de Reintento Automático
- **Acción:** Reintentar enlace automáticamente si falla
- **Implementación:** Lógica de retry con backoff exponencial

#### 3. Agregar Notificaciones de Estado
- **Acción:** Notificaciones del sistema cuando Worker se conecta/desconecta
- **Implementación:** Usar `electron-notification` o nativo

---

## Estructura de Archivos

```
d:\proyectos\Synapse\
├── backend\
│   ├── api\
│   ├── engine\
│   ├── memory\
│   ├── network\
│   ├── database\
│   ├── main.py
│   ├── config.py
│   └── requirements.txt
├── desktop\
│   ├── electron\
│   │   ├── main.js
│   │   └── preload.js
│   ├── frontend\
│   │   ├── src\
│   │   │   └── components\
│   │   │       ├── ConnectionWindow.jsx
│   │   │       ├── Dashboard.jsx
│   │   │       ├── Chatbox.jsx
│   │   │       ├── ModelConfig.jsx
│   │   │       ├── DatabaseViewer.jsx
│   │   │       └── DebateModeSelector.jsx
│   │   └── package.json
│   ├── assets\
│   │   └── icon.png
│   ├── package.json
│   └── dist\
│       └── Synapse Council Setup 3.0.0.exe
├── SynapseWorker.zip
└── Escritorio.rdp
```

---

## Configuración de Red

### Topología
```
[Master: sobremesa] <---> [Router] <---> [Worker: makederpc]
IP: 192.168.1.45       192.168.1.1       IP: 192.168.1.43 (dinámica)
```

### Puertos Utilizados
- **8000:** API REST (Master y Worker)
- **54321:** Descubrimiento UDP
- **5173:** Dev server frontend (solo desarrollo)
- **5174:** Local server frontend (producción)
- **5985:** WinRM HTTP

---

## Dependencias Principales

### Desktop (Node.js)
- `electron`: 28.3.3
- `react`: ^18.2.0
- `vite`: ^5.0.0
- `tailwindcss`: ^3.4.0
- `express`: ^4.18.0
- `node-winrm`: ^1.0.0
- `electron-builder`: 24.13.3

### Backend (Python)
- `fastapi`: ^0.104.0
- `uvicorn`: ^0.24.0
- `openai`: ^1.0.0
- `langchain`: ^0.1.0
- `chromadb`: ^0.4.0

---

## Resumen de Tareas Completadas

### ✅ Completado
- [x] Diseño de arquitectura desktop mejorada
- [x] Creación de estructura Electron + React
- [x] Ventana de estado de conexión Master/Worker
- [x] Botón para enlazar Master/Worker
- [x] Auto-descubrimiento UDP mejorado (SYNAPSE_V2)
- [x] Botón para arrancar Master/Worker
- [x] Botón SynapseIA para abrir dashboard
- [x] Dashboard con estado master/worker + velocidades
- [x] Chatbox directo a modelos (unilateral)
- [x] Panel de configuración de modelos/engines
- [x] Visualización de base de datos (debates históricos)
- [x] Selector de modo de debate
- [x] Script wrapper para arrancar master y worker
- [x] Monitoreo de procesos master/worker
- [x] Endpoints API (/settings, /chat/direct, /metrics, /health)
- [x] Instalación de dependencias desktop
- [x] Configuración de empaquetado Electron
- [x] Creación de instalador
- [x] Arreglo de ventana en blanco (Express local)
- [x] Eliminación de DevTools en producción
- [x] Actualización de protocolo UDP para compatibilidad Python
- [x] Escaneo de red local como fallback
- [x] Descubrimiento por dirección MAC usando ARP
- [x] Configuración de carpeta compartida en Worker
- [x] Botón para abrir RDP manualmente
- [x] Configuración de ventana maximizada

### ⚠️ Pendiente
- [ ] Corregir enlace Master/Worker
- [ ] Verificar arranque remoto WinRM
- [ ] Mejorar comando de arranque remoto (usar ruta local)
- [ ] Verificar instalación de dependencias en Worker
- [ ] Verificar configuración de firewall en Worker
- [ ] Agregar logs detallados de WinRM
- [ ] Verificar configuración de NODE_ROLE

---

## Conclusión

El proyecto Synapse Council tiene una arquitectura sólida y la mayoría de los componentes están implementados correctamente. El sistema de descubrimiento automático funciona bien y puede detectar IPs dinámicas usando MAC addresses.

El problema principal es el enlace entre Master y Worker, que parece estar relacionado con el arranque remoto del Worker vía WinRM. Los próximos pasos deben enfocarse en verificar y corregir el comando de arranque remoto, asegurando que el Worker se inicie correctamente con la configuración adecuada.

Una vez resuelto el problema de enlace, el sistema funcionará completamente automático: descubrirá la IP del Worker, lo iniciará remotamente, y establecerá la conexión sin intervención manual.
