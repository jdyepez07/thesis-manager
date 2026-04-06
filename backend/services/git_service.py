import logging
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)


def clone_or_pull(repo_url: str, project_path: Path) -> tuple[bool, str]:
    """
    Clones the repo if the project folder is new; runs git pull otherwise.

    Returns (is_new, human_readable_message).
    Raises subprocess.CalledProcessError if git fails (bad URL, no network, etc.).
    """
    if not (project_path / ".git").exists():
        logger.info("Cloning %s into %s", repo_url, project_path)
        subprocess.run(
            ["git", "clone", repo_url, str(project_path)],
            check=True,
            capture_output=True,
            text=True,
        )
        return True, "Repository cloned successfully"

    logger.info("Pulling latest changes for %s", project_path.name)
    subprocess.run(
        ["git", "pull"],
        cwd=str(project_path),
        check=True,
        capture_output=True,
        text=True,
    )
    return False, "Repository updated (git pull)"
