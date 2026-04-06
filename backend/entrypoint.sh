#!/bin/bash
set -euo pipefail

mkdir -p /proyectos
chown -R nobody:nogroup /proyectos 2>/dev/null || true

exec gunicorn -w 4 -b 0.0.0.0:5000 app:app
