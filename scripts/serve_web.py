#!/usr/bin/env python3
"""Strict local Pages-like server; unknown routes return 404, with no SPA fallback."""
import argparse
import re
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

    def send_head(self):
        # Pages supports byte ranges. SimpleHTTPRequestHandler alone does not,
        # which makes Chromium silently seek back to zero on otherwise valid MP4s.
        self.byte_range = None
        path = Path(self.translate_path(self.path))
        value = self.headers.get('Range')
        if not value or not path.is_file():
            return super().send_head()
        size = path.stat().st_size
        match = re.fullmatch(r'bytes=(\d*)-(\d*)', value)
        if not match or not any(match.groups()):
            self.send_error(400, 'Only one byte range is supported')
            return None
        first, last = match.groups()
        start = int(first) if first else max(0, size - int(last))
        end = min(int(last), size - 1) if first and last else size - 1
        if start > end or start >= size:
            self.send_response(416)
            self.send_header('Content-Range', f'bytes */{size}')
            self.send_header('Content-Length', '0')
            self.end_headers()
            return None
        f = path.open('rb')
        f.seek(start)
        self.byte_range = (start, end)
        self.send_response(206)
        self.send_header('Content-Type', self.guess_type(str(path)))
        self.send_header('Content-Length', str(end - start + 1))
        self.send_header('Accept-Ranges', 'bytes')
        self.send_header('Content-Range', f'bytes {start}-{end}/{size}')
        self.end_headers()
        return f

    def copyfile(self, source, outputfile):
        if self.byte_range is None:
            return super().copyfile(source, outputfile)
        remaining = self.byte_range[1] - self.byte_range[0] + 1
        while remaining:
            block = source.read(min(remaining, 64 * 1024))
            if not block:
                break
            outputfile.write(block)
            remaining -= len(block)

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
        if len(args) > 1 and str(args[1]) not in ('200', '206', '304'):
            super().log_message(fmt, *args)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=4173)
    args = parser.parse_args()
    print(f'Serving {ROOT} at http://127.0.0.1:{args.port}{PREFIX}', flush=True)
    ThreadingHTTPServer(('127.0.0.1', args.port), Handler).serve_forever()
