"""Smoke test of a built katip-kalkan.mcpb, started exactly as the manifest tells Claude Desktop to start it.

    python connector/tests/smoke_mcpb.py connector/dist/katip-kalkan.mcpb

Runs on Linux, macOS and Windows (CI). It unpacks the bundle, makes a client folder whose path and file
name use Turkish letters, and over stdio: lists files (the client's name must not show), masks the petition
(no gold value may appear), saves the reply with real names as .docx in the folder, refuses a path outside
the folder, and checks the guard hook with this OS's paths. Synthetic fixtures only.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
FIX = HERE / "fixtures"


def main(bundle: str) -> None:
    work = Path(tempfile.mkdtemp(prefix="katip-smoke-"))
    ext = work / "ext"
    zipfile.ZipFile(bundle).extractall(ext)
    m = json.loads((ext / "manifest.json").read_text(encoding="utf-8"))
    folder = work / "Davalar ÇĞİÖŞÜ çğıöşü"
    case = folder / "2026-1 Şükrü Çağlayan"
    case.mkdir(parents=True)
    downloads = work / "İndirilenler"
    downloads.mkdir()
    shutil.copy(FIX / "dilekce_01.docx", case / "Şükrü Çağlayan - Cevap Dilekçesi.docx")
    shutil.copy(FIX / "dilekce_01.txt", downloads / "UYAP evrak.txt")
    cfg = m["server"]["mcp_config"]
    over = cfg.get("platform_overrides", {}).get(sys.platform, {})
    sub = lambda s: (s.replace("${__dirname}", str(ext)).replace("${user_config.allowed_dir}", str(folder))
                     .replace("${user_config.downloads_dir}", str(downloads))
                     .replace("${user_config.profile}", "ai").replace("${user_config.language}", "tr"))
    args = [sub(a) for a in over.get("args", cfg["args"])]
    env = {**os.environ, **{k: sub(v) for k, v in cfg.get("env", {}).items()},
           "KATIP_HOME": str(work / ".katip"), "KATIP_AUTO_DEPS": "0", "PYTHONIOENCODING": "utf-8"}
    # the manifest says python3 (python on Windows); CI's interpreter has the pinned helpers installed
    proc = subprocess.Popen([sys.executable, *args], stdin=subprocess.PIPE, stdout=subprocess.PIPE, env=env,
                            cwd=work, text=True, encoding="utf-8")
    n = 0

    def rpc(method, params=None):
        nonlocal n
        n += 1
        proc.stdin.write(json.dumps({"jsonrpc": "2.0", "id": n, "method": method, "params": params or {}},
                                    ensure_ascii=False) + "\n")
        proc.stdin.flush()
        return json.loads(proc.stdout.readline())

    def call(name, **a):
        r = rpc("tools/call", {"name": name, "arguments": a})["result"]
        return r, json.dumps(r, ensure_ascii=False)

    rpc("initialize", {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "smoke"}})
    tools = {t["name"]: t for t in rpc("tools/list")["result"]["tools"]}
    assert len(tools) == 16, tools.keys()  # 11 Kalkan tools + 5 Katip DD tools
    manifest = {t["name"] for t in json.load(open(Path(__file__).parents[1] / "manifest.json"))["tools"]}
    assert manifest == set(tools), set(tools) ^ manifest
    info = tools["mask_file"]["inputSchema"]["properties"]["bilgi"]["default"]
    print("approval line:", info)
    dd, _ = call("dd_sources")
    assert not dd["isError"] and "masak" in dd["structuredContent"], dd
    status, _ = call("katip_status")
    print("status:", {k: status["structuredContent"][k] for k in ("engine", "vault", "ocr")})
    if sys.platform != "linux":
        assert "memory" not in status["structuredContent"]["vault"], "vault should be encrypted on disk"
    r, raw = call("list_files", bilgi="x")
    assert r["structuredContent"]["matches"] == 2, raw
    r, raw = call("list_files", bilgi="x", ara="caglayan CEVAP")
    assert r["structuredContent"]["matches"] == 1 and "Çağlayan" not in raw and "Şükrü" not in raw, raw
    fid = r["structuredContent"]["files"][0]["file_id"]
    print("found by name:", r["structuredContent"]["files"][0]["name"], "in", r["structuredContent"]["files"][0]["where"])
    r, raw = call("mask_file", bilgi="x", file_id=fid, matter="2026/1")
    assert not r["isError"], raw
    gold = json.loads((FIX / "dilekce_01.gold.json").read_text(encoding="utf-8"))
    leaked = [g["text"] for g in gold if g["text"] in raw]
    assert not leaked, leaked
    masked = r["structuredContent"]["masked_text"]
    print("masked, start:", masked[:160].replace("\n", " "))
    r, raw = call("restore_to_file", bilgi="x", text="Sayın [AD SOYAD-1], cevabımız ektedir.",
                  output_path="cevap-dilekçesi.docx", matter="2026/1")
    out = Path(r["structuredContent"]["output_path"])
    assert out.parent == case.resolve() and out.exists(), raw  # next to the source document
    body = zipfile.ZipFile(out).read("word/document.xml").decode("utf-8")
    assert "[AD SOYAD-1]" not in body and any(g["text"] in body for g in gold if g["entity_type"] == "PERSON")
    print("restored:", out.name)
    r, raw = call("restore_to_file", bilgi="x", text="x", output_path=str(work / "outside.docx"), matter="2026/1")
    assert r["isError"] and not (work / "outside.docx").exists(), raw
    r, raw = call("mask_file", bilgi="x", path=str(work / "ext" / "manifest.json"))
    assert r["isError"], raw
    r, raw = call("write_masked_copy", bilgi="x", file_id=fid, matter="2026/1")
    assert not r["isError"] and not [g["text"] for g in gold if g["text"] in raw], raw
    proc.stdin.close()
    proc.wait(timeout=30)
    # the Claude Code guard with this OS's paths
    guard = [sys.executable, str(HERE.parent / "hooks" / "guard.py")]
    genv = {**os.environ, "KATIP_FOLDER": str(folder), "KATIP_HOME": str(work / ".katip"),
            "KATIP_EXTRA_DIRS": str(downloads)}
    for tool, args_, want in [("Read", {"file_path": str(case / "a.docx")}, 2),
                              ("Read", {"file_path": str(downloads / "UYAP evrak.txt")}, 2),
                              ("Read", {"file_path": str(work / "notes.md")}, 0),
                              ("Bash", {"command": f'type "{folder}\\a.docx"'}, 2)]:
        code = subprocess.run(guard, input=json.dumps({"tool_name": tool, "tool_input": args_, "cwd": str(work)}),
                              text=True, capture_output=True, env=genv).returncode
        assert code == want, (tool, args_, code)
    print("smoke test passed on", sys.platform)


if __name__ == "__main__":
    main(sys.argv[1])
