# PyInstaller spec for the Katip engine: one folder with its own Python, so Katip.app (desktop/macos) can ship it
# and nobody needs a terminal or a Python install. Run from desktop/:
#   pyinstaller packaging/katip-engine.spec --noconfirm      -> dist/katip-engine/katip-engine
# Like Klasör, katip_kalkan ships as plain files (it reads engine.zip and its models next to its source); the
# bundled Nano model comes with it. Base/Mini are downloaded once on request through katip-mask (SHA-256 checked).
from pathlib import Path
from PyInstaller.utils.hooks import collect_all

HERE = Path(SPECPATH).parent
CONNECTOR = HERE.parent / "connector"

datas, binaries, hidden = [], [], []
for pkg in ("katip_mask", "rapidocr", "pymupdf", "onnxruntime"):
    d, b, h = collect_all(pkg)
    datas += d; binaries += b; hidden += h
datas += [(str(CONNECTOR / "katip_kalkan"), "connector/katip_kalkan")]
hidden += ["cryptography.hazmat.primitives.ciphers.aead", "pymupdf", "numpy", "onnxruntime", "rapidocr", "PIL.Image",
           "hmac", "secrets", "subprocess", "unicodedata", "zipfile", "xml.sax.saxutils", "http.server", "http.client",
           "urllib.request", "concurrent.futures", "dataclasses", "typing", "logging", "html", "html.parser", "email",
           "email.policy", "email.header", "email.message", "csv", "difflib", "bisect", "heapq", "plistlib", "argparse"]

a = Analysis([str(HERE / "katip_engine" / "__main__.py")], pathex=[str(HERE)],
             datas=datas, binaries=binaries, hiddenimports=hidden,
             excludes=["tkinter", "matplotlib", "pytest", "pandas", "webview", "katip_kalkan", "katip_klasor"],
             noarchive=False)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name="katip-engine", console=True)
coll = COLLECT(exe, a.binaries, a.datas, name="katip-engine")
