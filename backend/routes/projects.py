import json
import logging
import shutil

from flask import Blueprint, jsonify, request

from config import PROJECTS_DIR
from services.deploy_service import stop_deploy
from services.docker_service import (
    get_compose_status,
    get_container_status,
    list_all_containers,
)
from utils.state import read_state, clear_state
from utils.validators import is_valid_name

logger = logging.getLogger(__name__)

projects_bp = Blueprint("projects", __name__)


@projects_bp.route("/list", methods=["GET"])
def list_projects():
    """
    Lists all projects managed by the gestor (those with a state file).
    Returns each project's name, mode, assigned port, url, and source link.

    The frontend uses this endpoint to populate the deployments table.
    The response shape matches what /status returns per project so the
    dashboard can render both consistently.
    """
    try:
        projects = []
        if PROJECTS_DIR.exists():
            for folder in sorted(PROJECTS_DIR.iterdir()):
                if not folder.is_dir():
                    continue
                state = read_state(folder)
                if not state:
                    continue

                host_port = state.get("host_port")
                containers = _get_containers_for(folder, state)

                projects.append({
                    "nombre": folder.name,
                    "mode": state.get("mode"),
                    "puerto": host_port,
                    "url": f"http://localhost:{host_port}" if host_port else None,
                    "link": state.get("link"),
                    "containers": containers,
                })

        return jsonify({"proyectos": projects, "total": len(projects)})
    except Exception as exc:
        logger.exception("Error in /list")
        return jsonify({"error": "Failed to list projects", "detail": str(exc)}), 500


@projects_bp.route("/status", methods=["GET"])
def status():
    """
    Returns live Docker status for a single project.

    Query param: nombre (str)
    """
    name = request.args.get("nombre", "").strip()

    if not name:
        return jsonify({"error": "Missing query param: 'nombre'"}), 400

    if not is_valid_name(name):
        return jsonify({"error": "Invalid project name."}), 400

    project_path = PROJECTS_DIR / name

    if not project_path.exists():
        return jsonify({"error": f"Project '{name}' does not exist."}), 404

    state = read_state(project_path)
    host_port = state.get("host_port")

    try:
        containers = _get_containers_for(project_path, state)
        return jsonify({
            "nombre": name,
            "mode": state.get("mode"),
            "puerto": host_port,
            "url": f"http://localhost:{host_port}" if host_port else None,
            "containers": containers,
        })
    except Exception as exc:
        logger.exception("Error in /status for %s", name)
        return jsonify({"error": "Failed to retrieve status", "detail": str(exc)}), 500


@projects_bp.route("/eliminar", methods=["DELETE"])
def delete_project():
    """
    Stops the project and permanently removes its local folder.

    Body: { "nombre": str }
    """
    data = request.get_json(silent=True) or {}
    name = data.get("nombre", "").strip()

    if not name:
        return jsonify({"error": "Missing field: 'nombre'"}), 400

    if not is_valid_name(name):
        return jsonify({"error": "Invalid project name."}), 400

    project_path = PROJECTS_DIR / name

    if not project_path.exists():
        return jsonify({"error": f"Project '{name}' does not exist."}), 404

    try:
        # stop_deploy handles the case where there's no active state gracefully
        try:
            stop_deploy(name)
        except FileNotFoundError:
            pass

        shutil.rmtree(project_path)
        logger.info("Project '%s' deleted from disk", name)
        return jsonify({"message": f"Project '{name}' deleted successfully."})
    except Exception as exc:
        logger.exception("Error in /eliminar for %s", name)
        return jsonify({"error": "Failed to delete project", "detail": str(exc)}), 500


@projects_bp.route("/health", methods=["GET"])
def health():
    """Used by Docker healthcheck and monitoring tools to verify the service is up."""
    return jsonify({"status": "ok", "projects_dir": str(PROJECTS_DIR)}), 200


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _get_containers_for(project_path, state: dict) -> list[dict]:
    """
    Fetches live Docker container info depending on the deployment mode.
    Returns an empty list if the project has no active state.
    """
    mode = state.get("mode")
    if mode == "compose":
        return get_compose_status(project_path)
    if mode == "dockerfile":
        container = state.get("container")
        return get_container_status(container) if container else []
    return []
