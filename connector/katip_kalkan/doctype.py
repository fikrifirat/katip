"""Katip Algıla: name a document's type on the device, then suggest the next steps for it.

    from katip_kalkan import doctype
    r = doctype.classify(text)            # {"type": "odeme_emri", "confidence": 0.97, "top": [...], ...}
    plan = doctype.next_steps(r, text)    # related statutes (Mevzuat), precedent queries (Emsal), workflow

Design rules
- Standard library only, like the rest of Kalkan. No document text is logged or sent anywhere.
- The model is a linear classifier over hashed word and character n-grams (one 2^14 x C int8 matrix,
  ~400 KB). Linear on purpose: it is fast (tens of ms per document in pure Python), easy to port to
  JS/Swift byte for byte (FNV-1a hashing, spec in lab/doctype/README.md), and one plaintext-matrix x
  encrypted-vector product under FHE (encrypted-compute experiment 3), with argmax done by the client.
- Language packs: `doctype_packs/<lang>.pack.json` holds the labels, their names (always with an
  English line) and the follow-up actions; `<lang>.model.json` + `.bin` hold the trained weights.
  A pack without weights loads fine (labels and actions only) and `classify` says so.
- Privacy split (plan H10): steps that run on the device ("where": "device") may run automatically.
  Steps that leave the device ("where": "network", e.g. a live precedent search) are returned as
  suggestions with the exact query shown; this module never runs them.
"""
from __future__ import annotations

import json
import math
import os
import re
import unicodedata
from array import array
from pathlib import Path

PACKS = Path(__file__).resolve().parent / "doctype_packs"
HEAD, TAIL = 3000, 1000          # characters read: the first ~2 pages and the signature / hüküm block
_FOLD = str.maketrans("çğıöşüâîûÇĞIÖŞÜÂÎÛ", "cgiosuaiuCGIOSUAIU")
_WORD = re.compile(r"[a-z0-9]+")
_DIGITS = re.compile(r"[0-9]+")


# ------------------------------------------------------------------ features (the spec every port follows)
def fnv1a(s: str) -> int:
    h = 0x811C9DC5
    for b in s.encode("utf-8"):
        h = ((h ^ b) * 0x01000193) & 0xFFFFFFFF
    return h


def normalise(text: str) -> str:
    """Turkish lower-case, then fold to ASCII: OCR output and ASCII-typed text look the same as clean text."""
    text = unicodedata.normalize("NFC", text)
    if len(text) > HEAD + TAIL:
        text = text[:HEAD] + "\n" + text[-TAIL:]
    text = text.replace("I", "ı").replace("İ", "i").lower().translate(_FOLD)
    text = unicodedata.normalize("NFKD", text)
    return "".join(c for c in text if not unicodedata.combining(c))


KINDS = ("w", "b", "c", "l", "h")   # words, bigrams, char 3-4 grams, line-start words, title-area words


def tokens(text: str, kinds=KINDS) -> list[str]:
    """Feature strings, before hashing. Digits collapse to '0' so numbers don't become features."""
    kinds = set(kinds)
    t = normalise(text)
    feats: list[str] = []
    for li, line in enumerate(t.split("\n")):
        ws = [_DIGITS.sub("0", w) for w in _WORD.findall(line)]
        if not ws:
            continue
        if "l" in kinds:
            feats.append("l:" + ws[0])                   # first word of a line: headings, field labels
            if len(ws) > 1:
                feats.append("l2:" + ws[0] + "_" + ws[1])
        for i, w in enumerate(ws):
            if "w" in kinds:
                feats.append("w:" + w)
            if i and "b" in kinds:
                feats.append("b:" + ws[i - 1] + "_" + w)
            if "c" in kinds and len(w) > 3 and w != "0":
                p = "<" + w + ">"
                for n in (3, 4):
                    feats.extend("c:" + p[j:j + n] for j in range(len(p) - n + 1))
    if "h" in kinds:
        feats.extend("h:" + _DIGITS.sub("0", w) for w in _WORD.findall(t[:300]))                  # words near the top: the title, the court, the notary
    return feats


def featurize(text: str, dim: int, kinds=KINDS) -> dict[int, float]:
    """Hashed, signed, log-scaled, L2-normalised bag of features: {index: value}."""
    counts: dict[int, float] = {}
    for f in tokens(text, kinds):
        h = fnv1a(f)
        i, sign = h % dim, (1.0 if (h >> 31) & 1 else -1.0)
        counts[i] = counts.get(i, 0.0) + sign
    vec = {i: math.copysign(math.log1p(abs(v)), v) for i, v in counts.items() if v}
    norm = math.sqrt(sum(v * v for v in vec.values())) or 1.0
    return {i: v / norm for i, v in vec.items()}


# ------------------------------------------------------------------ packs
_packs: dict[str, "Pack"] = {}


class Pack:
    def __init__(self, lang: str, root: Path | None = None, model_root: Path | None = None):
        """root: where <lang>.pack.json lives; model_root: where the weights live (lab runs point it elsewhere)."""
        self.lang = lang
        root, model_root = Path(root or PACKS), Path(model_root or root or PACKS)
        meta = json.loads((root / f"{lang}.pack.json").read_text(encoding="utf-8"))
        self.meta = meta
        self.labels: list[str] = [x["id"] for x in meta["types"]]
        self.types = {x["id"]: x for x in meta["types"]}
        self.threshold = float(meta.get("threshold", 0.5))
        self.model = None
        mp = model_root / f"{lang}.model.json"
        if mp.exists():
            m = json.loads(mp.read_text(encoding="utf-8"))
            w = array("b")
            w.frombytes((model_root / m["weights"]).read_bytes())
            if len(w) != m["dim"] * len(m["labels"]):
                raise RuntimeError(f"doctype weights for {lang!r} are damaged")
            self.model = m
            self.w = w
            self.dim, self.classes = m["dim"], m["labels"]
            self.scale, self.bias = m["scale"], m["bias"]
            self.kinds = tuple(m.get("kinds", KINDS))

    def logits(self, vec: dict[int, float]) -> list[float]:
        C, w = len(self.classes), self.w
        acc = [0.0] * C
        for i, v in vec.items():
            base = i * C
            for c in range(C):
                acc[c] += w[base + c] * v
        return [acc[c] * self.scale[c] + self.bias[c] for c in range(C)]


def pack(lang: str = "tr") -> Pack:
    if lang not in _packs:
        _packs[lang] = Pack(lang, model_root=os.environ.get("KATIP_DOCTYPE_MODELS") or None)
    return _packs[lang]


def languages() -> list[str]:
    return sorted(p.name.split(".")[0] for p in PACKS.glob("*.pack.json"))


# ------------------------------------------------------------------ classify
def _softmax(z: list[float]) -> list[float]:
    m = max(z)
    e = [math.exp(x - m) for x in z]
    s = sum(e)
    return [x / s for x in e]


def name(label: str, lang: str = "tr") -> dict:  # noqa: D401
    """{"local": "Ödeme emri", "en": "Payment order"}: the UI always shows the English line too."""
    t = pack(lang).types.get(label) or {"name": {"local": label, "en": label}}
    return dict(t["name"])


_STOP = {
    "tr": set("ve bir bu ile için olarak olan da de ki gibi daha çok ancak tarafından ise kadar sonra olup üzere "
              "veya göre ilgili edilmesi tarihli sayılı hakkında".split()),
    "nl": set("de het een en van in is dat op te voor met zijn niet aan er die bij ook als om door wordt naar "
              "uw u heeft worden deze tot".split()),
    "en": set("the and of to a in is that for on with as by this be are at from or an it which shall "
              "has have not".split()),
}


def detect_language(text: str) -> str:
    """"tr", "nl" or "en", by stop-word counts over the first ~4000 characters (no model, no network)."""
    ws = re.findall(r"[^\W\d_]+", unicodedata.normalize("NFC", text[:4000]).replace("I", "ı").replace("İ", "i").lower())
    score = {k: sum(w in v for w in ws) for k, v in _STOP.items()}
    score["tr"] += 2 * sum(c in "ğışİı" for c in text[:4000])
    return max(score, key=score.get) if any(score.values()) else "tr"


def classify(text: str, lang: str | None = None, k: int = 3) -> dict:
    """lang=None detects the language first. A language with labels but no trained weights abstains."""
    lang = lang or detect_language(text)
    if lang not in languages():
        return {"type": None, "lang": lang, "abstained": True, "confidence": 0.0, "top": [],
                "reason": f"no document-type pack for {lang!r}"}
    p = pack(lang)
    if p.model is None:
        return {"type": "overig" if "overig" in p.types else "diger", "lang": lang, "abstained": True,
                "confidence": 0.0, "top": [], "reason": f"no trained model for {lang!r} yet (labels and actions only)",
                "name": name("overig" if "overig" in p.types else "diger", lang)}
    if len(text.strip()) < 40:
        return {"type": "diger", "confidence": 0.0, "abstained": True, "reason": "too little text", "top": [],
                "name": name("diger", lang), "lang": lang, "model": p.model["version"]}
    probs = _softmax(p.logits(featurize(text, p.dim, p.kinds)))
    order = sorted(range(len(probs)), key=probs.__getitem__, reverse=True)
    best, conf = p.classes[order[0]], probs[order[0]]
    abstain = conf < p.threshold
    return {"type": "diger" if abstain else best, "confidence": round(conf, 3), "abstained": abstain,
            "guess": best, "name": name("diger" if abstain else best, lang),
            "top": [{"type": p.classes[i], "p": round(probs[i], 3), "name": name(p.classes[i], lang)} for i in order[:k]],
            "lang": lang, "model": p.model["version"]}


# ------------------------------------------------------------------ what to do next
_LAWS = r"(TBK|HMK|İİK|IIK|TTK|TMK|TCK|CMK|KVKK|VUK|İYUK|AİHS|Av\.?\s?K|İş\s?K(?:anunu)?|Tebligat\s?K(?:anunu)?)"
_CITE = [
    re.compile(_LAWS + r"\.?\s*(?:md\.?|m\.|madde|maddesi)\s*(\d+(?:/\d+)?)", re.I),
    re.compile(r"(\d{3,4})\s+sayılı\s+[^.\n]{0,60}?Kanun(?:u|'u|’u)?(?:nun|'nun|’nun)?\s+(\d+)\.?\s*madde", re.I),
]


def cited(text: str, limit: int = 12) -> list[str]:
    """Statute references written in the document itself ("TBK md. 117", "6698 sayılı ... 11. maddesi")."""
    out: list[str] = []
    for rx in _CITE:
        for m in rx.finditer(text):
            law = re.sub(r"\s+", " ", m.group(1)).strip()
            ref = f"{law} md. {m.group(2)}" if not law.isdigit() else f"{law} s. K. md. {m.group(2)}"
            if ref not in out:
                out.append(ref)
            if len(out) >= limit:
                return out
    return out


def next_steps(result: dict, text: str = "", lang: str | None = None, settings: dict | None = None) -> dict:
    """Plan for a classified document. Nothing here runs a network call.

    settings: {"auto_network": False, "off": ["emsal", ...]}: the lawyer's switches. Device steps
    auto-run unless switched off; network steps are suggestions unless auto_network is on, and even
    then the caller runs them, showing the query first.
    """
    settings = settings or {}
    lang = lang or result.get("lang") or "tr"
    off = set(settings.get("off") or ())
    p = pack(lang)
    t = p.types.get(result.get("type") or "diger") or p.types.get("diger") or {}
    steps = []
    for s in t.get("steps", []):
        if s["tool"] in off:
            continue
        net = s.get("where") == "network"
        steps.append({**s, "run": ("suggest" if net and not settings.get("auto_network") else "auto")})
    return {
        "type": result.get("type"), "name": name(result.get("type") or "diger", lang),
        "mevzuat": t.get("mevzuat", []),
        "cited_in_document": cited(text) if text else [],
        "emsal_queries": t.get("emsal", []),
        "steps": steps,
        "note": p.meta.get("note", {}),
    }


# ------------------------------------------------------------------ scan a folder
SCAN_EXT = {".pdf", ".docx", ".udf", ".txt", ".md", ".rtf", ".odt", ".png", ".jpg", ".jpeg", ".tif", ".tiff"}


def scan(folder: str | os.PathLike, lang: str | None = None, read=None, limit: int = 2000, depth: int = 4) -> list[dict]:
    """Classify every readable file under `folder`. Returns type and confidence per file, no text.

    read: callable(Path) -> str. Defaults to Kalkan's engine.read_text (PDF, DOCX, UDF, TXT; OCR when
    installed). Files that can't be read are listed with an error instead of a type.
    """
    if read is None:
        from . import engine
        read = engine.read_text
    root = Path(folder).expanduser()
    out: list[dict] = []
    for dirpath, dirs, files in os.walk(root):
        if len(Path(dirpath).relative_to(root).parts) >= depth:
            dirs[:] = []
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        for fn in sorted(files):
            fp = Path(dirpath) / fn
            if fn.startswith(".") or fp.suffix.lower() not in SCAN_EXT:
                continue
            row = {"path": str(fp.relative_to(root))}
            try:
                got = read(fp)
                text = got[1] if isinstance(got, tuple) else got   # engine.read_text -> (kind, text, ...)
                r = classify(text, lang)
                row.update(lang=r["lang"], type=r["type"], confidence=r["confidence"], abstained=r["abstained"], name=r.get("name"),
                           top=[(x["type"], x["p"]) for x in r["top"]])
                if r.get("reason"):
                    row["reason"] = r["reason"]
            except Exception as e:  # noqa: BLE001  (a bad file must not stop the scan)
                row["error"] = type(e).__name__
            out.append(row)
            if len(out) >= limit:
                return out
    return out
