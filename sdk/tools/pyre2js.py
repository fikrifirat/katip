"""Compile Python regular expressions into JavaScript ones that match exactly the same text.

Python's ``re`` and JavaScript's RegExp disagree in ways that matter for Turkish:

* ``re.I`` treats i, I, ı and İ as one letter; JavaScript's ``/i`` does not (so ``kimlik`` would miss
  ``KİMLİK``).
* ``\\w``, ``\\d``, ``\\s`` and ``\\b`` are Unicode-aware in Python, ASCII-only (or differently defined) in
  JavaScript.
* ``$`` also matches before a final newline in Python; ``.`` excludes ``\\r`` and line separators in
  JavaScript; JavaScript's multiline ``^``/``$`` also break on ``\\r`` and U+2028.
* scoped flags ``(?i:...)`` only exist in recent JavaScript engines.

Instead of translating pattern text, this module parses each pattern with Python's own parser and
emits JavaScript with every character class spelled out as an explicit set of code points. Each set
is computed by running Python's regex engine itself over every Unicode code point, so the
JavaScript pattern accepts a character exactly when Python's does. Anchors and word boundaries
become lookarounds with the same meaning. The output needs only the ``u`` flag.

Backtracking order (greedy/lazy repeats, alternation left to right, leftmost match) is the same
in both engines, so with identical character sets and anchors the matches are identical; the
parity tests check that on real documents and on fuzzed text.
"""
from __future__ import annotations

import re
import sys
import unicodedata
from functools import lru_cache

try:  # Python 3.11+
    from re import _compiler as sre_compile, _constants as C, _parser as sre_parse
except ImportError:  # pragma: no cover
    import sre_compile, sre_constants as C, sre_parse  # type: ignore

ALL = "".join(chr(c) for c in range(0x110000))
I, M, S, X, U, A = re.I, re.M, re.S, re.X, re.U, re.A


def _ranges(chars: str) -> list[tuple[int, int]]:
    out: list[list[int]] = []
    for c in map(ord, chars):
        if out and out[-1][1] == c - 1:
            out[-1][1] = c
        else:
            out.append([c, c])
    return [(a, b) for a, b in out]


def _cp(c: int) -> str:
    ch = chr(c)
    if ch.isascii() and ch.isalnum():
        return ch
    return f"\\u{{{c:X}}}"


CATS: dict[str, frozenset] = {}


def _cats() -> dict[str, frozenset]:
    """Code points of each Unicode general category, by Python's unicodedata (Cs/Cn included)."""
    if not CATS:
        groups: dict[str, set] = {}
        for c in range(0x110000):
            groups.setdefault(unicodedata.category(chr(c)), set()).add(c)
        CATS.update({k: frozenset(v) for k, v in groups.items()})
        for major in "LMNPSZC":
            CATS[major] = frozenset().union(*(v for k, v in groups.items() if k[0] == major))
    return CATS


def _body(cps: set[int]) -> str:
    """Class body for a set of code points: whole general categories as \\p{..}, the rest as ranges.
    Exact by Python's Unicode database; JavaScript engines use the same categories, so the two agree
    on every character both Unicode versions have assigned."""
    cats, parts, left = _cats(), [], set(cps)
    for k in sorted((k for k in cats if len(k) == 1), key=lambda k: -len(cats[k])) + \
             sorted((k for k in cats if len(k) == 2 and k not in ("Cs", "Co")), key=lambda k: -len(cats[k])):
        v = cats[k]
        if len(v) > 64 and v <= cps and v & left:
            parts.append(f"\\p{{{'gc=' + k}}}")
            left -= v
    rs = _ranges("".join(chr(c) for c in sorted(left)))
    return "".join(parts) + "".join(_cp(a) if a == b else f"{_cp(a)}-{_cp(b)}" for a, b in rs)


def js_class(chars: str, negate_if_shorter: bool = True) -> str:
    """A JavaScript (u-mode) character class matching exactly ``chars``."""
    if not chars:
        return "[]"  # matches nothing
    cps = set(map(ord, chars))
    if len(cps) == 1:
        return _lit(chars[0])
    pos = "[" + _body(cps) + "]"
    if negate_if_shorter and len(cps) > 1000:
        rest = set(range(0x110000)) - cps
        neg = "[^" + _body(rest) + "]" if rest else "[\\s\\S]"
        if len(neg) < len(pos):
            return neg
    return pos


SYNTAX = set("^$\\.*+?()[]{}|/")


def _lit(ch: str) -> str:
    if ch in SYNTAX:
        return "\\" + ch
    if 0x20 <= ord(ch) < 0x7F:
        return ch
    return f"\\u{{{ord(ch):X}}}"


@lru_cache(maxsize=None)
def _matching(code: tuple, flags: int) -> str:
    """Every code point that the single-character item ``code`` matches under ``flags``."""
    sp = sre_parse.SubPattern(sre_parse.State())
    sp.state.flags = flags | re.U
    sp.data = [_thaw(code)]
    pat = sre_compile.compile(sp, flags | re.U)
    return "".join(pat.findall(ALL))


def _freeze(item):
    if isinstance(item, (list, tuple)):
        return tuple(_freeze(x) for x in item)
    return item


def _thaw(item):
    op, av = item
    if op is C.IN:
        return (op, [tuple(x) for x in av])
    return (op, av)


WORD = None


def word_chars() -> str:
    global WORD
    if WORD is None:
        WORD = "".join(re.findall(r"\w", ALL))
    return WORD


def W() -> str:
    return js_class(word_chars())


class Compiler:
    def __init__(self, flags: int):
        if flags & re.A or flags & re.L:
            raise ValueError("ASCII/LOCALE flags are not supported")
        self.groups = 0
        self.names: dict[int, str] = {}

    def seq(self, sub, flags) -> str:
        return "".join(self.node(op, av, flags) for op, av in sub)

    def node(self, op, av, flags) -> str:
        f = flags & (I | M | S)
        if op is C.LITERAL:
            return js_class(_matching(_freeze((op, av)), f & I)) if f & I else _lit(chr(av))
        if op is C.NOT_LITERAL:
            return js_class(_matching(_freeze((op, av)), f & I))
        if op is C.IN:
            return js_class(_matching(_freeze((op, av)), f & I))
        if op is C.ANY:
            return "[\\s\\S]" if f & S else "[^\\n]"
        if op is C.BRANCH:
            return "(?:" + "|".join(self.seq(b, flags) for b in av[1]) + ")"
        if op is C.SUBPATTERN:
            group, add, dele, p = av
            inner = self.seq(p, (flags | add) & ~dele)
            if group is None:
                return "(?:" + inner + ")"
            name = self.names.get(group)
            return f"(?<{name}>" + inner + ")" if name else "(" + inner + ")"
        if op in (C.MAX_REPEAT, C.MIN_REPEAT):
            lo, hi, p = av
            body = "(?:" + self.seq(p, flags) + ")"
            if hi is C.MAXREPEAT:
                q = "*" if lo == 0 else "+" if lo == 1 else f"{{{lo},}}"
            elif lo == 0 and hi == 1:
                q = "?"
            elif lo == hi:
                q = f"{{{lo}}}"
            else:
                q = f"{{{lo},{hi}}}"
            return body + q + ("?" if op is C.MIN_REPEAT else "")
        if op is C.ASSERT or op is C.ASSERT_NOT:
            d, p = av
            kind = ("=" if op is C.ASSERT else "!")
            return ("(?" if d == 1 else "(?<") + kind + self.seq(p, flags) + ")"
        if op is C.GROUPREF:
            return f"\\{av}"
        if op is C.AT:
            w = W()
            if av is C.AT_BEGINNING:
                return "(?:(?<![\\s\\S])|(?<=\\n))" if f & M else "(?<![\\s\\S])"
            if av is C.AT_BEGINNING_STRING:
                return "(?<![\\s\\S])"
            if av is C.AT_END:
                return "(?=\\n|(?![\\s\\S]))" if f & M else "(?=\\n?(?![\\s\\S]))"
            if av is C.AT_END_STRING:
                return "(?![\\s\\S])"
            if av is C.AT_BOUNDARY:
                return f"(?:(?<={w})(?!{w})|(?<!{w})(?={w}))"
            if av is C.AT_NON_BOUNDARY:
                return f"(?:(?<={w})(?={w})|(?<!{w})(?!{w}))"
        raise NotImplementedError(f"regex op {op} not supported")


def compile_pattern(pattern, flags: int = 0) -> dict:
    """Python pattern (str or compiled) -> {"source": JS source for the u flag, "groups": n, "empty": bool}."""
    if isinstance(pattern, re.Pattern):
        flags, pattern = pattern.flags, pattern.pattern
    parsed = sre_parse.parse(pattern, flags)
    c = Compiler(parsed.state.flags)
    c.names = {v: k for k, v in parsed.state.groupdict.items()}
    src = c.seq(parsed, parsed.state.flags)
    lo, _ = parsed.getwidth()
    # sanity: the JS source must at least compile in a JS engine (checked by the JS tests)
    return {"source": src, "groups": parsed.state.groups - 1, "empty": lo == 0}


def py_ignorecase_classes() -> dict[str, str]:
    """For runtime-built patterns (escaped user values under re.I): each character whose case-insensitive
    class in Python is more than itself -> every character of that class."""
    out = {}
    for ch in sorted({c for c in ALL if c.lower() != c or c.upper() != c or c in "ıiſsKkµ"}):
        if 0xD800 <= ord(ch) <= 0xDFFF:
            continue
        cls = _matching(_freeze((C.LITERAL, ord(ch))), I)
        if cls != ch:
            out[ch] = cls
    return out


if __name__ == "__main__":
    for p in sys.argv[1:]:
        print(compile_pattern(p)["source"])
