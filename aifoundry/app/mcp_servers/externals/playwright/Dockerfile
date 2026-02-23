FROM mcr.microsoft.com/playwright/python:v1.40.0-jammy

WORKDIR /app

# Instalar Node.js 20 (necesario para @playwright/mcp)
RUN apt-get update && apt-get install -y curl \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Instalar navegadores de Playwright para Node.js
RUN npx -y playwright install chromium

# Exponer el puerto
EXPOSE 8931

# Comando por defecto (será sobreescrito por docker-compose)
CMD ["tail", "-f", "/dev/null"]
