"""Generate the JavaScript SDK's engine tables from the vendored Python engine.

Writes sdk/js/src/engine/generated.ts with:
  * RX: every regular expression the engine uses, compiled by pyre2js so it matches exactly what
    Python's re matches (named compiled patterns are picked up automatically; patterns written inline
    in function bodies are listed in INLINE below, and check_coverage() fails the build if the
    engine gains an inline pattern that is not listed or loses one that is);
  * CHARS: Python's str.isupper/islower/isdigit/... for single characters, as JS classes;
  * IGNORECASE: Python's case-insensitive equivalents of each letter, for patterns built at run time;
  * CASEFOLD: characters whose str.casefold() differs from str.lower();
  * WORDS: the engine's word lists, already folded by the engine's own fold(), so lookups agree.

    python sdk/tools/gen_js_tables.py          # write
    python sdk/tools/gen_js_tables.py --check  # CI: fail if generated.ts is stale
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "sdk" / "python" / "src"))
sys.path.insert(0, str(Path(__file__).parent))

import pyre2js  # noqa: E402
from katip_mask._engine import local_detect, recognizers, textutil  # noqa: E402
from katip_mask._engine.textutil import TR_LETTER, TR_LOWER, TR_UPPER, fold, wordlist  # noqa: E402

OUT = ROOT / "sdk" / "js" / "src" / "engine" / "generated.ts"
SPEC_OUT = ROOT / "sdk" / "js" / "src" / "spec.generated.ts"
ENGINE = ROOT / "sdk" / "python" / "src" / "katip_mask" / "_engine"

# Patterns written inline in the engine's function bodies: name -> (pattern, flags). Same text as the source.
INLINE: dict[str, tuple[str, int]] = {
    "iban_ws": (r"\s", 0),
    "iban_shape": (r"[A-Z]{2}\d{2}[A-Z0-9]{10,30}", 0),
    "non_digit": (r"\D", 0),
    "trim_word": (r"\s+(?=[A-Z]?[a-zçğıöşü]{2,})", 0),
    "space_dash": (r"[ -]", 0),
    "year_slash": (r"\d{4}/\d+", 0),
    "fin_cue": (r"(?i)f[İi]n|[şs][əe]xsiyy", 0),
    "iban_split": (r"([ \n])", 0),
    "email_split": (r"[._+\-\d]+", 0),
    "gap12": (r"[ \t]{1,2}", 0),
    "org_split": (r"[,;:()\n]|\s[-–—]\s", 0),
    "greeting": (r"(?:merhaba|sevgili|degerli|sayin|dear|hi|selam)[ ]*$", 0),
    "greeting_after": (r"^\s*[,!\n]", 0),
    "hanim_bey": (r"^\s*(?:hanım|bey)\b", re.I),
    "no_digit": (r"\bNo\s*[:.]?\s*\d", 0),
    "letters_digits": (rf"[{TR_LETTER}0-9]+", 0),
    "upper_or_digit": (rf"[{TR_UPPER}0-9]", 0),
    "letters": (rf"[{TR_LETTER}]+", 0),
    "grow_left": (rf"([{TR_UPPER}0-9][{TR_LETTER}0-9.'’]*)\s*$", 0),
    "grow_ws": (r"[ \t]*(\n)?[ \t]*", 0),
    "grow_next": (r"(?:No|Daire|Kat|D\s*:|\d{5}|[A-ZÇĞİÖŞÜ]+\s*/)", 0),
    "slash_after": (r"\s*/", 0),
    "slash_before": (r"/\s*$", 0),
    "colon": (r"[:]", 0),
    "postcode": (r"\d{5}", 0),
    "cap_word": (rf"[{TR_UPPER}][{TR_LETTER}]+", 0),
    "slash_gap": (r"[ \t]*/?[ \t]*", 0),
    "form_tok": (rf"[{TR_LETTER}0-9][{TR_LETTER}0-9'’.:/-]*", 0),
    "digit_before": (r"\d[ ]?$", 0),
    "digit_after": (r"^[ ]?\d", 0),
    "sentence_start": (r"(?:^|[.!?:;\n(\"“]\s*)$", 0),
    "next_word": (rf"[ \t]+([{TR_LETTER}]+)", 0),
    "roman": (r"[IVXLC]+", 0),
}
# inline patterns built from run-time values: the JS port builds these itself (see engine/pyre.ts)
DYNAMIC = {
    "local_detect.py": [r'rf"(?<![{TR_LETTER}]){re.escape(w)}(?![{TR_LETTER}])"'],
}


def named_patterns() -> dict[str, re.Pattern]:
    out: dict[str, re.Pattern] = {}
    for mod in (recognizers, local_detect, textutil):
        short = mod.__name__.rsplit(".", 1)[-1]
        for k, v in vars(mod).items():
            if isinstance(v, re.Pattern):
                out[f"{short}.{k}"] = v
            elif isinstance(v, (list, tuple)) and v and all(isinstance(x, re.Pattern) for x in v):
                for i, x in enumerate(v):
                    out[f"{short}.{k}.{i}"] = x
            elif isinstance(v, type) and v.__module__ == mod.__name__:
                for a, x in vars(v).items():
                    if isinstance(x, re.Pattern):
                        out[f"{v.__name__}.{a}"] = x
    for k, x in recognizers.SpecialCategoryRecognizer()._res.items():
        out[f"special.{k}"] = x
    from katip_mask import safety  # the SDK's own post-processing (same as Kalkan's)
    out["safety._IDS"] = safety._IDS
    return out


def check_coverage() -> None:
    """Every inline pattern literal in the engine must be in INLINE, and every INLINE entry must still be used."""
    seen: set[tuple[str, int]] = set()
    unknown: list[str] = []
    for f in ("recognizers.py", "local_detect.py", "textutil.py"):
        src = (ENGINE / f).read_text()
        mod = {"recognizers.py": recognizers, "local_detect.py": local_detect, "textutil.py": textutil}[f]
        for node in ast.walk(ast.parse(src)):
            if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                    and isinstance(node.func.value, ast.Name) and node.func.value.id == "re"
                    and node.func.attr in ("search", "match", "fullmatch", "finditer", "findall", "sub", "split")):
                continue
            arg = node.args[0]
            seg = ast.get_source_segment(src, arg)
            try:
                pat = eval(compile(ast.Expression(arg), f, "eval"), vars(mod))  # module constants only
            except NameError:
                if seg not in DYNAMIC.get(f, []):
                    unknown.append(f"{f}:{node.lineno} {seg}")
                continue
            flags = 0
            for kw in node.keywords:
                if kw.arg == "flags":
                    flags = eval(compile(ast.Expression(kw.value), f, "eval"), vars(mod))
            n_pos = {"sub": 4, "split": 3}.get(node.func.attr, 3)
            if len(node.args) >= n_pos:
                flags = eval(compile(ast.Expression(node.args[n_pos - 1]), f, "eval"), vars(mod))
            seen.add((pat, int(flags)))
            if (pat, int(flags)) not in {(p, int(fl)) for p, fl in INLINE.values()}:
                unknown.append(f"{f}:{node.lineno} {pat!r} flags={int(flags)}")
    stale = [k for k, (p, fl) in INLINE.items() if (p, int(fl)) not in seen]
    if unknown or stale:
        sys.exit("inline regex table out of date.\n  not listed: " + "\n  ".join(unknown) + "\n  no longer used: " + ", ".join(stale))


def char_tables() -> dict[str, str]:
    import unicodedata
    allc = [chr(c) for c in range(0x110000)]
    preds = {
        "upper": str.isupper, "lower": str.islower, "title": lambda c: unicodedata.category(c) == "Lt",
        "digit": str.isdigit, "alnum": str.isalnum, "alpha": str.isalpha, "space": str.isspace,
    }
    return {k: pyre2js.js_class("".join(c for c in allc if p(c))) for k, p in preds.items()}


def casefold_table() -> dict[str, str]:
    return {chr(c): chr(c).casefold() for c in range(0x110000)
            if not 0xD800 <= c <= 0xDFFF and chr(c).casefold() != chr(c).lower()}


def words() -> dict[str, list[str]]:
    out = {n: sorted(wordlist(n)) for n in ("first_names.txt", "last_names.txt", "common_words.txt", "stopwords_caps.txt",
                                           "provinces.txt", "districts.txt", "ambiguous_first.txt")}
    from importlib import resources
    places: set[str] = set()
    for f in ("provinces.txt", "districts.txt"):  # local_detect._place_words: no comment skipping
        places |= {fold(w).strip() for w in resources.files("katip_mask._engine.data").joinpath(f).read_text("utf-8").splitlines() if w.strip()}
    out["_place_words"] = sorted(places)
    return out


def render() -> str:
    rx = {}
    for name, p in sorted(named_patterns().items()):
        rx[name] = pyre2js.compile_pattern(p)
    for name, (p, fl) in sorted(INLINE.items()):
        rx["inline." + name] = pyre2js.compile_pattern(p, fl)
    w = pyre2js.word_chars()
    consts = {
        "TR_UPPER": TR_UPPER, "TR_LOWER": TR_LOWER, "TR_LETTER": TR_LETTER,
        "TR_LETTER_CLASS": pyre2js.js_class("".join(re.findall(rf"[{TR_LETTER}]", pyre2js.ALL))),
        "WORD_CLASS": pyre2js.js_class(w),
        "LONE_NAME_SCORE": repr(local_detect.LONE_NAME_SCORE),
    }
    src = json.dumps({"rx": rx, "chars": char_tables(), "ignorecase": pyre2js.py_ignorecase_classes(),
                      "casefold": casefold_table(), "consts": consts}, ensure_ascii=False, sort_keys=True)
    data = words()
    lines = [
        "// GENERATED by sdk/tools/gen_js_tables.py from the vendored Python engine. Do not edit.",
        "// Regexes are compiled with sdk/tools/pyre2js.py so they match exactly what Python's re matches.",
        f"// Unicode {UNICODE}.",
        "/* eslint-disable */",
        f"export const ENGINE_SHA256 = {json.dumps(json.loads((ENGINE / 'SOURCE.json').read_text())['sha256'])};",
        f"export const TABLES: {{ rx: Record<string, {{ source: string; groups: number; empty: boolean }}>; chars: Record<string, string>; "
        f"ignorecase: Record<string, string>; casefold: Record<string, string>; consts: Record<string, string> }} = {src};",
        "export const WORDS: Record<string, string> = {",
    ]
    for k, v in data.items():
        lines.append(f"  {json.dumps(k)}: {json.dumps(chr(10).join(v), ensure_ascii=False)},")
    lines.append("};")
    return "\n".join(lines) + "\n"


def render_spec() -> str:
    profiles = json.loads((ROOT / "sdk" / "spec" / "profiles.json").read_text())
    models = json.loads((ROOT / "sdk" / "spec" / "models.json").read_text())
    return ("// GENERATED by sdk/tools/gen_js_tables.py from sdk/spec/*.json. Do not edit.\n"
            f"export const PROFILE_SPEC = {json.dumps(profiles, ensure_ascii=False, indent=1)} as const;\n"
            f"export const MODEL_SPEC = {json.dumps(models, ensure_ascii=False, indent=1)} as const;\n")


# Character classes depend on the Unicode tables of the Python that generates them; pin one so the
# output is reproducible (Python 3.14 ships Unicode 16.0). CI generates and checks with the same version.
UNICODE = "16.0.0"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    import unicodedata
    if unicodedata.unidata_version != UNICODE:
        sys.exit(f"gen_js_tables: needs Unicode {UNICODE} (Python 3.14), this Python has {unicodedata.unidata_version}")
    check_coverage()
    out, spec = render(), render_spec()
    if a.check:
        for path, want in ((OUT, out), (SPEC_OUT, spec)):
            if not path.exists() or path.read_text() != want:
                sys.exit(f"{path.relative_to(ROOT)} is stale: run python sdk/tools/gen_js_tables.py")
        print("generated JS tables are up to date")
        return
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(out)
    SPEC_OUT.write_text(spec)
    print(f"wrote {OUT.relative_to(ROOT)} ({len(out) // 1024} KB, sha256 {hashlib.sha256(out.encode()).hexdigest()[:12]})")


if __name__ == "__main__":
    main()
