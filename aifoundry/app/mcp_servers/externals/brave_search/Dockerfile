FROM node:18-slim

# Directorio de trabajo
WORKDIR /app

# Instalar el servidor MCP de Brave Search globalmente
RUN npm install -g @brave/brave-search-mcp-server

# Exponer el puerto HTTP
EXPOSE 8080

# Comando de inicio en modo HTTP
# Las variables de entorno BRAVE_API_KEY, BRAVE_MCP_TRANSPORT, BRAVE_MCP_HOST y BRAVE_MCP_PORT
# se pasarán desde docker-compose.yml
ENTRYPOINT ["npx", "-y", "@brave/brave-search-mcp-server", "--transport", "http", "--port", "8080", "--host", "0.0.0.0"]
