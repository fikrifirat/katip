"""Encrypted masking of UYAP .udf files end to end (CPU, OpenFHE CKKS, take-2 engine).

  python lab/encrypted/run_udf.py docs/samples/dilekce_01.udf [more.udf ...]

Reads the text out of each UDF on the "client", runs Nano-FHE encrypted on the "server", decrypts, runs the
Katip pipeline (rules + model) on the decrypted label scores and writes the masked UDF back the way Katip does
(same-length blocks, so UDF styling stays aligned; the e-signature file is dropped). Compares with the same
model in plaintext and with plain Nano. Synthetic demo samples only. Writes results/udf/.
"""
from __future__ import annotations

import io, json, re, sys, time, zipfile
from pathlib import Path

import numpy as np
import torch

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent), str(HERE.parent / "legal")]
import bench_eval as E  # noqa: E402
import ckks_nano as C  # noqa: E402
from dev_select import tagger_for  # noqa: E402
from run_encrypted import CachedSession, WINDOW, windows_of  # noqa: E402

BLOCK = "█"
CDATA = re.compile(r"(<content>\s*<!\[CDATA\[)(.*?)(\]\]>\s*</content>)", re.S)


def udf_text(data):
    xml = zipfile.ZipFile(io.BytesIO(data)).read("content.xml").decode("utf-8")
    return xml, CDATA.search(xml).group(2)


def udf_redact(data, spans):
    """Same as src/py/local_formats.udf_redact: same-length blocks, signature dropped."""
    xml, text = udf_text(data); chars = list(text)
    for s, e, _ in spans:
        for k in range(s, e):
            if not chars[k].isspace(): chars[k] = BLOCK
    new = "".join(chars).replace("]]>", "]]&gt;")
    xml = CDATA.sub(lambda m: m.group(1) + new + m.group(3), xml, count=1)
    src = zipfile.ZipFile(io.BytesIO(data)); buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for it in src.infolist():
            if it.filename.lower().endswith(".sgn"): continue
            z.writestr(it, xml.encode("utf-8") if it.filename == "content.xml" else src.read(it.filename))
    return buf.getvalue(), new


def main():
    paths = [Path(p) for p in sys.argv[1:] if not p.startswith("--")]
    tg = tagger_for("fitted"); net = tg.sess.net
    lay = C.Layout(slots=32768, f=32, window=WINDOW)
    docs = [{"id": p.stem, "text": udf_text(p.read_bytes())[1], "path": p} for p in paths]
    wins = [w for d in docs for w in windows_of(tg, d["text"])]
    n_tok = sum(map(len, wins)); assert n_tok <= lay.T, f"{n_tok} tokens: one batch holds {lay.T}"
    res = {"files": [p.name for p in paths], "words": sum(len(d["text"].split()) for d in docs), "tokens": n_tok}
    print(json.dumps(res), flush=True)

    ctx = C.make_context(lay.rotations()); F = C.fold(net, 3.0)
    cl = C.Client(ctx, net, lay); srv = (C.ServerTake2 if "--take2" in sys.argv else C.Server)(ctx.cc, F, net.heads, lay)   # take 1 by default: less memory
    embs = cl.embed(wins); batch = lay.place([len(w) for w in wins])[0]
    t0 = time.time(); cts = cl.encrypt(cl.matrix(embs, batch)); res["encrypt_s"] = round(time.time() - t0, 1)
    res["upload_MB"] = round(sum(C.ct_bytes(c) for c in cts) / 1e6, 1)
    t0 = time.time(); out = srv.run(cts, lay.masks(batch)); res["server_s"] = round(time.time() - t0, 1)
    print("server", res["server_s"], "s", flush=True)
    t0 = time.time(); dec = cl.decrypt(out, 3, batch); res["decrypt_s"] = round(time.time() - t0, 2)
    with torch.no_grad():
        plain = [net(torch.tensor([w]), torch.ones(1, len(w), dtype=torch.long))[0].double().numpy() for w in wins]
    cache = {}
    for (wi, _, L), lg in zip(batch, dec): cache[tuple(wins[wi])] = lg.astype(np.float32)
    res["max_abs_logit_error"] = max(float(np.abs(cache[tuple(w)] - p).max()) for w, p in zip(wins, plain))

    te = tagger_for("fitted"); te.sess = CachedSession(cache)
    p_enc, _ = E.run(te, docs, "pipeline"); p_fit, _ = E.run(tagger_for("fitted"), docs, "pipeline")
    p_nano, _ = E.run(tagger_for("nano"), docs, "pipeline")
    res["identical_to_plaintext_same_model"] = E.label_agreement(p_fit, p_enc)
    res["identical_to_plain_nano"] = E.label_agreement(p_nano, p_enc)
    od = HERE / "results" / "udf"; od.mkdir(parents=True, exist_ok=True)
    res["per_file"] = []
    for d, pe, pn in zip(docs, p_enc, p_nano):
        data, masked = udf_redact(d["path"].read_bytes(), pe["spans"])
        (od / f"{d['id']}.encrypted-masked.udf").write_bytes(data)
        (od / f"{d['id']}.before.txt").write_text(d["text"]); (od / f"{d['id']}.after.txt").write_text(masked)
        _, masked_nano = udf_redact(d["path"].read_bytes(), pn["spans"])
        diff = [(s, e, d["text"][s:e]) for s, e, _ in pe["spans"] if [s, e] not in [x[:2] for x in pn["spans"]]] + \
               [(s, e, d["text"][s:e]) for s, e, _ in pn["spans"] if [s, e] not in [x[:2] for x in pe["spans"]]]
        res["per_file"].append({"file": d["id"], "spans": len(pe["spans"]), "same_as_plain_nano": masked == masked_nano,
                                "differs_from_plain_nano": [{"text": t, "only_in": "encrypted" if (s, e, t) in diff[:len(diff)] and [s, e] in [x[:2] for x in pe["spans"]] else "plain Nano"} for s, e, t in diff]})
    print(json.dumps(res, indent=1, ensure_ascii=False), flush=True)
    (od / "udf_run.json").write_text(json.dumps(res, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
