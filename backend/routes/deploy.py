import logging

from flask import Blueprint, jsonify, request

from config import PROJECTS_DIR
from services.deploy_service import run_deploy, stop_deploy
from utils.validators import is_valid_name, is_valid_repo_url

logger = logging.getLogger(__name__)

deploy_bp = Blueprint("deploy", __name__)


@deploy_bp.route("/desplegar", methods=["POST"])
def deploy():
    """
    Clones (or pulls) a GitHub repo and deploys it via Docker Compose or Dockerfile.

    Body: { "nombre": str, "link": str, "puerto": int (optional) }
    """
    data = request.get_json(silent=True) or {}
    name = data.get("nombre", "").strip()
    link = data.get("link", "").strip()
    port = data.get("puerto")

    if not name or not link:
        return jsonify({"error": "Missing required fields: 'nombre' and 'link'"}), 400

    if not is_valid_name(name):
        return jsonify({"error": "Invalid name. Use only letters, numbers, hyphens or underscores (max 64 chars)."}), 400

    if not is_valid_repo_url(link):
        return jsonify({"error": "Invalid repository URL. Must start with https://, http://, or git@."}), 400

    try:
        payload = run_deploy(name, link, port)
        return jsonify(payload), 202
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except RuntimeError as exc:
        return jsonify({"error": "Docker build failed", "detail": str(exc)}), 500
    except Exception as exc:
        logger.exception("Unexpected error in /desplegar")
        return jsonify({"error": "Unexpected server error", "detail": str(exc)}), 500


@deploy_bp.route("/stop", methods=["POST"])
def stop():
    """
    Stops and removes the containers for a project.

    Body: { "nombre": str }
    """
    data = request.get_json(silent=True) or {}
    name = data.get("nombre", "").strip()

    if not name:
        return jsonify({"error": "Missing field: 'nombre'"}), 400

    if not is_valid_name(name):
        return jsonify({"error": "Invalid project name."}), 400

    try:
        stop_deploy(name)
        return jsonify({"message": f"Project '{name}' stopped successfully."}), 200
    except FileNotFoundError as exc:
        return jsonify({"error": str(exc)}), 404
    except Exception as exc:
        logger.exception("Unexpected error in /stop")
        return jsonify({"error": "Failed to stop project", "detail": str(exc)}), 500


@deploy_bp.route("/logs", methods=["GET"])
def logs():
    """
    Returns the last N lines from the build log of a project.

    Query params: nombre (str), lineas (int, default 100)
    """
    name = request.args.get("nombre", "").strip()
    lines = request.args.get("lineas", 100, type=int)

    if not name:
        return jsonify({"error": "Missing query param: 'nombre'"}), 400

    if not is_valid_name(name):
        return jsonify({"error": "Invalid project name."}), 400

    log_path = PROJECTS_DIR / name / "build.log"

    if not log_path.exists():
        return jsonify({"error": f"No build logs found for '{name}'."}), 404

    try:
        content = log_path.read_text(errors="replace").strip().splitlines()
        tail = content[-lines:]
        return jsonify({"name": name, "lines": len(tail), "log": "\n".join(tail)})
    except Exception as exc:
        logger.exception("Error reading logs for %s", name)
        return jsonify({"error": "Could not read log file", "detail": str(exc)}), 500
