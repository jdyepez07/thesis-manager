import json
import logging
from pathlib import Path

from config import STATE_FILENAME

logger = logging.getLogger(__name__)


def read_state(project_path: Path) -> dict:
    """Returns the saved deployment state, or {} if the file doesn't exist yet."""
    state_file = project_path / STATE_FILENAME
    if not state_file.exists():
        return {}
    try:
        return json.loads(state_file.read_text())
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Could not read state file at %s: %s", state_file, exc)
        return {}


def write_state(project_path: Path, data: dict) -> None:
    """Persists deployment state to disk so it survives server restarts."""
    state_file = project_path / STATE_FILENAME
    state_file.write_text(json.dumps(data, indent=2))


def clear_state(project_path: Path) -> None:
    """Marks the project as inactive without deleting its folder."""
    write_state(project_path, {})
