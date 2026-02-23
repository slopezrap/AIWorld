#!/bin/bash
# AIFoundry - Start Script
# Inicia todos los servicios Docker necesarios

set -e

echo "🚀 Iniciando servicios AIFoundry..."
echo ""

# Directorio del proyecto (donde está docker-compose.yml)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

# Construir y levantar servicios
echo "📦 Construyendo imágenes..."
docker-compose build --quiet

echo "🔄 Levantando contenedores..."
docker-compose up -d

# Esperar a que los servicios estén listos
echo "⏳ Esperando a que los servicios estén listos..."
sleep 5

# Verificar estado
echo ""
echo "✅ Servicios activos:"
docker-compose ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}"

echo ""
echo "📡 URLs disponibles:"
echo "   - Brave Search MCP: http://localhost:8082/mcp"
echo "   - Playwright MCP:   http://localhost:8931/mcp"
echo ""
echo "🎉 AIFoundry iniciado correctamente!"
