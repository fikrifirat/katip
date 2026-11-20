"""Take 3, split design: Belfort runs every weight layer encrypted; the client does the small attention mixing.

Why: Belfort's compiler handles 1x1 convolutions and squares quickly, but local attention written out in
compilable operations (~1,400 ops) did not finish compiling in 45 minutes. So the model is cut at the
attention step, the standard "client-aided" FHE pattern: the server computes q, k, v and the feed-forward
layers on ciphertexts, the client (who owns the data and the secret key) decrypts q, k, v, mixes them with
the attention weights in plaintext and sends the result back encrypted. The server never sees plaintext.
The server does ~95% of the model's multiply-adds; the client does attention (~5%) and 3 round trips per call.

Three eML models, all [1, C, 64] with tokens along the width (a model reading two branches from one input
failed in Belfort's compiler, so they stay separate):
  Q: u        (128 ch) -> [q0; k0; v0] (384 ch)
  B: [u; a0]  (256 ch) -> [h1 = layer 0 output (128 ch); q1; k1; v1 (384 ch)]
  F: [h1; a1] (256 ch) -> label scores (3 ch)
Per call: Q -> attention 0 (client) -> B -> attention 1 (client) -> F.
"""
from __future__ import annotations

from typing import Annotated

import numpy as np
import torch
from torch import nn

try:
    from belfort_ml import Secret
except ImportError:
    class Secret: pass

H = 128


def conv1(W, b=None):
    m = nn.Conv1d(W.shape[1], W.shape[0], 1, bias=b is not None)
    with torch.no_grad():
        m.weight.copy_(torch.tensor(np.asarray(W), dtype=torch.float32)[..., None])
        if b is not None: m.bias.copy_(torch.tensor(np.asarray(b), dtype=torch.float32))
    return m


def blocks(cin, parts):
    """1x1 conv over the concatenated input: parts = [(W [out, 128], input block index), ...] summed, plus bias."""
    W = np.zeros((parts[0][0].shape[0], cin), dtype=np.float32)
    for w, i in parts: W[:, i * H:(i + 1) * H] += w
    return W


# Scales: every encrypted value is kept within about +-2. Belfort's CKKS programs lose values far outside
# that (the first run's last stage saw squares up to ~865 and returned scores off by up to 44). Each model takes
# its input divided by s_in and returns its output divided by s_out; the scales inside are folded into the weights.
SCALES = {"Q": dict(s_in=4, s_out=4),
          "B": dict(s_in=4, s_y=4, s_hp=4, s_out=16),
          "F": dict(s_in=16, s_y=16, s_hp=32, s_out=64)}


class ModelQ(nn.Module):
    """Layer 0 queries, keys, values from the embeddings: u (128 ch) -> [q0; k0; v0] (384 ch)."""
    def __init__(self, F0, F1, s_in=1, s_out=1):
        super().__init__()
        W = np.concatenate([F0.Wq, F0.Wk, F0.Wv]); b = np.concatenate([F0.bq, F0.bk, F0.bv])
        self.qkv = conv1(W * s_in / s_out, b / s_out)

    def forward(self, z: Annotated[torch.Tensor, Secret]):
        return self.qkv(z)


def _ff(Fl, cin_parts, s_in, s_y, s_hp, s_out):
    """y = A z + c1, hp = W1 y + b1, out = Ay y + c2 + Bs hp^2, with z = s_in z', y = s_y y', hp = s_hp hp', out = s_out out'."""
    y = conv1(blocks(2 * H, cin_parts) * s_in / s_y, Fl.c1 / s_y)
    w1 = conv1(Fl.W1 * s_y / s_hp, Fl.b1 / s_hp)
    ay = conv1(Fl.Ay * s_y / s_out, Fl.c2 / s_out); bs = conv1(Fl.Bs * s_hp ** 2 / s_out)
    return y, w1, ay, bs


class ModelF(nn.Module):
    """Layer 1 after attention, folded with the classifier: [h1; a1] (256 ch) -> label scores (3 ch)."""
    def __init__(self, F0, F1, s_in=1, s_y=1, s_hp=1, s_out=1):
        super().__init__()
        self.y, self.w1, self.ay, self.bs = _ff(F1, [(F1.Ax, 0), (F1.Ba, 1)], s_in, s_y, s_hp, s_out)

    def forward(self, z: Annotated[torch.Tensor, Secret]):
        y = self.y(z); hp = self.w1(y)
        return self.ay(y) + self.bs(hp * hp)


class ModelB(nn.Module):
    """Layer 0 after attention, then layer 1's q, k, v: [u; a0] (256 ch) -> [h1; q1; k1; v1] (512 ch)."""
    def __init__(self, F0, F1, s_in=1, s_y=1, s_hp=1, s_out=1):
        super().__init__()
        self.y, self.w1, self.ay, self.bs = _ff(F0, [(F0.Ax, 0), (F0.Ba, 1)], s_in, s_y, s_hp, s_out)
        # h1 = s_out h1', and the q, k, v outputs are divided by s_out too: weights unchanged, biases / s_out
        self.qkv = conv1(np.concatenate([F1.Wq, F1.Wk, F1.Wv]), np.concatenate([F1.bq, F1.bk, F1.bv]) / s_out)

    def forward(self, z: Annotated[torch.Tensor, Secret]):
        y = self.y(z); hp = self.w1(y)
        h1 = self.ay(y) + self.bs(hp * hp)
        return torch.cat([h1, self.qkv(h1)], 1)


def build(F, scaled=True):
    sc = SCALES if scaled else {k: {} for k in SCALES}
    return {"Q": ModelQ(*F, **sc["Q"]).eval(), "B": ModelB(*F, **sc["B"]).eval(), "F": ModelF(*F, **sc["F"]).eval()}


def attention(qkv, mask, heads=2):
    """Client side, plaintext. qkv [3H, T] -> a [H, T]; same as EmlNano: (q.k + 1)^2 * mask, then times v."""
    q, k, v = qkv[:H].T, qkv[H:2 * H].T, qkv[2 * H:].T; d = H // heads; out = []
    for h in range(heads):
        s = q[:, h * d:(h + 1) * d] @ k[:, h * d:(h + 1) * d].T + 1.0
        out.append((s * s * mask) @ v[:, h * d:(h + 1) * d])
    return np.concatenate(out, 1).T


def forward_split(callQ, callB, callF, x, mask, scaled=True):
    """x [T, 128] embeddings -> label scores [T, 3]. Each call maps an input [1, C, T] to an output [C', T].
    The client divides each input and multiplies each output by that model's scales."""
    S = SCALES if scaled else {k: {"s_in": 1, "s_out": 1} for k in SCALES}
    f32 = lambda a: np.asarray(a, dtype=np.float32)
    q0 = callQ(f32(x.T[None] / S["Q"]["s_in"])) * S["Q"]["s_out"]
    a0 = attention(q0, mask)
    o = callB(f32(np.concatenate([x.T, a0])[None] / S["B"]["s_in"])) * S["B"]["s_out"]
    h1, qkv1 = o[:H], o[H:]
    a1 = attention(qkv1, mask)
    return (callF(f32(np.concatenate([h1, a1])[None] / S["F"]["s_in"])) * S["F"]["s_out"]).T
