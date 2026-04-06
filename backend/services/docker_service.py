import logging
import subprocess
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Port detection
# ---------------------------------------------------------------------------

def detect_compose_internal_port(compose_path: Path) -> str | None:
    """
    Reads the first exposed port from any service in the compose file.

    Handles all three port notations Docker Compose accepts:
      - "8080:5000"           → returns "5000"
      - {target: 5000, ...}   → returns "5000"
      - 5000  (int, no host)  → returns "5000"
    """
    try:
        data = yaml.safe_load(compose_path.read_text())
    except yaml.YAMLError as exc:
        logger.error("Could not parse %s: %s", compose_path, exc)
        return None

    for service in data.get("services", {}).values():
        for port in service.get("ports", []):
            if isinstance(port, dict):
                target = port.get("target")
                if target:
                    return str(target)
            elif isinstance(port, str):
                # "host:internal" or just "port"
                return port.split(":")[-1]
            elif isinstance(port, int):
                return str(port)
    return None


def detect_dockerfile_exposed_port(dockerfile_path: Path) -> str:
    """
    Parses the first EXPOSE instruction in a Dockerfile.
    Falls back to "5000" when none is found (common Flask default).
    """
    try:
        for line in dockerfile_path.read_text().splitlines():
            stripped = line.strip()
            if stripped.upper().startswith("EXPOSE"):
                parts = stripped.split()
                if len(parts) >= 2:
                    # EXPOSE can be "8080/tcp" — strip the protocol suffix
                    return parts[1].split("/")[0]
    except OSError:
        pass
    return "5000"


# ---------------------------------------------------------------------------
# Compose helpers
# ---------------------------------------------------------------------------

def patch_compose_host_port(compose_path: Path, host_port: int, internal_port: str) -> None:
    """
    Rewrites the host-side port for the service that exposes `internal_port`.
    All other fields in the compose file are left untouched.
    """
    data = yaml.safe_load(compose_path.read_text())

    for service in data.get("services", {}).values():
        if "ports" not in service:
            continue

        patched = []
        for port in service["ports"]:
            if isinstance(port, dict):
                if str(port.get("target")) == internal_port:
                    port["published"] = host_port
                patched.append(port)
            elif isinstance(port, str):
                internal = port.split(":")[-1]
                patched.append(f"{host_port}:{internal}" if internal == internal_port else port)
            else:
                patched.append(port)

        service["ports"] = patched

    compose_path.write_text(yaml.safe_dump(data, sort_keys=False))


def strip_bind_mounts(compose_path: Path) -> None:
    """
    Removes host bind-mounts (paths starting with '.' or '/') from each service.
    Named volumes (e.g. "db_data:/var/lib/postgresql") are kept because they
    are useful for stateful services and don't reference host paths.
    """
    data = yaml.safe_load(compose_path.read_text())

    for service in data.get("services", {}).values():
        if "volumes" not in service:
            continue
        named_only = [
            v for v in service["volumes"]
            if isinstance(v, str) and not v.startswith((".", "/"))
        ]
        if named_only:
            service["volumes"] = named_only
        else:
            del service["volumes"]

    compose_path.write_text(yaml.safe_dump(data, sort_keys=False))


# ---------------------------------------------------------------------------
# Start
# ---------------------------------------------------------------------------

def start_compose(project_path: Path, log_path: Path) -> None:
    """Launches docker compose up in the background; output goes to build.log."""
    _run_background(["docker", "compose", "up", "--build", "-d"], project_path, log_path)


def build_and_start_container(
    project_path: Path,
    image_name: str,
    container_name: str,
    host_port: int,
    internal_port: str,
    log_path: Path,
) -> None:
    """
    Builds the Docker image synchronously so build errors surface immediately,
    then runs the container in the background.

    Raises RuntimeError with the last 2 000 chars of stderr if the build fails.
    """
    result = subprocess.run(
        ["docker", "build", "-t", image_name, "."],
        cwd=str(project_path),
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        log_path.write_text(result.stderr)
        raise RuntimeError(result.stderr[-2000:])

    _run_background(
        ["docker", "run", "-d", "-p", f"{host_port}:{internal_port}", "--name", container_name, image_name],
        project_path,
        log_path,
    )


# ---------------------------------------------------------------------------
# Stop
# ---------------------------------------------------------------------------

def stop_compose(project_path: Path) -> None:
    """Tears down all services defined in the project's compose file."""
    subprocess.run(
        ["docker", "compose", "down", "--remove-orphans"],
        cwd=str(project_path),
        capture_output=True,
        text=True,
    )


def stop_container(container_name: str) -> None:
    """Stops and removes a single named container."""
    subprocess.run(["docker", "stop", container_name], capture_output=True)
    subprocess.run(["docker", "rm", container_name], capture_output=True)


# ---------------------------------------------------------------------------
# Status
# ---------------------------------------------------------------------------

def get_compose_status(project_path: Path) -> list[dict]:
    """Returns docker compose ps output as a list of service dicts."""
    result = subprocess.run(
        ["docker", "compose", "ps", "--format", "json"],
        cwd=str(project_path),
        capture_output=True,
        text=True,
    )
    return _parse_json_lines(result.stdout)


def get_container_status(container_name: str) -> list[dict]:
    """Returns docker ps output filtered by container name as a list of dicts."""
    result = subprocess.run(
        ["docker", "ps", "--filter", f"name={container_name}", "--format", "json"],
        capture_output=True,
        text=True,
    )
    return _parse_json_lines(result.stdout)


def list_all_containers() -> list[dict]:
    """Returns all running Docker containers as a list of dicts."""
    result = subprocess.run(
        ["docker", "ps", "--format", "json"],
        capture_output=True,
        text=True,
    )
    return _parse_json_lines(result.stdout)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _run_background(cmd: list[str], cwd: Path, log_path: Path) -> None:
    """Spawns a subprocess whose stdout/stderr are written to log_path."""
    import subprocess as _sp
    with open(log_path, "w") as log_file:
        _sp.Popen(cmd, cwd=str(cwd), stdout=log_file, stderr=log_file)


def _parse_json_lines(output: str) -> list[dict]:
    """
    Docker --format json prints one JSON object per line, not a JSON array.
    This helper converts that into a proper Python list.
    """
    import json
    results = []
    for line in output.strip().splitlines():
        line = line.strip()
        if line:
            try:
                results.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return results
