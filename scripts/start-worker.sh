#!/bin/bash
# Script de inicio para Worker Node

echo "🚀 Iniciando Synapse Worker Node..."

# Verificar NVIDIA GPU
if nvidia-smi > /dev/null 2>&1; then
    echo "✅ NVIDIA GPU detectada:"
    nvidia-smi --query-gpu=name,memory.total --format=csv,noheader
else
    echo "⚠️  No se detectó GPU NVIDIA. Ejecutando en modo CPU (más lento)."
fi

# Iniciar Ollama
echo "📦 Iniciando servidor Ollama..."
ollama serve &

# Esperar a que Ollama esté listo
echo "⏳ Esperando a que Ollama esté listo..."
for i in {1..30}; do
    if curl -s http://localhost:11434/api/tags > /dev/null; then
        echo "✅ Ollama listo!"
        echo "📋 Modelos disponibles:"
        ollama list || echo "   (Se descargarán bajo demanda)"
        break
    fi
    sleep 2
done

# Mantener contenedor activo
echo "🎯 Worker Node operativo. Esperando requests..."
tail -f /dev/null
