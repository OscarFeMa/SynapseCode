#!/bin/bash
# Synapse Council - Start Script para Docker
# Uso: ./scripts/docker-start.sh [opciones]

set -e

# Colores para output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Synapse Council - Docker Start${NC}"
echo "================================"

# Verificar Docker está instalado
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker no está instalado${NC}"
    echo "   Instala Docker: https://docs.docker.com/get-docker/"
    exit 1
fi

# Verificar Docker Compose
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo -e "${RED}❌ Docker Compose no está instalado${NC}"
    exit 1
fi

# Detectar comando de compose (docker-compose o docker compose)
if docker compose version &> /dev/null; then
    COMPOSE_CMD="docker compose"
else
    COMPOSE_CMD="docker-compose"
fi

echo -e "${GREEN}✅ Docker detectado${NC}"
echo "   Comando: $COMPOSE_CMD"

# Verificar .env existe
if [ ! -f .env ]; then
    echo -e "${YELLOW}⚠️  Archivo .env no encontrado${NC}"
    echo "   Creando .env desde ejemplo..."
    cp .env.example .env 2>/dev/null || echo "${YELLOW}   No hay .env.example, necesitas crear .env manualmente${NC}"
fi

# Parsear argumentos
MODE=${1:-up}

 case "$MODE" in
    up|start)
        echo ""
        echo -e "${BLUE}📦 Iniciando servicios...${NC}"
        $COMPOSE_CMD up -d
        
        echo ""
        echo -e "${GREEN}⏳ Esperando a que los servicios estén listos...${NC}"
        sleep 10
        
        # Verificar health
        echo ""
        echo -e "${BLUE}🔍 Verificando estado...${NC}"
        $COMPOSE_CMD ps
        
        echo ""
        echo -e "${GREEN}✅ Synapse Council iniciado!${NC}"
        echo ""
        echo "   📡 API Master: http://localhost:8000"
        echo "   🔧 Ollama Worker: http://localhost:11434"
        echo "   📊 Health Check: http://localhost:8000/health"
        echo ""
        echo -e "${YELLOW}📝 Comandos útiles:${NC}"
        echo "   Ver logs:  $COMPOSE_CMD logs -f"
        echo "   Detener:   $COMPOSE_CMD down"
        echo "   Escalar:   $COMPOSE_CMD up -d --scale worker=3"
        ;;
        
    down|stop)
        echo ""
        echo -e "${BLUE}🛑 Deteniendo servicios...${NC}"
        $COMPOSE_CMD down
        echo -e "${GREEN}✅ Servicios detenidos${NC}"
        ;;
        
    restart)
        echo ""
        echo -e "${BLUE}🔄 Reiniciando servicios...${NC}"
        $COMPOSE_CMD restart
        echo -e "${GREEN}✅ Servicios reiniciados${NC}"
        ;;
        
    logs)
        echo ""
        echo -e "${BLUE}📋 Mostrando logs...${NC}"
        $COMPOSE_CMD logs -f
        ;;
        
    build)
        echo ""
        echo -e "${BLUE}🔨 Reconstruyendo imágenes...${NC}"
        $COMPOSE_CMD build --no-cache
        echo -e "${GREEN}✅ Imágenes reconstruidas${NC}"
        ;;
        
    status)
        echo ""
        echo -e "${BLUE}📊 Estado de servicios:${NC}"
        $COMPOSE_CMD ps
        
        echo ""
        echo -e "${BLUE}📈 Uso de recursos:${NC}"
        docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}" 2>/dev/null || echo "   (Docker stats no disponible)"
        ;;
        
    worker-scale)
        NUM=${2:-2}
        echo ""
        echo -e "${BLUE}⚡ Escalando a $NUM workers...${NC}"
        $COMPOSE_CMD up -d --scale worker=$NUM
        echo -e "${GREEN}✅ Escalado a $NUM workers${NC}"
        ;;
        
    clean)
        echo ""
        echo -e "${YELLOW}🧹 Limpiando contenedores y volúmenes...${NC}"
        $COMPOSE_CMD down -v --remove-orphans
        docker system prune -f
        echo -e "${GREEN}✅ Limpieza completada${NC}"
        ;;
        
    *)
        echo "Uso: $0 [up|down|restart|logs|build|status|worker-scale|clean]"
        echo ""
        echo "Comandos:"
        echo "  up/start      - Iniciar todos los servicios"
        echo "  down/stop     - Detener servicios"
        echo "  restart       - Reiniciar servicios"
        echo "  logs          - Ver logs en tiempo real"
        echo "  build         - Reconstruir imágenes Docker"
        echo "  status        - Ver estado y recursos"
        echo "  worker-scale N- Escalar a N workers"
        echo "  clean         - Limpiar todo (¡cuidado!)")
        exit 1
        ;;
esac
