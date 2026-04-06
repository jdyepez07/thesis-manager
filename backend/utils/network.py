import socket


def get_free_port() -> int:
    """
    Asks the OS for a free TCP port and returns it.

    SO_REUSEADDR is set so Docker can bind the same port immediately
    after this socket is closed, reducing the race-condition window.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(("", 0))
        return s.getsockname()[1]
