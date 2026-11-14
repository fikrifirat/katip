"""Serve the browser timing page for Katip Mask Nano / Mini / Base on http://127.0.0.1:8765/.

Uses the app's own stack from docs/ (vendor/transformers, vendor/ort, ner.js). Models are served read-only from
their local folders (not in git). Responses are no-store, so every page load is a cold load over the network
stack; COOP/COEP make the page cross-origin isolated so performance.measureUserAgentSpecificMemory() works.
POST /result appends one run to runs.jsonl next to this file (summarise.py turns it into results.json).
    python lab/mini/browser_bench/serve_bench.py [path-to-katip-mask-base-folder]
"""
import http.server, json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "../../.."))
BASE = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "ml/berturk/out")
MAP = {  # url prefix -> folder
    "/models/katip-mask-nano/": os.path.join(ROOT, "docs/models/katip-mask-nano"),
    "/models/katip-mask-mini/": os.path.join(ROOT, "lab/legal/bench/models/katip-mask-mini-v2"),
    "/models/katip-mask-base/": BASE,
    "/vendor/": os.path.join(ROOT, "docs/vendor"),
    "/samples/": os.path.join(ROOT, "docs/samples"),
    "/ner.js": os.path.join(ROOT, "docs/ner.js"),
    "/": HERE,
}

class H(http.server.SimpleHTTPRequestHandler):
    def translate_path(self, path):
        path = path.split("?")[0]
        for pre, folder in MAP.items():
            if path == pre.rstrip("/") or path.startswith(pre):
                rest = path[len(pre):] if pre.endswith("/") else ""
                full = os.path.realpath(os.path.join(folder, rest)) if rest else folder
                return full if full.startswith(os.path.realpath(folder)) else "/nonexistent"
        return "/nonexistent"
    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        self.send_header("Cross-Origin-Opener-Policy", "same-origin")
        self.send_header("Cross-Origin-Embedder-Policy", "require-corp")
        super().end_headers()
    def do_POST(self):
        body = self.rfile.read(int(self.headers["Content-Length"]))
        with open(os.path.join(HERE, "runs.jsonl"), "a", encoding="utf-8") as f:
            f.write(json.dumps(json.loads(body), ensure_ascii=False) + "\n")
        self.send_response(204); self.end_headers()
    def log_message(self, *a): pass

H.extensions_map[".mjs"] = "text/javascript"; H.extensions_map[".wasm"] = "application/wasm"
http.server.ThreadingHTTPServer(("127.0.0.1", 8765), H).serve_forever()
