"""Local static server for the ProjectPilot AI frontend."""

from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


HOST = "127.0.0.1"
PORT = 5500
FRONTEND_DIR = Path(__file__).parent / "frontend"


class FrontendHandler(SimpleHTTPRequestHandler):
    """Serve files from the frontend directory."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(FRONTEND_DIR), **kwargs)


if __name__ == "__main__":
    server = ThreadingHTTPServer((HOST, PORT), FrontendHandler)
    print(f"ProjectPilot AI frontend running at http://{HOST}:{PORT}")
    print("Make sure the backend is running at http://127.0.0.1:8000")
    server.serve_forever()
