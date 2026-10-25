"""Static server for mockup/ that tells browsers not to cache.

`python -m http.server` lets browsers reuse old copies of JS modules after a rebuild, so a page can run
a mix of old and new files. This sends Cache-Control: no-store on every response.

Usage: python3 scripts/serve.py [port] [directory]     (defaults: 8765 mockup)
"""
import functools
import http.server
import sys

port = int(sys.argv[1]) if len(sys.argv) > 1 else 8765
directory = sys.argv[2] if len(sys.argv) > 2 else "mockup"


class NoCache(http.server.SimpleHTTPRequestHandler):
    extensions_map = {**http.server.SimpleHTTPRequestHandler.extensions_map, ".mjs": "text/javascript", ".js": "text/javascript"}

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()


handler = functools.partial(NoCache, directory=directory)
with http.server.ThreadingHTTPServer(("", port), handler) as httpd:
    print(f"serving {directory}/ on http://localhost:{port} (no-cache)")
    httpd.serve_forever()
