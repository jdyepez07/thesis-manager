#!/bin/bash
# entrypoint: instala dependencias si es que quieres, luego arranca gunicorn/Flask
set -euo pipefail
# crear carpeta proyectos con permisos
mkdir -p /app/proyectos
chown -R nobody:nogroup /app/proyectos || true
exec gunicorn -w 4 -b 0.0.0.0:5000 app:app
