"""Cite-Bench-TR: ask language models Turkish legal questions and check every statute they cite.

    python lab/cite/bench.py run   --model qwen3:8b                         # local, through Ollama
    python lab/cite/bench.py run   --model gpt-4.1-mini --base-url https://api.openai.com/v1 --api-key-env OPENAI_API_KEY
    python lab/cite/bench.py score                                          # all answers/*.jsonl -> results/*.json

Any OpenAI-compatible chat endpoint works (Ollama, LM Studio, llama.cpp server, vLLM, OpenAI, OpenRouter...). Answers
are cached per (model, question, language), so a run can be stopped and resumed. Standard library only.

What we measure, per answer (details in README.md):
  cites      statute citations found by Katip Cite in the answer
  wrong      citations that are provably wrong: no such article, repealed article or law, number/name clash, unknown law
  right_art  the answer cites (correctly) at least one of the articles a lawyer would expect for this question
  fact       the answer states the key fact (deadline, share, threshold), where the question has one
  stale      the answer states the OLD rule of a recently changed law
  safe       no wrong citation AND the right article AND (if the question has one) the key fact. This is the ranking.
"""
from __future__ import annotations

import argparse, json, math, os, platform, random, re, sys, time, urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from katip_cite import BAD, Checker, fold  # noqa: E402

QUESTIONS = HERE / "data" / "questions.jsonl"
ANSWERS = HERE / "answers"
RESULTS = HERE / "results"
VERSION = "v0.1"

SYSTEM = {
    "tr": "Türk hukuku hakkında soruları yanıtlayan bir asistansın. Kısa ve net yanıt ver. Dayandığın kanun "
          "maddelerini kanun adı veya numarası ve madde numarasıyla belirt (örneğin: TBK m. 344).",
    "en": "You are an assistant answering questions about Turkish law. Answer briefly and clearly. Cite the statute "
          "articles you rely on, with the law's name or number and the article number (for example: Turkish Code of "
          "Obligations, Article 344).",
}


def load_questions():
    return [json.loads(l) for l in QUESTIONS.read_text().splitlines() if l.strip()]


def slug(model: str) -> str:
    return re.sub(r"[^a-zA-Z0-9._-]+", "_", model).strip("_")


# ----------------------------------------------------------------------------------------------------------- run
def chat(base_url, api_key, model, system, user, temperature, max_tokens, timeout):
    body = {"model": model, "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "temperature": temperature, "max_tokens": max_tokens, "seed": 7, "stream": False}
    req = urllib.request.Request(base_url.rstrip("/") + "/chat/completions", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json", **({"Authorization": f"Bearer {api_key}"} if api_key else {})})
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=timeout) as r:
        out = json.loads(r.read())
    msg = out["choices"][0]["message"]
    text = msg.get("content") or ""
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.S).strip()     # reasoning models (qwen3 etc.)
    return text, time.time() - t0, out.get("usage", {})


def run(a):
    qs = load_questions()
    if a.limit:
        qs = qs[: a.limit]
    langs = a.langs.split(",")
    ANSWERS.mkdir(exist_ok=True)
    path = ANSWERS / f"{slug(a.name or a.model)}.jsonl"
    done = set()
    if path.exists():
        for l in path.read_text().splitlines():
            r = json.loads(l)
            if r.get("answer") is not None:
                done.add((r["id"], r["lang"]))
    key = os.environ.get(a.api_key_env) if a.api_key_env else None
    todo = [(q, lang) for q in qs for lang in langs if (q["id"], lang) not in done]
    print(f"{a.model}: {len(todo)} to ask ({len(done)} cached) -> {path}")
    with open(path, "a") as f:
        for i, (q, lang) in enumerate(todo, 1):
            user = q["q_tr"] if lang == "tr" else q["q_en"]
            if a.no_think:
                user += " /no_think"
            try:
                text, sec, usage = chat(a.base_url, key, a.model, SYSTEM[lang], user, a.temperature, a.max_tokens, a.timeout)
                err = None
            except Exception as e:  # keep going; the row is retried next run
                text, sec, usage, err = None, 0.0, {}, f"{type(e).__name__}: {e}"
            f.write(json.dumps({"id": q["id"], "lang": lang, "model": a.model, "name": a.name or a.model,
                                "answer": text, "seconds": round(sec, 2), "usage": usage, "error": err,
                                "base_url": a.base_url if "localhost" in a.base_url or "127.0.0.1" in a.base_url else "remote",
                                "temperature": a.temperature, "bench": VERSION}, ensure_ascii=False) + "\n")
            f.flush()
            print(f"  [{i}/{len(todo)}] {q['id']} {lang} {sec:5.1f}s {'ERR ' + err if err else ''}")


# --------------------------------------------------------------------------------------------------------- score
def fold_rx(rx):
    """Fold a regex the way fold() folds text (i/ı/İ -> i, lower case) without touching regex syntax such as \\s*."""
    return rx.replace("İ", "i").replace("I", "i").replace("ı", "i").lower()


def matches(rx_list, text):
    t = fold(text)
    return any(re.search(fold_rx(rx), t) for rx in rx_list)


def expected_hit(cits, expect):
    want = set()
    for e in expect:
        no, art = e.split(":")
        want.add((no, art.lower()))
    for c in cits:
        if c["kind"] != "statute" or c["verdict"] != "OK":
            continue
        art = (c["article"] or "").lower()
        if (c["law_no"], art) in want or (c["law_no"], art.split("/")[0]) in want:
            return True
    return False


def score_answer(row, q, checker):
    text = row["answer"] or ""
    r = checker.check(text)
    seen, st = set(), []
    for c in r["citations"]:                   # one answer repeating the same citation counts once
        key = (c["law_no"], c["article"], c["verdict"])
        if c["kind"] == "statute" and key not in seen:
            seen.add(key); st.append(c)
    wrong = [c for c in st if c["verdict"] in BAD]
    hit = expected_hit(st, q["expect"])
    fact = matches(q["must"], text) if q["must"] else None
    stale = (matches(q["stale"], text) and not fact) if q.get("stale") else False
    safe = (not wrong) and hit and (fact is not False)
    return {"id": q["id"], "lang": row["lang"], "area": q["area"], "risk": q["risk"], "cites": len(st), "wrong": len(wrong),
            "ok": sum(c["verdict"] == "OK" for c in st), "unverified": sum(c["verdict"] == "UNVERIFIED" for c in st),
            "decisions": sum(c["kind"] == "decision" for c in r["citations"]), "right_art": hit, "fact": fact,
            "stale": stale, "safe": safe, "no_citation": len(st) == 0, "seconds": row.get("seconds"),
            "wrong_detail": [{"text": c["text"], "verdict": c["verdict"], "law": c["law_no"], "article": c["article"], "note": c["note"]} for c in wrong]}


def boot_ci(xs, n=2000, seed=0):
    if not xs:
        return [float("nan")] * 2
    rnd = random.Random(seed)
    ms = sorted(sum(rnd.choice(xs) for _ in xs) / len(xs) for _ in range(n))
    return [ms[int(0.025 * n)], ms[int(0.975 * n) - 1]]


def mcnemar(a, b):
    """Exact two-sided McNemar p for paired booleans."""
    n01 = sum(1 for x, y in zip(a, b) if x and not y)
    n10 = sum(1 for x, y in zip(a, b) if y and not x)
    n = n01 + n10
    if n == 0:
        return 1.0
    k = min(n01, n10)
    p = sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n
    return min(1.0, 2 * p)


def summarise(rows):
    def mean(xs):
        xs = [float(x) for x in xs if x is not None]
        return sum(xs) / len(xs) if xs else float("nan")
    cites = sum(r["cites"] for r in rows)
    wrong = sum(r["wrong"] for r in rows)
    ok = sum(r["ok"] for r in rows)
    return {"n": len(rows), "safe": mean(r["safe"] for r in rows), "safe_ci": boot_ci([float(r["safe"]) for r in rows]),
            "right_article": mean(r["right_art"] for r in rows), "key_fact": mean(r["fact"] for r in rows),
            "stale": sum(r["stale"] for r in rows),
            "citations": cites, "wrong_citations": wrong, "wrong_rate": wrong / (ok + wrong) if ok + wrong else float("nan"),
            "answers_with_wrong": mean(r["wrong"] > 0 for r in rows), "no_citation": mean(r["no_citation"] for r in rows),
            "decision_citations_per_answer": mean(r["decisions"] for r in rows),
            "seconds_per_answer": mean(r["seconds"] for r in rows)}


def score(a):
    checker = Checker()
    qs = {q["id"]: q for q in load_questions()}
    RESULTS.mkdir(exist_ok=True)
    files = [Path(p) for p in a.files] if a.files else sorted(ANSWERS.glob("*.jsonl"))
    for p in files:
        latest = {}
        for l in p.read_text().splitlines():
            r = json.loads(l)
            if r.get("answer") is not None and r["id"] in qs:
                latest[(r["id"], r["lang"])] = r
        if not latest:
            continue
        rows = [score_answer(r, qs[r["id"]], checker) for r in latest.values()]
        meta = next(iter(latest.values()))
        by = lambda key: {k: summarise([r for r in rows if r[key] == k]) for k in sorted({r[key] for r in rows})}
        tr = {r["id"]: r["safe"] for r in rows if r["lang"] == "tr"}
        en = {r["id"]: r["safe"] for r in rows if r["lang"] == "en"}
        both = sorted(set(tr) & set(en))
        out = {"system": p.stem, "name": meta["name"], "model": meta["model"], "bench": VERSION,
               "runs_locally": meta.get("base_url") != "remote", "temperature": meta.get("temperature"),
               "index": checker.meta, "machine": f"{platform.machine()} {platform.system()}",
               "questions": len({r['id'] for r in rows}), "complete": len(rows) == 2 * len(qs),
               "all": summarise(rows), "by_lang": by("lang"), "by_area": by("area"), "by_risk": by("risk"),
               "lang_gap": {"paired": len(both), "tr_minus_en": (sum(tr[i] for i in both) - sum(en[i] for i in both)) / len(both) if both else None,
                            "mcnemar_p": mcnemar([tr[i] for i in both], [en[i] for i in both]) if both else None},
               "wrong_examples": [dict(id=r["id"], lang=r["lang"], **w) for r in rows for w in r["wrong_detail"]][:200],
               "rows": rows}
        (RESULTS / f"{p.stem}.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
        s = out["all"]
        print(f"{p.stem:<28} safe {100 * s['safe']:5.1f}% [{100 * s['safe_ci'][0]:.1f}-{100 * s['safe_ci'][1]:.1f}]  "
              f"right article {100 * s['right_article']:5.1f}%  key fact {100 * s['key_fact']:5.1f}%  "
              f"wrong citations {s['wrong_citations']}/{s['citations']} ({100 * s['wrong_rate']:.1f}%)  stale {s['stale']}  n={s['n']}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--model", required=True)
    r.add_argument("--name", help="display name and file name (default: model)")
    r.add_argument("--base-url", default="http://localhost:11434/v1")
    r.add_argument("--api-key-env", default=None, help="environment variable that holds the API key (never pass keys inline)")
    r.add_argument("--langs", default="tr,en")
    r.add_argument("--temperature", type=float, default=0.0)
    r.add_argument("--max-tokens", type=int, default=800)
    r.add_argument("--timeout", type=int, default=300)
    r.add_argument("--limit", type=int, default=0, help="only the first N questions (smoke test)")
    r.add_argument("--no-think", action="store_true", help="append /no_think (Qwen3 hybrid models)")
    s = sub.add_parser("score")
    s.add_argument("files", nargs="*")
    a = ap.parse_args()
    run(a) if a.cmd == "run" else score(a)
