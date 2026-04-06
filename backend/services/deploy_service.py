import logging
from pathlib import Path

from config import PROJECTS_DIR
from services.git_service import clone_or_pull
from services.docker_service import (
    detect_compose_internal_port,
    detect_dockerfile_exposed_port,
    patch_compose_host_port,
    strip_bind_mounts,
    start_compose,
    build_and_start_container,
    stop_compose,
    stop_container,
)
from utils.network import get_free_port
from utils.state import read_state, write_state, clear_state

logger = logging.getLogger(__name__)


def run_deploy(name: str, repo_url: str, requested_port: int | None) -> dict:
    """
    Full deployment pipeline for a single project:
      1. Create the project folder.
      2. Clone the repo (or pull if it already exists).
      3. Tear down any previous deployment.
      4. Detect the deployment mode (compose vs dockerfile).
      5. Patch ports, strip bind-mounts, and launch the containers.
      6. Persist state to disk.

    Returns a dict that is serialised directly into the HTTP response.
    Raises ValueError for config problems, RuntimeError for Docker build failures.
    """
    project_path = PROJECTS_DIR / name
    project_path.mkdir(parents=True, exist_ok=True)

    is_new, git_message = clone_or_pull(repo_url, project_path)

    previous_state = read_state(project_path)
    if not is_new and previous_state:
        _stop_previous(project_path, previous_state)

    host_port = int(requested_port) if requested_port else get_free_port()
    log_path = project_path / "build.log"

    compose_file = project_path / "docker-compose.yml"
    dockerfile = project_path / "Dockerfile"

    if compose_file.exists():
        return _deploy_compose(name, repo_url, project_path, compose_file, host_port, log_path, git_message)

    if dockerfile.exists():
        return _deploy_dockerfile(name, repo_url, project_path, dockerfile, host_port, log_path, git_message)

    raise ValueError(
        "No docker-compose.yml or Dockerfile found at the repository root. "
        "The project must include at least one of these files."
    )


def stop_deploy(name: str) -> None:
    """
    Stops and removes all containers for a project, then clears its saved state.
    Raises FileNotFoundError if the project doesn't exist or has no active deployment.
    """
    project_path = PROJECTS_DIR / name
    state = read_state(project_path)

    if not project_path.exists() or not state:
        raise FileNotFoundError(f"Project '{name}' not found or has no active deployment.")

    _stop_previous(project_path, state)
    clear_state(project_path)


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _deploy_compose(
    name: str,
    repo_url: str,
    project_path: Path,
    compose_file: Path,
    host_port: int,
    log_path: Path,
    git_message: str,
) -> dict:
    internal_port = detect_compose_internal_port(compose_file)
    if internal_port is None:
        raise ValueError("The docker-compose.yml does not declare any exposed ports.")

    patch_compose_host_port(compose_file, host_port, internal_port)
    strip_bind_mounts(compose_file)
    start_compose(project_path, log_path)

    write_state(project_path, {
        "name": name,
        "link": repo_url,
        "mode": "compose",
        "host_port": host_port,
        "internal_port": internal_port,
    })

    logger.info("Compose deployment started: %s → port %d", name, host_port)
    return _response_payload(name, host_port, "docker-compose", git_message)


def _deploy_dockerfile(
    name: str,
    repo_url: str,
    project_path: Path,
    dockerfile: Path,
    host_port: int,
    log_path: Path,
    git_message: str,
) -> dict:
    internal_port = detect_dockerfile_exposed_port(dockerfile)
    image = f"{name}-image"
    container = f"{name}-container"

    # Build is synchronous so the caller gets a real error on failure.
    build_and_start_container(project_path, image, container, host_port, internal_port, log_path)

    write_state(project_path, {
        "name": name,
        "link": repo_url,
        "mode": "dockerfile",
        "image": image,
        "container": container,
        "host_port": host_port,
        "internal_port": internal_port,
    })

    logger.info("Dockerfile deployment started: %s → port %d", name, host_port)
    return _response_payload(name, host_port, "dockerfile", git_message)


def _stop_previous(project_path: Path, state: dict) -> None:
    """Stops whatever was running based on the persisted mode."""
    mode = state.get("mode")
    try:
        if mode == "compose":
            stop_compose(project_path)
        elif mode == "dockerfile":
            container = state.get("container")
            if container:
                stop_container(container)
    except Exception as exc:
        # Log but don't abort — the container may have already been removed.
        logger.warning("Could not stop previous deployment: %s", exc)


def _response_payload(name: str, host_port: int, mode: str, git_message: str) -> dict:
    return {
        "message": f"Deployment started for '{name}'",
        "url": f"http://localhost:{host_port}",
        "port": host_port,
        "mode": mode,
        "git": git_message,
        "logs": f"/logs?nombre={name}",
    }
