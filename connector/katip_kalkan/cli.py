"""Command line for the same features, plus `share` for the ChatGPT path.

    katip-kalkan serve                         # local MCP server (stdio) for Claude
    katip-kalkan mask dilekce.docx --matter 2026/123
    katip-kalkan share dilekce.docx --relay https://relay.katip.example
    katip-kalkan restore answer.txt out.txt --matter 2026/123
    katip-kalkan relay --port 8787             # run the relay (server side)
    katip-kalkan feedback [--export grades.json]   # the lawyer's precedent grades (emsal_ara / geri_bildirim)
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request
from pathlib import Path

from . import core, vault


def share(path: str, relay_url: str, matter: str = "default", token: str | None = None) -> str:
    """Mask locally, encrypt locally, upload ciphertext. Returns the share code."""
    doc = core.mask_file(path, matter)
    if doc["pages"] > 1:  # the relay gets the whole masked text in one drop
        parts = [doc["masked_text"]] + [core.mask_file(path, matter, p)["masked_text"] for p in range(2, doc["pages"] + 1)]
        doc["masked_text"] = "".join(parts)
    payload = {k: doc[k] for k in ("file_name", "kind", "masked_text", "entity_counts", "placeholders")}
    key, nonce, ct = vault.seal_for_relay(json.dumps(payload, ensure_ascii=False))
    req = urllib.request.Request(relay_url.rstrip("/") + "/v1/drops", method="POST",
                                 data=json.dumps({"nonce": vault.b64u(nonce), "ciphertext": vault.b64u(ct)}).encode(),
                                 headers={"Content-Type": "application/json",
                                          **({"Authorization": f"Bearer {token}"} if token else {})})
    with urllib.request.urlopen(req, timeout=30) as r:
        drop = json.loads(r.read())
    return f"katip-{drop['id']}.{vault.b64u(key)}"


def install_model(folder: str, name: str | None = None, trust: float | None = None) -> str:
    import shutil
    src = Path(folder).expanduser()
    onnx = src / "onnx" / "model_quantized.onnx"
    if not onnx.exists():
        onnx = src / "onnx" / "model.onnx"
    if not (src / "config.json").exists() or not (src / "tokenizer.json").exists() or not onnx.exists():
        raise SystemExit("expected config.json, tokenizer.json and onnx/model_quantized.onnx (or model.onnx)")
    dst = vault.katip_home() / "models" / (name or src.name)
    (dst / "onnx").mkdir(parents=True, exist_ok=True)
    for f in ("config.json", "tokenizer.json", "tokenizer_config.json"):
        if (src / f).exists():
            shutil.copyfile(src / f, dst / f)
    shutil.copyfile(onnx, dst / "onnx" / onnx.name)
    if trust is not None:
        (dst / "katip.json").write_text(json.dumps({"trust": trust}))
    return str(dst)


def _dd(a):
    """Your own terminal: full records, nothing redacted."""
    from .dd import service
    if a.dd_cmd == "search":
        out = service.screen(a.name, birth_year=a.birth, id_number=a.id, redact=False, verbatim=a.json)
        if a.json:
            print(json.dumps(out, ensure_ascii=False, indent=1))
            return
        for h in out["hits"]:
            print(f"{h['score']:.2f} {h['band']:6} {h['source']:7} {h['listed_name'][:50]:50} {h['date']:10} {h['source_url']}")
            for n in h["notes"]:
                print(f"{'':16}{n}")
        for s, v in out["sources_status"].items():
            print(f"{s}: {v['records']} records, data as of {v['data_as_of'] or 'never'}")
        print(out["how_to_read"])
        return
    if a.dd_cmd == "update":
        out = service.update("masak")
    elif a.dd_cmd == "status":
        out = service.sources_status()
    elif a.dd_cmd == "add-gazette":
        out = service.add_gazette(a.paths, use_ocr=a.ocr)
    elif a.dd_cmd == "gazette-lookup":
        out = service.gazette_lookup(a.target, a.office, a.max_pages, a.court)
    else:
        out = service.ilan_lookup(a.target, a.max_ads, headed=a.headed)
    print(json.dumps(out, ensure_ascii=False, indent=1))


def main(argv=None):
    ap = argparse.ArgumentParser(prog="katip-kalkan")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("serve", help="local MCP server over stdio")
    r = sub.add_parser("relay", help="run the relay")
    r.add_argument("--host", default="127.0.0.1")
    r.add_argument("--port", type=int, default=8787)
    for name in ("mask", "share", "copy"):
        p = sub.add_parser(name)
        p.add_argument("file")
        p.add_argument("--matter", default="default")
        if name == "share":
            p.add_argument("--relay", default=os.environ.get("KATIP_RELAY_URL", "http://127.0.0.1:8787"))
    p = sub.add_parser("restore")
    p.add_argument("text_file", help="file with the AI's answer (placeholders)")
    p.add_argument("output")
    p.add_argument("--matter", default="default")
    p = sub.add_parser("install-model", help="copy a Katip Mask model folder into ~/.katip/models")
    p.add_argument("folder")
    p.add_argument("--name")
    p.add_argument("--trust", type=float, help="0.5 for Base v2 and Nano v1.1 (as in registry.json)")
    p = sub.add_parser("forget")
    p.add_argument("--matter", default="default")
    p = sub.add_parser("feedback", help="summary of precedent grades; --export writes them to one file to send")
    p.add_argument("--export")
    p = sub.add_parser("scan", help="name the type of every document in a folder, on this computer")
    p.add_argument("folder")
    p.add_argument("--json", action="store_true")
    p.add_argument("--steps", action="store_true", help="also show related statutes and suggested next steps")
    d = sub.add_parser("dd", help="due-diligence screening: MASAK lists, ilan.gov.tr, Ticaret Sicili Gazetesi")
    dsub = d.add_subparsers(dest="dd_cmd", required=True)
    dsub.add_parser("update", help="fetch the four MASAK asset-freeze lists (about 10 requests, 2 s apart)")
    dsub.add_parser("status", help="records and data date of each source")
    q = dsub.add_parser("search", help="screen a person or company name")
    q.add_argument("name")
    q.add_argument("--birth", default="")
    q.add_argument("--id", default="")
    q.add_argument("--json", action="store_true")
    g = dsub.add_parser("add-gazette", help="add Ticaret Sicili Gazetesi PDFs (files or a folder)")
    g.add_argument("paths", nargs="+")
    g.add_argument("--ocr", action="store_true")
    il = dsub.add_parser("ilan-lookup", help="look up ONE named target on ilan.gov.tr in a real browser")
    il.add_argument("target")
    il.add_argument("--max-ads", type=int, default=20)
    il.add_argument("--headed", action="store_true")
    gl = dsub.add_parser("gazette-lookup", help="look up ONE company in the Ticaret Sicili Gazetesi with your own login")
    gl.add_argument("target")
    gl.add_argument("--office", required=True, help="ticaret sicili müdürlüğü, e.g. BURSA")
    gl.add_argument("--max-pages", type=int, default=3)
    gl.add_argument("--court", action="store_true", help="court and bankruptcy-office notices (konkordato, iflas)")
    a = ap.parse_args(argv)

    if a.cmd == "dd":
        return _dd(a)
    if a.cmd == "serve":
        from .local_server import main as serve
        return serve()
    if a.cmd == "relay":
        sys.argv = [sys.argv[0], "--host", a.host, "--port", str(a.port)]
        from .relay import main as relay
        return relay()
    if a.cmd == "mask":
        doc = core.mask_file(a.file, a.matter)
        print(doc["masked_text"])
        print(json.dumps(doc["entity_counts"], ensure_ascii=False), file=sys.stderr)
    elif a.cmd == "copy":
        print(core.write_redacted(a.file, a.matter)["output_path"])
    elif a.cmd == "share":
        code = share(a.file, a.relay, a.matter, os.environ.get("KATIP_RELAY_UPLOAD_TOKEN"))
        print(code)
        print("Paste this code into ChatGPT. It works once and expires in 15 minutes.", file=sys.stderr)
    elif a.cmd == "restore":
        text = Path(a.text_file).read_text(encoding="utf-8")
        print(json.dumps(core.restore_to_file(text, a.output, a.matter)))
    elif a.cmd == "install-model":
        print(install_model(a.folder, a.name, a.trust))
    elif a.cmd == "scan":
        from . import doctype
        rows = doctype.scan(a.folder)
        if a.json:
            print(json.dumps(rows, ensure_ascii=False, indent=1))
        for r in [] if a.json else rows:
            if "error" in r:
                print(f"{'?':5}  {'(unreadable: ' + r['error'] + ')':58}  {r['path']}")
                continue
            n = r.get("name") or {}
            label = f"{n.get('local', r['type'])} · {n.get('en', '')}"
            print(f"{r['confidence']:5.2f}  {label[:58]:58}  {r['path']}")
            if a.steps and not r["abstained"]:
                plan = doctype.next_steps({"type": r["type"], "lang": r["lang"]})
                refs = ", ".join(m["ref"] for m in plan["mevzuat"])
                if refs:
                    print(f"{'':7}Mevzuat: {refs}")
                for s in plan["steps"]:
                    print(f"{'':7}{'→' if s['run'] == 'auto' else '?'} {s['tool']}: {s['why'].get('en', '')}")
    elif a.cmd == "forget":
        print(json.dumps(core.forget_matter(a.matter)))
    elif a.cmd == "feedback":
        from . import emsal
        print(json.dumps(emsal.feedback(a.export), ensure_ascii=False, indent=1))


if __name__ == "__main__":
    sys.exit(main())
