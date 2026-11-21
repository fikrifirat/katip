"""Nano-FHE written with only the operations Belfort eML accepts (Linear, add, products of tensors).

Input: one window of T=64 tokens, already embedded on the device ([1, 64, 128]). eML takes one encrypted
input with a fixed shape, and every linear layer must fit in one ciphertext (32,768 values): the
feed-forward layer's 64 x 512 = 32,768 values sets T = 64. Attention is computed over the whole input with a
plaintext mask (second, unencrypted argument) that keeps +-16 neighbours inside each packed segment, which
is the same function as ckks_nano's local attention.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import torch
from typing import Annotated

from torch import nn

try:
    from belfort_ml import Secret
except ImportError:          # plaintext use without the Belfort SDK
    class Secret: pass

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parent), str(HERE.parent.parent)]

T = 64
WINDOW = 16


def lin(W, b=None):
    m = nn.Linear(W.shape[1], W.shape[0], bias=b is not None)
    with torch.no_grad():
        m.weight.copy_(torch.tensor(W, dtype=torch.float32))
        if b is not None: m.bias.copy_(torch.tensor(b, dtype=torch.float32))
    return m


class EmlNano(nn.Module):
    def __init__(self, folded, heads=2, T=T, window=WINDOW):
        super().__init__()
        self.heads = heads
        self.L = nn.ModuleList()
        for F in folded:
            m = nn.Module()
            m.q, m.k, m.v = lin(F.Wq, F.bq), lin(F.Wk, F.bk), lin(F.Wv, F.bv)
            m.ax, m.ba = lin(F.Ax, F.c1), lin(F.Ba)
            m.w1 = lin(F.W1, F.b1)
            m.ay, m.bs = lin(F.Ay, F.c2), lin(F.Bs)
            self.L.append(m)

    def forward(self, x: Annotated[torch.Tensor, Secret], mask: torch.Tensor):
        """x: [1, T, 128] encrypted embeddings. mask: [T, T] plaintext attention mask, 1/n_keys where a query may
        attend (same segment, within +-16) and 0 elsewhere. The mask only reveals segment lengths, which the
        server learns from the ciphertext layout anyway; it lets several short windows share one input exactly."""
        H = x.shape[-1]; d = H // self.heads
        for m in self.L:
            q, k, v = m.q(x), m.k(x), m.v(x)
            heads = []
            for h in range(self.heads):
                qh, kh, vh = q[..., h * d:(h + 1) * d], k[..., h * d:(h + 1) * d], v[..., h * d:(h + 1) * d]
                s = qh @ kh.transpose(-1, -2) + 1.0
                p = s * s * mask
                heads.append(p @ vh)
            a = torch.cat(heads, -1)
            y = m.ax(x) + m.ba(a)
            hp = m.w1(y)
            x = m.ay(y) + m.bs(hp * hp)
        return x                                # [1, T, 3] label scores


def segment_mask(lengths, T=T, window=WINDOW):
    """Block-diagonal local-attention mask for segments packed back to back in T rows."""
    M = np.zeros((T, T), dtype=np.float32); o = 0
    for L in lengths:
        i = np.arange(L)
        M[o:o + L, o:o + L] = (np.abs(i[None] - i[:, None]) <= window)
        o += L
    n = M.sum(1, keepdims=True); n[n == 0] = 1
    return M / n
