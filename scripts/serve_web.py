#!/usr/bin/env python3
"""Strict local Pages-like server; unknown routes return 404, with no SPA fallback."""
import argparse
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1] / 'web/dist'
PREFIX = '/ClothLOOP-Dataset/'


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def do_GET(self):
        self.route(False)

    def do_HEAD(self):
        self.route(True)

    def route(self, head):
        path = urlsplit(self.path).path
        if path == PREFIX.rstrip('/'):
            self.send_response(301)
            self.send_header('Location', PREFIX)
            self.end_headers()
        elif path.startswith(PREFIX):
            self.path = '/' + self.path[len(PREFIX):]
            try:
                super().do_HEAD() if head else super().do_GET()
            except (BrokenPipeError, ConnectionResetError):
                pass  # Browsers routinely cancel lazy assets when navigating away.
        else:
            self.send_error(404)

    def log_message(self, fmt, *args):
        if len(args) > 1 and str(args[1]) not in ('200', '304'):
            super().log_message(fmt, *args)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=4173)
    args = parser.parse_args()
    print(f'Serving {ROOT} at http://127.0.0.1:{args.port}{PREFIX}', flush=True)
    ThreadingHTTPServer(('127.0.0.1', args.port), Handler).serve_forever()
