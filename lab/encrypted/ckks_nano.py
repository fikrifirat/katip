"""Nano-FHE under real encryption: CKKS (OpenFHE), client/server split.

Client (the lawyer's browser): tokenizes, looks up embeddings + first LayerNorm in plaintext, packs the token
vectors into ciphertexts, encrypts, and later decrypts the 3 label scores per token. It holds the secret key.
Server: holds only public evaluation keys and the model weights; runs both transformer layers and the
classifier on ciphertext. It never sees a token, an embedding or a label.

Packing (`Layout`): each ciphertext holds f features x T token slots. Linear layers mix features with
rotations by multiples of T (generalised diagonal method); attention over +-W neighbours rotates by up to W
slots, and slots that would cross a window boundary are masked with plaintext masks.

Multiplicative depth per layer is 8 (see `depth()`); two layers + classifier = 16, no bootstrapping.
"""
from __future__ import annotations

import os, tempfile, time
from dataclasses import dataclass, field

import numpy as np
import openfhe as fhe
import torch


# ----------------------------------------------------------------------------------------- weight folding
@dataclass
class Folded:
    """Plaintext weights of one layer, folded so each FHE step is one weighted sum."""
    Wq: np.ndarray; bq: np.ndarray; Wk: np.ndarray; bk: np.ndarray; Wv: np.ndarray; bv: np.ndarray
    Ax: np.ndarray; Ba: np.ndarray; c1: np.ndarray             # y  = Ax x + Ba a + c1          (o-proj + LN1)
    W1: np.ndarray; b1: np.ndarray                             # h' = W1 y + b1                 (shifted so g = alpha h'^2 + const)
    Ay: np.ndarray; Bs: np.ndarray; c2: np.ndarray             # y2 = Ay y + Bs h'^2 + c2       (FFN out + LN2 [+ classifier])


def fold(net, c_attn: float, gelu=(0.1535, 0.5, 0.0723)):
    """Fold Nano-FHE's weights. The last layer's LN2 is folded together with the classifier (3 outputs)."""
    H = net.hidden; d = H // net.heads
    C = np.eye(H) - np.ones((H, H)) / H                         # centring: x - mean(x)
    al, be, ga = gelu
    shift = be / (2 * al); const = ga - be * be / (4 * al)      # al x^2 + be x + ga = al (x + shift)^2 + const
    out = []
    n = len(net.layers)
    for li, L in enumerate(net.layers):
        g = lambda m: m.weight.detach().double().numpy()
        b = lambda m: m.bias.detach().double().numpy()
        s = 1.0 / (d ** 0.5) / c_attn                           # softmax stand-in uses (1 + q.k / (sqrt(d) c))^2
        A1 = np.diag(g(L.ln1)) @ C / getattr(L.ln1, "fixed_sigma", 1.0)
        A2 = np.diag(g(L.ln2)) @ C / getattr(L.ln2, "fixed_sigma", 1.0)
        c2 = A2 @ (g(L.f2) @ np.full(g(L.f1).shape[0], const) + b(L.f2)) + b(L.ln2)
        Ay, Bs = A2, A2 @ (al * g(L.f2))
        if li == n - 1:                                         # fold the classifier in: 3 outputs instead of 128
            Wc, bc = g(net.cls), b(net.cls)
            Ay, Bs, c2 = Wc @ Ay, Wc @ Bs, Wc @ c2 + bc
        out.append(Folded(Wq=g(L.q) * s, bq=b(L.q) * s, Wk=g(L.k), bk=b(L.k), Wv=g(L.v), bv=b(L.v),
                          Ax=A1, Ba=A1 @ g(L.o), c1=A1 @ b(L.o) + b(L.ln1),
                          W1=g(L.f1), b1=b(L.f1) + shift, Ay=Ay, Bs=Bs, c2=c2))
    return out


def plain_reference(net, x, mask, folded, window):
    """The folded computation in float64 numpy, same packing semantics, to check the CKKS output against."""
    out = []
    for xi, mi in zip(x, mask):
        T = int(mi.sum()); h = xi[:T].astype(np.float64)
        for F in folded:
            q, k, v = h @ F.Wq.T + F.bq, h @ F.Wk.T + F.bk, h @ F.Wv.T + F.bv
            a = np.zeros_like(h); d = h.shape[1] // net.heads
            for hd in range(net.heads):
                sl = slice(hd * d, (hd + 1) * d)
                for t in range(T):
                    js = [j for j in range(max(0, t - window), min(T, t + window + 1))]
                    p = (1 + q[t, sl] @ k[js, sl].T) ** 2 / len(js)
                    a[t, sl] = p @ v[js, sl]
            y = h @ F.Ax.T + a @ F.Ba.T + F.c1
            hp = y @ F.W1.T + F.b1
            h = y @ F.Ay.T + (hp * hp) @ F.Bs.T + F.c2
        out.append(h)
    return out


def depth():
    """Levels used: per layer QKV 1, q.k 2, square 3, x masked v 4, o+LN1 5, W1 6, square 7, W2+LN2 8."""
    return 16


# ---------------------------------------------------------------------------------------------- crypto
@dataclass
class Context:
    cc: object
    keys: object
    slots: int
    ring_dim: int
    sizes: dict = field(default_factory=dict)


def make_context(rotations, ring_dim: int | None = None, secure: bool = True, scale_bits: int = 40, first_bits: int = 60,
                 dnum: int | None = None) -> Context:
    p = fhe.CCParamsCKKSRNS()
    p.SetMultiplicativeDepth(depth())
    p.SetScalingModSize(scale_bits)
    p.SetFirstModSize(first_bits)
    p.SetScalingTechnique(fhe.FLEXIBLEAUTO)
    if dnum: p.SetNumLargeDigits(dnum)
    if secure:
        p.SetSecurityLevel(fhe.HEStd_128_classic)
        if ring_dim: p.SetRingDim(ring_dim)
    else:
        p.SetSecurityLevel(fhe.HEStd_NotSet); p.SetRingDim(ring_dim or 1 << 12)
    cc = fhe.GenCryptoContext(p)
    for f in (fhe.PKE, fhe.KEYSWITCH, fhe.LEVELEDSHE, fhe.ADVANCEDSHE):
        cc.Enable(f)
    N = cc.GetRingDimension()
    t0 = time.time()
    keys = cc.KeyGen()
    cc.EvalMultKeyGen(keys.secretKey)
    cc.EvalRotateKeyGen(keys.secretKey, sorted(set(rotations)))
    ctx = Context(cc, keys, N // 2, N)
    ctx.sizes["keygen_s"] = round(time.time() - t0, 1)
    return ctx


def key_bytes(ctx: Context) -> dict:
    """Serialized size of what the client uploads once (public key + relinearization + rotation keys)."""
    out = {}
    with tempfile.TemporaryDirectory() as d:
        f = os.path.join(d, "k")
        fhe.SerializeToFile(f, ctx.keys.publicKey, fhe.BINARY); out["public_key_MB"] = os.path.getsize(f) / 1e6
        ctx.cc.SerializeEvalMultKey(f, fhe.BINARY); out["relin_key_MB"] = os.path.getsize(f) / 1e6
        ctx.cc.SerializeEvalAutomorphismKey(f, fhe.BINARY); out["rotation_keys_MB"] = os.path.getsize(f) / 1e6
    return {k: round(v, 1) for k, v in out.items()}


def ct_bytes(ct) -> int:
    with tempfile.TemporaryDirectory() as d:
        f = os.path.join(d, "c"); fhe.SerializeToFile(f, ct, fhe.BINARY)
        return os.path.getsize(f)


# ----------------------------------------------------------------------------------------------- packing
@dataclass
class Layout:
    """Block packing: a ciphertext holds `f` features x T token slots (slot = block * T + token).

    A tensor of H features is H/f ciphertexts. Rotating by r moves every feature's tokens by r at once,
    so attention needs H/f rotations per offset instead of H. Linear layers mix the f blocks inside a
    ciphertext with rotations by multiples of T (generalised diagonal method).
    """
    slots: int
    f: int
    window: int

    @property
    def T(self): return self.slots // self.f

    def rotations(self):
        r = [x for x in range(-self.window, self.window + 1) if x]
        r += [k * self.T for k in range(1, self.f)]
        return r

    def place(self, lengths):
        """Greedy: windows back to back in [0, T). Returns batches of (window index, start, length)."""
        batches, cur, pos = [], [], 0
        for i, L in enumerate(lengths):
            if pos + L > self.T:
                batches.append(cur); cur, pos = [], 0
            cur.append((i, pos, L)); pos += L
        if cur: batches.append(cur)
        return batches

    def masks(self, batch):
        """For each offset r: value 1/n_t at token t if t+r is in t's window (n_t = number of such keys), replicated per block."""
        valid = {}; n = np.zeros(self.T)
        for r in range(-self.window, self.window + 1):
            m = np.zeros(self.T)
            for _, s, L in batch:
                t = np.arange(L); ok = (t + r >= 0) & (t + r < L)
                m[s + t[ok]] = 1
            valid[r] = m; n += m
        n[n == 0] = 1
        return {r: np.tile(m / n, self.f) for r, m in valid.items()}

    def to_slots(self, X):
        """[T, H] token-feature matrix -> list of H/f slot vectors."""
        H = X.shape[1]
        return [X[:, I * self.f:(I + 1) * self.f].T.reshape(-1) for I in range(H // self.f)]

    def from_slots(self, vecs, H):
        X = np.zeros((self.T, len(vecs) * self.f))
        for I, v in enumerate(vecs):
            X[:, I * self.f:(I + 1) * self.f] = v.reshape(self.f, self.T).T
        return X[:, :H]


# ----------------------------------------------------------------------------------------------- server
class Server:
    """Runs Nano-FHE's two layers + classifier on ciphertexts. Holds evaluation keys and weights, no secret key."""

    def __init__(self, cc, folded, heads, lay: Layout, log=print):
        self.cc, self.F, self.heads, self.lay, self.log = cc, folded, heads, lay, log
        self.M = 2 * cc.GetRingDimension()
        self.timings, self.counts = {}, {}

    def _tick(self, k, t0):
        self.timings[k] = round(self.timings.get(k, 0) + time.time() - t0, 1)

    def _rots(self, ct, steps):
        pre = self.cc.EvalFastRotationPrecompute(ct)
        self.counts["rotations"] = self.counts.get("rotations", 0) + len([s for s in steps if s])
        return {s: (ct if s == 0 else self.cc.EvalFastRotation(ct, s, self.M, pre)) for s in steps}

    def _linear(self, terms, n_out, bias):
        """sum over (cts, W) of W @ x, plus bias; W is [n_out, n_in]. Generalised diagonal method per block pair."""
        cc, f, T = self.cc, self.lay.f, self.lay.T
        nJ = (n_out + f - 1) // f
        out = [None] * nJ
        for cts, W in terms:
            Wp = np.zeros((nJ * f, len(cts) * f)); Wp[:W.shape[0], :W.shape[1]] = W
            for I, ct in enumerate(cts):
                R = self._rots(ct, [k * T for k in range(f)])
                for J in range(nJ):
                    for k in range(f):
                        b = np.arange(f)
                        diag = Wp[J * f + b, I * f + (b + k) % f]            # value for output block b
                        if not diag.any(): continue
                        pt = cc.MakeCKKSPackedPlaintext(np.repeat(diag, T).tolist())
                        t = cc.EvalMult(R[k * T], pt)
                        out[J] = t if out[J] is None else cc.EvalAdd(out[J], t)
                        self.counts["pt_mults"] = self.counts.get("pt_mults", 0) + 1
        bp = np.zeros(nJ * f); bp[:len(bias)] = bias
        return [cc.EvalAdd(o, cc.MakeCKKSPackedPlaintext(np.repeat(bp[J * f:(J + 1) * f], T).tolist())) for J, o in enumerate(out)]

    def _block_sum(self, ct):
        """Sum of the f blocks, replicated into every block (log2 f rotations)."""
        cc, T, s = self.cc, self.lay.T, 1
        while s < self.lay.f:
            ct = cc.EvalAdd(ct, cc.EvalRotate(ct, s * T)); s *= 2
            self.counts["rotations"] = self.counts.get("rotations", 0) + 1
        return ct

    def layer(self, x, F, masks_pt, last):
        cc, W, f = self.cc, self.lay.window, self.lay.f
        H = len(x) * f; d = H // self.heads; per = d // f            # ciphertexts per head
        offs = list(range(-W, W + 1))
        t0 = time.time()
        q = self._linear([(x, F.Wq)], H, F.bq); k = self._linear([(x, F.Wk)], H, F.bk); v = self._linear([(x, F.Wv)], H, F.bv)
        self._tick("Q, K, V", t0); t0 = time.time()
        a = []
        for h in range(self.heads):
            Is = range(h * per, (h + 1) * per)
            kr = {I: self._rots(k[I], offs) for I in Is}
            p = {}
            for r in offs:
                acc = None
                for I in Is:
                    t = cc.EvalMultNoRelin(q[I], kr[I][r]); acc = t if acc is None else cc.EvalAdd(acc, t)
                s = self._block_sum(cc.Relinearize(acc))
                p[r] = cc.EvalSquare(cc.EvalAdd(s, 1.0))
            del kr
            for I in Is:
                vr = self._rots(v[I], offs); acc = None
                for r in offs:
                    t = cc.EvalMultNoRelin(p[r], cc.EvalMult(vr[r], masks_pt[r])); acc = t if acc is None else cc.EvalAdd(acc, t)
                a.append(cc.Relinearize(acc))
        del q, k, v
        self._tick("attention", t0); t0 = time.time()
        y = self._linear([(x, F.Ax), (a, F.Ba)], H, F.c1)
        self._rcache = {}                                   # x is no longer needed
        self._tick("output + LayerNorm", t0); t0 = time.time()
        hp = self._linear([(y, F.W1)], F.W1.shape[0], F.b1)
        sq = [cc.EvalSquare(t) for t in hp]; del hp
        out = self._linear([(y, F.Ay), (sq, F.Bs)], F.Ay.shape[0], F.c2)
        self._tick("feed-forward + LayerNorm" + (" + classifier" if last else ""), t0)
        return out

    def run(self, cts, masks):
        masks_pt = {r: self.cc.MakeCKKSPackedPlaintext(m.tolist()) for r, m in masks.items()}
        x = cts
        for i, F in enumerate(self.F):
            t0 = time.time()
            x = self.layer(x, F, masks_pt, last=i == len(self.F) - 1)
            self.log(f"    layer {i + 1}: {time.time() - t0:.0f}s  {self.timings}", flush=True)
        return x


class ServerTake2(Server):
    """Take 2: same maths, same answers, faster on a multi-core CPU.

    1. openfhe-python releases the GIL, and OpenMP inside one CKKS operation barely helps at these sizes, so
       independent operations run on a thread pool (one thread per core) with OMP_NUM_THREADS=1.
    2. Attention's 32 rotations per ciphertext and its products also run on the pool (take 2b).
    3. Rotations of a ciphertext are computed once per layer and reused: x feeds Q, K, V and the residual
       (4 linear layers), y feeds the FFN and its residual, so those rotations were being redone.
    """

    def __init__(self, *a, threads=None, **kw):
        super().__init__(*a, **kw)
        from concurrent.futures import ThreadPoolExecutor
        self.pool = ThreadPoolExecutor(threads or os.cpu_count())
        self._rcache = {}

    def _map(self, fn, items):
        return list(self.pool.map(fn, items))

    def _rots_par(self, ct, steps):
        """Hoisted rotations of one ciphertext, the rotations themselves spread over the thread pool."""
        pre = self.cc.EvalFastRotationPrecompute(ct)
        self.counts["rotations"] = self.counts.get("rotations", 0) + len([s for s in steps if s])
        rs = self._map(lambda s: ct if s == 0 else self.cc.EvalFastRotation(ct, s, self.M, pre), steps)
        return dict(zip(steps, rs))

    def _rot_all(self, cts):
        """Block rotations (multiples of T) for every ciphertext, cached by object identity for this layer."""
        T, f = self.lay.T, self.lay.f
        todo = [c for c in cts if id(c) not in self._rcache]
        for c, R in zip(todo, self._map(lambda c: self._rots(c, [k * T for k in range(f)]), todo)):
            self._rcache[id(c)] = (c, R)
        return [self._rcache[id(c)][1] for c in cts]

    def _linear(self, terms, n_out, bias):
        cc, f, T = self.cc, self.lay.f, self.lay.T
        nJ = (n_out + f - 1) // f
        prepared = []
        for cts, W in terms:
            Wp = np.zeros((nJ * f, len(cts) * f)); Wp[:W.shape[0], :W.shape[1]] = W
            prepared.append((self._rot_all(cts), Wp))
        bp = np.zeros(nJ * f); bp[:len(bias)] = bias
        b = np.arange(f)
        def block(J):
            acc = None
            for Rs, Wp in prepared:
                for I, R in enumerate(Rs):
                    for k in range(f):
                        diag = Wp[J * f + b, I * f + (b + k) % f]
                        if not diag.any(): continue
                        t = cc.EvalMult(R[k * T], cc.MakeCKKSPackedPlaintext(np.repeat(diag, T).tolist()))
                        acc = t if acc is None else cc.EvalAdd(acc, t)
            return cc.EvalAdd(acc, cc.MakeCKKSPackedPlaintext(np.repeat(bp[J * f:(J + 1) * f], T).tolist()))
        return self._map(block, range(nJ))

    def layer(self, x, F, masks_pt, last):
        cc, W, f = self.cc, self.lay.window, self.lay.f
        H = len(x) * f; d = H // self.heads; per = d // f
        offs = list(range(-W, W + 1)); self._rcache = {}
        t0 = time.time()
        q = self._linear([(x, F.Wq)], H, F.bq); k = self._linear([(x, F.Wk)], H, F.bk); v = self._linear([(x, F.Wv)], H, F.bv)
        self._tick("Q, K, V", t0); t0 = time.time()
        a = [None] * len(v)
        for h in range(self.heads):
            Is = list(range(h * per, (h + 1) * per))
            kr = {I: self._rots_par(k[I], offs) for I in Is}
            def score(r):
                acc = None
                for I in Is:
                    t = cc.EvalMultNoRelin(q[I], kr[I][r]); acc = t if acc is None else cc.EvalAdd(acc, t)
                s = self._block_sum(cc.Relinearize(acc))
                return cc.EvalSquare(cc.EvalAdd(s, 1.0))
            p = dict(zip(offs, self._map(score, offs))); del kr
            vr = {I: self._rots_par(v[I], offs) for I in Is}
            def term(Ir):
                I, r = Ir
                return cc.EvalMultNoRelin(p[r], cc.EvalMult(vr[I][r], masks_pt[r]))
            for I in Is:                                   # products in parallel, then a sum and one relinearization
                ts = self._map(term, [(I, r) for r in offs])
                acc = ts[0]
                for t in ts[1:]: acc = cc.EvalAdd(acc, t)
                a[I] = cc.Relinearize(acc)
            del vr, p
        del q, k, v
        self._tick("attention", t0); t0 = time.time()
        y = self._linear([(x, F.Ax), (a, F.Ba)], H, F.c1)
        self._rcache = {}                                   # x is no longer needed
        self._tick("output + LayerNorm", t0); t0 = time.time()
        hp = self._linear([(y, F.W1)], F.W1.shape[0], F.b1)
        sq = self._map(cc.EvalSquare, hp); del hp
        out = self._linear([(y, F.Ay), (sq, F.Bs)], F.Ay.shape[0], F.c2)
        self._tick("feed-forward + LayerNorm" + (" + classifier" if last else ""), t0)
        self._rcache = {}
        return out


# ----------------------------------------------------------------------------------------------- client
class Client:
    """The lawyer's device: plaintext embeddings, encryption, decryption. Holds the secret key."""

    def __init__(self, ctx: Context, net, lay: Layout):
        self.ctx, self.net, self.lay = ctx, net, lay

    @torch.no_grad()
    def embed(self, windows):
        return [self.net.embed(torch.tensor([w]))[0].double().numpy() for w in windows]

    def matrix(self, embs, batch):
        X = np.zeros((self.lay.T, embs[0].shape[1]))
        for i, s, L in batch: X[s:s + L] = embs[i]
        return X

    def encrypt(self, X):
        cc, pk = self.ctx.cc, self.ctx.keys.publicKey
        return [cc.Encrypt(pk, cc.MakeCKKSPackedPlaintext(v.tolist())) for v in self.lay.to_slots(X)]

    def decrypt(self, cts, n_out, batch):
        cc, sk = self.ctx.cc, self.ctx.keys.secretKey
        vecs = []
        for ct in cts:
            pt = cc.Decrypt(sk, ct); pt.SetLength(self.ctx.slots); vecs.append(np.array(pt.GetRealPackedValue()))
        Y = self.lay.from_slots(vecs, n_out)
        return [Y[s:s + L] for _, s, L in batch]
