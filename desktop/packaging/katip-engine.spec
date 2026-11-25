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
# playwright: the DD features (ilan.gov.tr, Ticaret Sicili Gazetesi) drive the Mac's own Chrome through it; its
# Node driver comes along (about 120 MB unpacked). A browser is never bundled: Chrome, or Chromium on request.
for pkg in ("katip_mask", "rapidocr", "pymupdf", "onnxruntime", "playwright"):
    d, b, h = collect_all(pkg)
    datas += d; binaries += b; hidden += h
# Kalkan goes in with its compiled files (unchecked-hash .pyc, valid whatever the file dates): the frozen engine
# never writes bytecode, because a write inside Katip.app is "modifying apps" to macOS and breaks the signature.
import compileall, shutil
KALKAN = HERE / "build" / "kalkan-src" / "katip_kalkan"
shutil.rmtree(KALKAN, ignore_errors=True)
shutil.copytree(CONNECTOR / "katip_kalkan", KALKAN, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
import py_compile
compileall.compile_dir(str(KALKAN), quiet=1, invalidation_mode=py_compile.PycInvalidationMode.UNCHECKED_HASH)
datas += [(str(KALKAN), "connector/katip_kalkan")]
# Kalkan ships as files, so PyInstaller can't see what it imports: every standard-library module it names
# (urllib.robotparser for DD, sqlite3, ...) is found here and frozen in, so no feature fails on a missing module.
import ast, sys
for py in (CONNECTOR / "katip_kalkan").rglob("*.py"):
    for node in ast.walk(ast.parse(py.read_text(encoding="utf-8"))):
        names = [a.name for a in node.names] if isinstance(node, ast.Import) else \
            [node.module] if isinstance(node, ast.ImportFrom) and node.module and not node.level else []
        hidden += [n for n in names if n.split(".")[0] in sys.stdlib_module_names]
hidden += ["playwright.sync_api", "sqlite3"]
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
