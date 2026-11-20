# PyInstaller spec for Katip Klasör (Mac .app, Windows folder). Run from desktop/:
#   pyinstaller packaging/katip-klasor.spec --noconfirm
# Models are not bundled: Base/Mini are downloaded once at first start through katip-mask (SHA-256 checked);
# the bundled Nano and the OCR models come with katip_kalkan.
import sys
from pathlib import Path
from PyInstaller.utils.hooks import collect_all

HERE = Path(SPECPATH).parent
CONNECTOR = HERE.parent / "connector"

datas, binaries, hidden = [], [], []
for pkg in ("katip_mask", "rapidocr", "pymupdf", "webview", "onnxruntime", "clr_loader", "pythonnet"):  # pythonnet: pywebview on Windows
    try:
        d, b, h = collect_all(pkg)
    except Exception:
        continue
    datas += d; binaries += b; hidden += h
datas += [(str(HERE / "katip_klasor" / "ui"), "katip_klasor/ui"),
          (str(CONNECTOR / "katip_kalkan"), "connector/katip_kalkan")]

# katip_kalkan ships as plain files (connector/katip_kalkan, found by katip_klasor/__init__.py), because it reads
# engine.zip and its models next to its own source. Its imports are listed here so they are bundled.
hidden += ["cryptography.hazmat.primitives.ciphers.aead", "pymupdf", "numpy", "onnxruntime", "rapidocr", "PIL.Image",
           "hmac", "secrets", "subprocess", "unicodedata", "zipfile", "xml.sax.saxutils", "http.server", "urllib.request",
           "concurrent.futures", "dataclasses", "typing", "logging", "html", "csv", "difflib", "bisect", "heapq"]
a = Analysis([str(HERE / "katip_klasor" / "__main__.py")], pathex=[str(HERE)],
             datas=datas, binaries=binaries, hiddenimports=hidden,
             excludes=["tkinter", "matplotlib", "pytest", "pandas", "katip_kalkan"], noarchive=False)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name="Katip Klasor", console=False,
          icon=str(HERE / "packaging" / ("katip.icns" if sys.platform == "darwin" else "katip.ico")))
coll = COLLECT(exe, a.binaries, a.datas, name="Katip Klasor")
if sys.platform == "darwin":
    app = BUNDLE(coll, name="Katip Klasör.app", icon=str(HERE / "packaging" / "katip.icns"),
                 bundle_identifier="com.fikrifirat.katip.klasor",
                 info_plist={"CFBundleShortVersionString": "0.1.0", "NSHighResolutionCapable": True,
                             "LSApplicationCategoryType": "public.app-category.productivity"})
