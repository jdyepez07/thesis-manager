import os
import re
from pathlib import Path

# Base directory where cloned projects live. Overridable via env so the
# Docker volume mount path doesn't have to match the development path.
PROJECTS_DIR = Path(os.getenv("PROJECTS_BASE", "/proyectos"))

# File written inside each project folder to track deployment state.
STATE_FILENAME = ".gestor_state.json"

# Limits what characters are allowed in a project name.
# Prevents path traversal attacks like nombre="../../etc".
VALID_NAME_RE = re.compile(r"^[a-zA-Z0-9_-]{1,64}$")
