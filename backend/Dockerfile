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

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app

ENV PROJECTS_BASE=/proyectos

RUN chmod +x entrypoint.sh

EXPOSE 5000
CMD ["./entrypoint.sh"]
