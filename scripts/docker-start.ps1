# Synapse Council - Start Script para Docker (PowerShell)
# Uso: .\scripts\docker-start.ps1 [opciones]

$ErrorActionPreference = "Stop"

# Colores
$Green = "`e[32m"
$Blue = "`e[34m"
$Yellow = "`e[33m"
$Red = "`e[31m"
$NC = "`e[0m"

Write-Host "${Blue}🚀 Synapse Council - Docker Start (Windows)${NC}"
Write-Host "=============================================="

# Verificar Docker
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Host "${Red}❌ Docker no está instalado${NC}"
    Write-Host "   Instala Docker Desktop: https://www.docker.com/products/docker-desktop"
    exit 1
}

# Verificar Docker Compose
$composeCmd = $null
if (docker compose version 2>$null) {
    $composeCmd = "docker compose"
} elseif (Get-Command docker-compose -ErrorAction SilentlyContinue) {
    $composeCmd = "docker-compose"
}

if (-not $composeCmd) {
    Write-Host "${Red}❌ Docker Compose no está instalado${NC}"
    exit 1
}

Write-Host "${Green}✅ Docker detectado${NC}"
Write-Host "   Comando: $composeCmd"

# Verificar .env
if (-not (Test-Path .env)) {
    Write-Host "${Yellow}⚠️  Archivo .env no encontrado${NC}"
    if (Test-Path .env.example) {
        Copy-Item .env.example .env
        Write-Host "   ✅ .env creado desde ejemplo"
    } else {
        Write-Host "   ${Yellow}No hay .env.example, necesitas crear .env manualmente${NC}"
    }
}

# Parsear argumentos
$MODE = $args[0]
if (-not $MODE) { $MODE = "up" }

switch ($MODE) {
    "up" {
        Write-Host ""
        Write-Host "${Blue}📦 Iniciando servicios...${NC}"
        Invoke-Expression "$composeCmd up -d"
        
        Write-Host ""
        Write-Host "${Green}⏳ Esperando a que los servicios estén listos...${NC}"
        Start-Sleep -Seconds 10
        
        Write-Host ""
        Write-Host "${Blue}🔍 Verificando estado...${NC}"
        Invoke-Expression "$composeCmd ps"
        
        Write-Host ""
        Write-Host "${Green}✅ Synapse Council iniciado!${NC}"
        Write-Host ""
        Write-Host "   📡 API Master: http://localhost:8000"
        Write-Host "   🔧 Ollama Worker: http://localhost:11434"
        Write-Host "   📊 Health Check: http://localhost:8000/health"
        Write-Host ""
        Write-Host "${Yellow}📝 Comandos útiles:${NC}"
        Write-Host "   Ver logs:  $composeCmd logs -f"
        Write-Host "   Detener:   $composeCmd down"
        Write-Host "   Escalar:   $composeCmd up -d --scale worker=3"
    }
    
    "down" {
        Write-Host ""
        Write-Host "${Blue}🛑 Deteniendo servicios...${NC}"
        Invoke-Expression "$composeCmd down"
        Write-Host "${Green}✅ Servicios detenidos${NC}"
    }
    
    "restart" {
        Write-Host ""
        Write-Host "${Blue}🔄 Reiniciando servicios...${NC}"
        Invoke-Expression "$composeCmd restart"
        Write-Host "${Green}✅ Servicios reiniciados${NC}"
    }
    
    "logs" {
        Write-Host ""
        Write-Host "${Blue}📋 Mostrando logs...${NC}"
        Invoke-Expression "$composeCmd logs -f"
    }
    
    "build" {
        Write-Host ""
        Write-Host "${Blue}🔨 Reconstruyendo imágenes...${NC}"
        Invoke-Expression "$composeCmd build --no-cache"
        Write-Host "${Green}✅ Imágenes reconstruidas${NC}"
    }
    
    "status" {
        Write-Host ""
        Write-Host "${Blue}📊 Estado de servicios:${NC}"
        Invoke-Expression "$composeCmd ps"
    }
    
    "clean" {
        Write-Host ""
        Write-Host "${Yellow}🧹 Limpiando contenedores y volúmenes...${NC}"
        Invoke-Expression "$composeCmd down -v --remove-orphans"
        docker system prune -f
        Write-Host "${Green}✅ Limpieza completada${NC}"
    }
    
    default {
        Write-Host "Uso: .\scripts\docker-start.ps1 [up|down|restart|logs|build|status|clean]"
        Write-Host ""
        Write-Host "Comandos:"
        Write-Host "  up       - Iniciar todos los servicios"
        Write-Host "  down     - Detener servicios"
        Write-Host "  restart  - Reiniciar servicios"
        Write-Host "  logs     - Ver logs en tiempo real"
        Write-Host "  build    - Reconstruir imágenes Docker"
        Write-Host "  status   - Ver estado de servicios"
        Write-Host "  clean    - Limpiar todo (¡cuidado!)"
    }
}
