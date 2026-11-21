"""Start Katip Klasör.

  katip-klasor                 the window (pywebview), watching the Katip folder
  katip-klasor --browser       the same screens in your browser, if pywebview isn't installed
  katip-klasor scan            mask what is waiting in 1 Gelen once, then exit (no window)
  katip-klasor release CASE    release every file of a case that has nothing left to check
  katip-klasor status          folder, model, counts per case
  katip-klasor eval [--export rapor.json]   test scores from the lawyer's marks (counts only)
"""
from __future__ import annotations

import argparse
import sys
import webbrowser


def _cli_scan() -> int:
    from .watcher import Watcher
    n = Watcher().scan_once(wait_stable=False)
    print(f"{n} dosya işlendi.")
    return 0


def _cli_status() -> int:
    from katip_kalkan import ner
    from . import layout, store
    s = store.load_settings()
    root = layout.ensure(store.folder(s))
    print(f"Katip klasörü: {root}")
    if w := layout.synced_warning(root):
        print(f"Uyarı: {w}")
    print(f"Model: {ner.describe()}")
    for case in [layout.GENERAL] + layout.cases(root):
        jobs = store.load_jobs(case)
        if jobs:
            by = {}
            for j in jobs.values():
                by[j["status"]] = by.get(j["status"], 0) + 1
            print(f"  {case}: " + ", ".join(f"{k} {v}" for k, v in sorted(by.items())))
    return 0


def _cli_release(case: str) -> int:
    from . import layout, pipeline, store
    s = store.load_settings()
    root = layout.ensure(store.folder(s))
    n = 0
    for key, j in store.load_jobs(case).items():
        if j["status"] == "ready":
            pipeline.release(root, case, key, s, who=store._user() + " (cli)")
            n += 1
    print(f"{n} dosya {layout.OUT}/{case} klasörüne kondu. İşaretli yeri olan dosyalar pencereden kontrol edilir.")
    return 0


def _utf8_console() -> None:
    """Windows consoles default to cp1252, which can't print Turkish letters (ş, ğ, ı)."""
    for stream in (sys.stdout, sys.stderr):
        if stream is not None and hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8", errors="replace")
            except (OSError, ValueError):
                pass


def _cli_eval(export: str | None) -> int:
    import json
    from . import evaluate, layout, store
    root = layout.ensure(store.folder(store.load_settings()))
    cases = [layout.GENERAL] + layout.cases(root)
    rep = evaluate.report(cases)
    texts = [j.get("text", "") for c in cases for j in store.load_jobs(c).values()]
    evaluate.check_no_values(rep, texts)
    t = rep["total"]
    print(f"{rep['files']} test dosyası · bulunan {t['found']} · yanlış {t['false']} · kaçan {t['missed']} · "
          f"duyarlılık %{t['recall']} · kesinlik %{t['precision']} · F2 {t['f2']}")
    for typ, m in rep["by_type"].items():
        print(f"  {typ}: bulunan {m['found']}, yanlış {m['false']}, kaçan {m['missed']}")
    if export:
        with open(export, "w", encoding="utf-8") as f:
            json.dump(rep, f, ensure_ascii=False, indent=1)
        print(f"Yazıldı: {export}. Göndermeden önce açıp okuyun; yalnızca sayılar içerir.")
    return 0


def main(argv: list[str] | None = None) -> int:
    _utf8_console()
    ap = argparse.ArgumentParser(prog="katip-klasor", description="Katip Klasör: belgeleri bu bilgisayarda maskeler.")
    ap.add_argument("cmd", nargs="?", choices=["scan", "status", "release", "eval"])
    ap.add_argument("case", nargs="?")
    ap.add_argument("--browser", action="store_true", help="pencere yerine tarayıcıda aç")
    ap.add_argument("--port", type=int, default=0)
    ap.add_argument("--export", help="eval: write the counts-only report here")
    a = ap.parse_args(argv)
    if a.cmd == "scan":
        return _cli_scan()
    if a.cmd == "status":
        return _cli_status()
    if a.cmd == "eval":
        return _cli_eval(a.export)
    if a.cmd == "release":
        if not a.case:
            ap.error("release needs a case name")
        return _cli_release(a.case)

    from .server import serve
    url, srv, w = serve(a.port)
    w.start()
    try:
        import webview  # pywebview
    except ImportError:
        webview = None
    if webview and not a.browser:
        webview.create_window("Katip Klasör", url, width=1280, height=820, min_size=(900, 600))
        webview.start()
    else:
        print(f"Katip Klasör: {url}  (kapatmak için Ctrl+C)")
        webbrowser.open(url)
        try:
            import threading
            threading.Event().wait()
        except KeyboardInterrupt:
            pass
    w.stop()
    srv.shutdown()
    return 0


if __name__ == "__main__":
    sys.exit(main())
