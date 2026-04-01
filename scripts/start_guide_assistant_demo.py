#!/usr/bin/env python3
"""Serve the standalone guide assistant demo page."""
from __future__ import annotations

import http.server
import os
import socketserver
import sys
import webbrowser

from _bootstrap import PROJECT_ROOT  # noqa: F401

PORT = 8080


class DemoRequestHandler(http.server.SimpleHTTPRequestHandler):
    """Static file server with permissive CORS for local demos."""

    def end_headers(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        super().end_headers()

    def do_OPTIONS(self) -> None:  # noqa: N802
        self.send_response(200)
        self.end_headers()


def open_demo_url(url: str) -> None:
    """Open the demo URL with a Windows fallback."""
    try:
        if webbrowser.open(url):
            return
    except Exception:
        pass

    if sys.platform.startswith("win"):
        try:
            os.startfile(url)  # type: ignore[attr-defined]
        except Exception:
            pass


def main() -> None:
    with socketserver.TCPServer(("", PORT), DemoRequestHandler) as httpd:
        demo_url = f"http://127.0.0.1:{PORT}/guide_assistant_demo.html"
        print("=" * 60)
        print("Guide Assistant demo server is running")
        print(f"Demo URL: {demo_url}")
        print("Backend API: http://127.0.0.1:8000")
        print("=" * 60)

        open_demo_url(demo_url)

        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nGuide Assistant demo server stopped")


if __name__ == "__main__":
    main()
