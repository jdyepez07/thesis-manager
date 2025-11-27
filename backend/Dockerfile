FROM python:3.11-slim

# Instalar git, curl, docker-cli y dependencias
RUN apt-get update && apt-get install -y \
    git \
    curl \
    ca-certificates \
    lsb-release \
    gnupg \
    && curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /usr/share/keyrings/docker.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker.gpg] https://download.docker.com/linux/debian $(lsb_release -cs) stable" \
       > /etc/apt/sources.list.d/docker.list \
    && apt-get update && apt-get install -y docker-ce-cli \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copiar requirements e instalarlos
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar entrypoint primero y darle permisos
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Copiar el resto del código
COPY . /app

ENV PROJECTS_BASE=/proyectos

EXPOSE 5000
CMD ["bash", "/app/entrypoint.sh"]
