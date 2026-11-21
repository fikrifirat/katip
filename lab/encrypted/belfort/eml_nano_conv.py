"""Nano-FHE in the layout Belfort's compiler accepts: tokens along the width of a 1-D "image" ([1, C, T]).

Belfort's compiler (HEIR, belfort-ml 0.2.5) rejects an encrypted [T, 128] matrix times a weight matrix,
whatever T, but compiles 1x1 convolutions, depthwise convolutions and products of encrypted tensors (the CNN
toolbox). So every token-wise linear layer becomes a 1x1 convolution, and local attention (+-16 tokens) is
written out per offset r: shift the keys and values by r with a fixed depthwise convolution, multiply with the
queries, sum each head's channels with a 1x1 convolution, then (s + 1)^2 times the mask for that offset.
Same function as EmlNano and ckks_nano's local attention, computed differently.

Input: one encrypted tensor [1, 128 + 33, T]: the T embedded tokens, then the attention mask as 33 extra
channels (channel 128 + r + 16 holds mask[t, t + r]). eML takes a single encrypted input, so the mask rides
along encrypted; it only says where packed segments start and end.
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

H, WINDOW = 128, 16
R = 2 * WINDOW + 1


def conv1(W, b=None):
    m = nn.Conv1d(W.shape[1], W.shape[0], 1, bias=b is not None)
    with torch.no_grad():
        m.weight.copy_(torch.tensor(np.asarray(W), dtype=torch.float32)[..., None])
        if b is not None: m.bias.copy_(torch.tensor(np.asarray(b), dtype=torch.float32))
    return m


def select(rows, n_in):
    W = np.zeros((len(rows), n_in), dtype=np.float32)
    for i, r in enumerate(rows): W[i, r] = 1.0
    return conv1(W)


class EmlNanoConv(nn.Module):
    def __init__(self, folded, heads=2, window=WINDOW, merge_kv=False):
        super().__init__()
        self.window, d = window, H // heads
        C = H + 2 * window + 1
        self.emb = select(range(H), C)                                   # embeddings out of the input
        self.msk = nn.ModuleList(select([H + j] * heads, C) for j in range(2 * window + 1))   # mask_r per head
        hsum = np.zeros((heads, H), dtype=np.float32); hexp = np.zeros((H, heads), dtype=np.float32)
        for h in range(heads): hsum[h, h * d:(h + 1) * d] = 1; hexp[h * d:(h + 1) * d, h] = 1
        self.hsum, self.hexp = conv1(hsum), conv1(hexp)
        self.merge_kv = merge_kv
        nsh = 2 * H if merge_kv else H                                    # merged: keys and values shift together
        self.shift = nn.ModuleList()
        for j in range(2 * window + 1):                                   # output[t] = input[t + j - window]
            c = nn.Conv1d(nsh, nsh, 2 * window + 1, padding=window, groups=nsh, bias=False)
            with torch.no_grad(): c.weight.zero_(); c.weight[:, 0, j] = 1.0
            self.shift.append(c)
        self.L = nn.ModuleList()
        for F in folded:
            m = nn.Module()
            m.q, m.k, m.v = conv1(F.Wq, F.bq), conv1(F.Wk, F.bk), conv1(F.Wv, F.bv)
            m.kv = conv1(np.concatenate([F.Wk, F.Wv]), np.concatenate([F.bk, F.bv]))
            m.ax, m.ba = conv1(F.Ax, F.c1), conv1(F.Ba)
            m.w1 = conv1(F.W1, F.b1)
            m.ay, m.bs = conv1(F.Ay, F.c2), conv1(F.Bs)
            self.L.append(m)

    def forward(self, x: Annotated[torch.Tensor, Secret]):
        masks = [m(x) for m in self.msk]                 # [1, heads, T] each
        h = self.emb(x)
        for m in self.L:
            q = m.q(h)
            if self.merge_kv: kv = m.kv(h)
            else: k, v = m.k(h), m.v(h)
            a = None
            for j, sh in enumerate(self.shift):
                if self.merge_kv:
                    kvs = sh(kv); ks, vs = kvs[:, :H], kvs[:, H:]
                else:
                    ks, vs = sh(k), sh(v)
                s = self.hsum(q * ks) + 1.0
                p = s * s * masks[j]
                t = self.hexp(p) * vs
                a = t if a is None else a + t
            y = m.ax(h) + m.ba(a)
            hp = m.w1(y)
            h = m.ay(y) + m.bs(hp * hp)
        return h                                         # [1, 3, T] label scores


def pack(x, mask, window=WINDOW):
    """x [T, 128] embeddings, mask [T, T] (segment_mask) -> encrypted input [1, 128 + 2w + 1, T]."""
    T = x.shape[0]; out = np.zeros((H + 2 * window + 1, T), dtype=np.float32)
    out[:H] = x.T
    for j in range(2 * window + 1):
        r = j - window
        for t in range(T):
            if 0 <= t + r < T: out[H + j, t] = mask[t, t + r]
    return out[None]
