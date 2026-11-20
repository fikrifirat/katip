"""The Katip folder on disk: four numbered subfolders, one subfolder per case inside each."""
from __future__ import annotations

import hashlib
import re
import unicodedata
from pathlib import Path

from katip_kalkan import names

INBOX, OUT, ANSWERS, RESTORED = "1 Gelen", "2 Maskeli", "3 Yapay zekâ cevapları", "4 Geri yüklenmiş"
FOLDERS = (INBOX, OUT, ANSWERS, RESTORED)
GENERAL = "Genel"  # files dropped straight into 1 Gelen, not into a case folder

INPUT_EXT = {".txt", ".md", ".udf", ".docx", ".pdf", ".png", ".jpg", ".jpeg", ".tif", ".tiff", ".webp"}
ANSWER_EXT = {".txt", ".md", ".docx"}

README = """Katip Klasör

1 Gelen                  Belgeleri buraya bırakın, her dava için bir alt klasör açın.
2 Maskeli                Kontrolden geçen maskeli kopyalar. Yapay zekâya ya da e-postaya bunları verin.
3 Yapay zekâ cevapları   Yapay zekânın cevabını (.docx, .txt, .md) buraya, aynı dava klasörüne koyun.
4 Geri yüklenmiş         Gerçek adları geri konmuş cevap. Bu klasör bilgisayarınızda kalır.

Katip yalnızca tespit ettiğini maskeler. Paylaşmadan önce Kontrol ekranındaki işaretli yerlere bakın.
Asıl belgeler hiçbir zaman taşınmaz ya da değiştirilmez.
"""

SYNCED = ("Mobile Documents", "CloudDocs", "iCloud Drive", "OneDrive", "Dropbox", "Google Drive", "GoogleDrive",
          "Yandex.Disk", "pCloud", "Box Sync")


def nfc(s: str) -> str:
    return unicodedata.normalize("NFC", s)


def ensure(root: Path) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    for f in FOLDERS:
        (root / f).mkdir(exist_ok=True)
    readme = root / "OKU-BENİ.txt"
    if not readme.exists():
        readme.write_text(README, encoding="utf-8")
    return root


def synced_warning(root: Path) -> str | None:
    parts = {nfc(p) for p in root.resolve().parts}
    hit = next((s for s in SYNCED if any(s in p for p in parts)), None)
    if hit:
        return (f"Katip klasörü bir bulut klasörünün içinde ({hit}). Asıl belgeler orada zaten buluta "
                "yükleniyor; Katip klasörünü bilgisayarınızda yerel bir yere taşımanız önerilir.")
    return None


def case_of(root: Path, path: Path, top: str) -> str:
    """The case a file belongs to: its first folder under the given top folder, or Genel."""
    rel = path.relative_to(root / top)
    return nfc(rel.parts[0]) if len(rel.parts) > 1 else GENERAL


def case_dir(root: Path, top: str, case: str) -> Path:
    return root / top if case == GENERAL else root / top / case


def cases(root: Path) -> list[str]:
    out = set()
    for top in (INBOX, OUT, ANSWERS):
        d = root / top
        if d.is_dir():
            out |= {nfc(p.name) for p in d.iterdir() if p.is_dir() and not p.name.startswith(".")}
    return sorted(out, key=str.casefold)


def _skip(p: Path) -> bool:
    n = p.name
    return (n.startswith((".", "~$")) or n.endswith((".tmp", ".crdownload", ".part", ".download"))
            or ".maskeli" in n or ".geri" in n)


def files_in(root: Path, top: str, exts: set[str]) -> list[Path]:
    """Files in a top folder and its case folders (two levels deep; deeper folders belong to their case)."""
    base = root / top
    if not base.is_dir():
        return []
    out = []
    for p in sorted(base.rglob("*")):
        if p.is_file() and p.suffix.lower() in exts and not _skip(p) and len(p.relative_to(base).parts) <= 4:
            out.append(p)
    return out


def safe_name(p: Path) -> str:
    """The masked copy's name: the original stem if it has no personal data, else a short safe name
    plus a few characters of the original path's hash, so two "…" names don't collide."""
    stem = nfc(p.stem)
    safe = names.safe_title(stem)
    if safe == stem.replace("_", " ") or safe == stem:
        return stem
    tag = hashlib.sha256(nfc(str(p)).encode()).hexdigest()[:4]
    safe = re.sub(r"\s+", " ", safe.replace("…", "")).strip(" -_.")
    return f"{safe or 'belge'} {tag}"
