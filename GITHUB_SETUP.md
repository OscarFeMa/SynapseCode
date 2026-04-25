# 🚀 Guía de Publicación en GitHub - Synapse Council v2.0

## Opción 1: Script Automático (Recomendado)

```batch
cd C:\Users\usuario\Desktop\Synapse_Master
push_to_github.bat
```

El script te guiará paso a paso.

---

## Opción 2: Comandos Manuales

### Paso 1: Crear Repositorio en GitHub
1. Ve a: https://github.com/new
2. Nombre del repositorio: `synapse-council`
3. Descripción: "Sistema de razonamiento colectivo multi-agente con consenso IA"
4. Público o Privado (tu elección)
5. **NO** inicializar con README (ya lo tenemos)
6. Click en "Create repository"

### Paso 2: Configurar Local y Subir

```bash
# Ir al directorio
cd C:\Users\usuario\Desktop\Synapse_Master

# Verificar que esté inicializado
git status

# Configurar remote (reemplazar con tu URL)
git remote add origin https://github.com/TU_USUARIO/synapse-council.git

# O si usas SSH:
# git remote add origin git@github.com:TU_USUARIO/synapse-council.git

# Subir código
git push -u origin main
```

---

## 🔐 Autenticación con GitHub

### Opción A: GitHub CLI (Recomendado)
```batch
# Instalar GitHub CLI
winget install GitHub.cli

# Autenticar
gh auth login
# Selecciona: HTTPS → Y → Login with browser

# Subir
git push -u origin main
```

### Opción B: Token de Acceso Personal
1. Ve a: https://github.com/settings/tokens
2. Generar nuevo token (classic)
3. Seleccionar scope: `repo`
4. Copiar token
5. Usar como contraseña al hacer push:

```bash
git push -u origin main
# Username: tu usuario de GitHub
# Password: el token generado (no tu contraseña!)
```

---

## 📋 Resumen de Archivos a Subir

### ✅ Incluidos (~14,700 líneas de código)
- `backend/` - API FastAPI y motores de debate
- `frontend/` - Interfaz React
- `web_interface/` - Interfaz HTML standalone
- `scripts/` - Utilidades (check_db.py, etc.)
- `*.bat` - Scripts de instalación Windows
- `*.md` - Documentación

### ❌ Excluidos (.gitignore)
- `venv/` - Entorno virtual
- `data/*.db` - Base de datos local
- `logs/` - Archivos de log
- `.env` - Variables de entorno (privadas)

---

## 🎯 Comandos de Verificación Post-Push

```bash
# Verificar remote
git remote -v

# Ver ramas
git branch -a

# Ver últimos commits
git log --oneline -5

# Ver estado
git status
```

---

## 🆘 Solución de Problemas

### Error: "remote: Permission denied"
```bash
# No tienes permisos. Verifica:
# 1. Repositorio existe en GitHub
# 2. Eres colaborador (si es privado)
# 3. Usas el token correcto

gh auth status
```

### Error: "fatal: not a git repository"
```bash
# Inicializar
git init
git add .
git commit -m "Initial commit"
```

### Error: "failed to push some refs"
```bash
# Si el repo remoto tiene cambios diferentes:
git pull origin main --rebase
git push origin main
```

---

## 🎉 Después de Subir

### Tu repositorio estará disponible en:
```
https://github.com/TU_USUARIO/synapse-council
```

### Incluye:
- ✅ Código fuente completo
- ✅ Documentación (README, HISTORY, TROUBLESHOOTING)
- ✅ Scripts de instalación Windows
- ✅ Interfaz web lista para usar

### Para clonar en otra máquina:
```bash
git clone https://github.com/TU_USUARIO/synapse-council.git
cd synapse-council
INSTALL_COMPLETE.bat
```

---

## 📝 Notas Importantes

1. **No subir `.env`** - Contiene claves API privadas
2. **No subir `data/*.db`** - Base de datos local
3. **No subir `venv/`** - Se recrea con instalador
4. **Sí subir `.env.example`** - Plantilla de configuración

---

**¿Necesitas ayuda?** Consulta `TROUBLESHOOTING.md` o ejecuta `check_health.bat`
