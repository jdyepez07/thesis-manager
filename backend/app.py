import os
import subprocess
from flask import Flask, request, jsonify
import yaml
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Permite configurar la base de proyectos por variable de entorno
PROYECTOS_DIR = os.getenv("PROJECTS_BASE", "/proyectos")


def reemplazar_puerto_docker_compose(compose_path, puerto_publico):
    """Reemplaza el puerto externo en docker-compose.yml"""
    with open(compose_path, "r") as f:
        compose_data = yaml.safe_load(f)

    services = compose_data.get("services", {})
    for service_name, service in services.items():
        if "ports" in service:
            new_ports = []
            for port in service["ports"]:
                # Port puede venir como "host:container" o como un dict en versiones modernas
                if isinstance(port, str):
                    if ":" in port:
                        internal = port.split(":")[1]
                        new_ports.append(f"{puerto_publico}:{internal}")
                    else:
                        new_ports.append(port)
                elif isinstance(port, dict):
                    # Formato {'target': 5006, 'published': 3005, 'protocol': 'tcp', 'mode': 'host'}
                    target = port.get("target")
                    if target is not None:
                        port["published"] = int(puerto_publico)
                    new_ports.append(port)
            service["ports"] = new_ports

    with open(compose_path, "w") as f:
        yaml.safe_dump(compose_data, f, sort_keys=False)


def limpiar_volumenes(compose_path):
    """Elimina la sección de volúmenes para evitar sobrescribir /app"""
    with open(compose_path, "r") as f:
        compose_data = yaml.safe_load(f)

    services = compose_data.get("services", {})
    for service in services.values():
        if "volumes" in service:
            del service["volumes"]

    with open(compose_path, "w") as f:
        yaml.safe_dump(compose_data, f, sort_keys=False)


def ejecutar_async(cmd, cwd=None):
    """Ejecuta un comando en segundo plano para no bloquear Flask"""
    subprocess.Popen(
        cmd,
        cwd=cwd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )


@app.route("/desplegar", methods=["POST"])
def desplegar():
    data = request.get_json(silent=True) or {}
    nombre = data.get("nombre")
    link = data.get("link")
    puerto = data.get("puerto")

    if not nombre or not link or not puerto:
        return jsonify({"error": "Faltan parámetros: nombre, link y puerto"}), 400

    puerto = str(puerto)
    proyecto_path = os.path.join(PROYECTOS_DIR, nombre)
    compose_file = os.path.join(proyecto_path, "docker-compose.yml")
    dockerfile_path = os.path.join(proyecto_path, "Dockerfile")

    try:
        # Crear carpeta del proyecto si no existe
        os.makedirs(proyecto_path, exist_ok=True)

        # Clonar repo si no existe
        if not os.path.exists(os.path.join(proyecto_path, ".git")):
            subprocess.run(["git", "clone", link, proyecto_path], check=True)

        # Si hay docker-compose.yml, ajustar y levantar con compose
        if os.path.exists(compose_file):
            reemplazar_puerto_docker_compose(compose_file, puerto)
            limpiar_volumenes(compose_file)

            # Levantar en segundo plano para evitar bloquear la respuesta HTTP
            ejecutar_async(
                ["docker", "compose", "up", "--build", "-d"],
                cwd=proyecto_path
            )

            return jsonify({
                "message": f"Despliegue iniciado para {nombre} en localhost:{puerto}",
                "details": "Usando docker-compose.yml, proceso en segundo plano"
            }), 202

        # Si no hay docker-compose.yml, usar Dockerfile (asume puerto interno 5006)
        if os.path.exists(dockerfile_path):
            imagen = f"{nombre}-image"
            contenedor = f"{nombre}-container"
            puerto_interno = "5006"

            # Construcción síncrona (rápida normalmente); si lo prefieres, también puede ser async
            subprocess.run(["docker", "build", "-t", imagen, "."], check=True, cwd=proyecto_path)

            # Lanzar contenedor en segundo plano
            ejecutar_async(
                ["docker", "run", "-d", "-p", f"{puerto}:{puerto_interno}", "--name", contenedor, imagen],
                cwd=proyecto_path
            )

            return jsonify({
                "message": f"Despliegue iniciado para {nombre} en localhost:{puerto}",
                "details": "Usando Dockerfile, proceso en segundo plano"
            }), 202

        # Si no hay ni compose ni Dockerfile, no sabemos cómo levantar
        return jsonify({
            "error": "No se encontró docker-compose.yml ni Dockerfile en el proyecto clonado",
            "details": "Agrega uno de los dos para poder desplegar automáticamente"
        }), 400

    except subprocess.CalledProcessError as e:
        return jsonify({
            "error": "Fallo ejecutando comando del sistema",
            "details": e.stderr.decode() if e.stderr else str(e)
        }), 500
    except Exception as e:
        return jsonify({
            "error": "Error inesperado",
            "details": str(e)
        }), 500


@app.route("/status", methods=["GET"])
def status():
    nombre = request.args.get("nombre")
    if not nombre:
        return jsonify({"error": "Falta parámetro 'nombre'"}), 400

    proyecto_path = os.path.join(PROYECTOS_DIR, nombre)
    compose_file = os.path.join(proyecto_path, "docker-compose.yml")

    try:
        if os.path.exists(compose_file):
            result = subprocess.run(
                ["docker", "compose", "ps", "--format", "json"],
                cwd=proyecto_path,
                capture_output=True,
                text=True
            )
            # docker compose ps --format json devuelve lista de servicios
            return jsonify({"services": yaml.safe_load(result.stdout)})
        else:
            ps = subprocess.run(
                ["docker", "ps", "--filter", f"name={nombre}", "--format", "json"],
                capture_output=True, text=True
            )
            return jsonify({"containers": yaml.safe_load(ps.stdout)})
    except Exception as e:
        return jsonify({"error": "Error consultando estado", "details": str(e)}), 500

@app.route("/list", methods=["GET"])
def list_containers():
    try:
        result = subprocess.run(
            ["docker", "ps", "--format", "json"],
            capture_output=True,
            text=True
        )
        # docker ps --format json devuelve una lista JSON por línea
        lines = result.stdout.strip().splitlines()
        containers = [yaml.safe_load(line) for line in lines if line.strip()]
        return jsonify({"containers": containers})
    except Exception as e:
        return jsonify({"error": "Error listando contenedores", "details": str(e)}), 500

@app.route("/stop", methods=["POST"])
def stop_container():
    data = request.get_json(silent=True) or {}
    nombre = data.get("nombre")
    if not nombre:
        return jsonify({"error": "Falta parámetro 'nombre'"}), 400
    try:
        subprocess.run(["docker", "stop", nombre], check=True)
        subprocess.run(["docker", "rm", nombre], check=True)
        return jsonify({"message": f"Contenedor {nombre} detenido y eliminado"}), 200
    except subprocess.CalledProcessError as e:
        return jsonify({"error": "Fallo al detener contenedor", "details": str(e)}), 500


if __name__ == "__main__":
    # Ejecuta el backend
    app.run(host="0.0.0.0", port=5000)
