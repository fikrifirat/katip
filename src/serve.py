"""Static file server for Katip Yerel on localhost. GET only: it has no upload
endpoint, logs no file names and refuses POST/PUT, so even the serving
machine never receives a document.  python serve.py [port]"""
import http.server, sys, functools, os

class H(http.server.SimpleHTTPRequestHandler):
    extensions_map = {**http.server.SimpleHTTPRequestHandler.extensions_map, ".mjs": "text/javascript", ".js": "text/javascript", ".wasm": "application/wasm"}
    def do_POST(self): self.send_error(405)
    do_PUT = do_DELETE = do_PATCH = do_POST
    def log_message(self, *a): pass
    def end_headers(self):
        self.send_header("Cache-Control", "no-store"); self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Cross-Origin-Opener-Policy", "same-origin"); super().end_headers()

port = int(sys.argv[1]) if len(sys.argv) > 1 else 8765
os.chdir(os.path.dirname(os.path.abspath(__file__)))
print(f"Katip Yerel: http://127.0.0.1:{port}/  (Ctrl+C to stop)")
http.server.ThreadingHTTPServer(("127.0.0.1", port), H).serve_forever()
