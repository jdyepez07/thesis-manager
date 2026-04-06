from config import VALID_NAME_RE


def is_valid_name(name: str) -> bool:
    """Returns True if the project name matches the allowed character set."""
    return bool(VALID_NAME_RE.match(name))


def is_valid_repo_url(url: str) -> bool:
    """
    Accepts HTTPS and SSH Git URLs.
    Does not guarantee the repo exists — just that the shape is correct.
    """
    return url.startswith(("https://", "http://", "git@"))
