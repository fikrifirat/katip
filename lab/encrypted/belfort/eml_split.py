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


class ModelQ(nn.Module):
    """Layer 0 queries, keys, values from the embeddings: u (128 ch) -> [q0; k0; v0] (384 ch)."""
    def __init__(self, F0, F1):
        super().__init__()
        self.qkv = conv1(np.concatenate([F0.Wq, F0.Wk, F0.Wv]), np.concatenate([F0.bq, F0.bk, F0.bv]))

    def forward(self, z: Annotated[torch.Tensor, Secret]):
        return self.qkv(z)


class ModelF(nn.Module):
    """Layer 1 after attention, folded with the classifier: [h1; a1] (256 ch) -> label scores (3 ch)."""
    def __init__(self, F0, F1):
        super().__init__()
        self.y = conv1(blocks(2 * H, [(F1.Ax, 0), (F1.Ba, 1)]), F1.c1)
        self.w1 = conv1(F1.W1, F1.b1); self.ay = conv1(F1.Ay, F1.c2); self.bs = conv1(F1.Bs)

    def forward(self, z: Annotated[torch.Tensor, Secret]):
        y = self.y(z); hp = self.w1(y)
        return self.ay(y) + self.bs(hp * hp)


class ModelB(nn.Module):
    def __init__(self, F0, F1):
        super().__init__()
        self.y = conv1(blocks(2 * H, [(F0.Ax, 0), (F0.Ba, 1)]), F0.c1)
        self.w1 = conv1(F0.W1, F0.b1); self.ay = conv1(F0.Ay, F0.c2); self.bs = conv1(F0.Bs)
        self.qkv = conv1(np.concatenate([F1.Wq, F1.Wk, F1.Wv]), np.concatenate([F1.bq, F1.bk, F1.bv]))

    def forward(self, z: Annotated[torch.Tensor, Secret]):
        y = self.y(z); hp = self.w1(y)
        h1 = self.ay(y) + self.bs(hp * hp)
        return torch.cat([h1, self.qkv(h1)], 1)


def attention(qkv, mask, heads=2):
    """Client side, plaintext. qkv [3H, T] -> a [H, T]; same as EmlNano: (q.k + 1)^2 * mask, then times v."""
    q, k, v = qkv[:H].T, qkv[H:2 * H].T, qkv[2 * H:].T; d = H // heads; out = []
    for h in range(heads):
        s = q[:, h * d:(h + 1) * d] @ k[:, h * d:(h + 1) * d].T + 1.0
        out.append((s * s * mask) @ v[:, h * d:(h + 1) * d])
    return np.concatenate(out, 1).T


def forward_split(callQ, callB, callF, x, mask):
    """x [T, 128] embeddings -> label scores [T, 3]. Each call maps an input [1, C, T] to an output [C', T]."""
    a0 = attention(callQ(x.T[None].astype(np.float32)), mask)
    o = callB(np.concatenate([x.T, a0])[None].astype(np.float32))
    h1, qkv1 = o[:H], o[H:]
    a1 = attention(qkv1, mask)
    return callF(np.concatenate([h1, a1])[None].astype(np.float32)).T
