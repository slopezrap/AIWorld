#!/bin/bash
# AIFoundry - Stop Script
# Detiene todos los servicios Docker

set -e

echo "🛑 Deteniendo servicios AIFoundry..."
echo ""

# Directorio del proyecto (donde está docker-compose.yml)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

# Detener servicios
echo "🔄 Deteniendo contenedores..."
docker-compose down

echo ""
echo "✅ Servicios detenidos correctamente!"
