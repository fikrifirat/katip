"""Non-linearities for Nano: exact (plaintext reference) and FHE-friendly stand-ins.

CKKS, the FHE scheme used here, can only add and multiply. Anything else (GELU, softmax's exp and division,
LayerNorm's 1/sqrt) has to become a polynomial, and every multiplication uses up one "level" of the
ciphertext. The FHE-friendly variant therefore uses low-degree polynomials and moves normalisation
constants into the weights, and the model is retrained (distilled from Nano) to work with them.
"""
from __future__ import annotations

import torch
import torch.nn.functional as F


class Exact:
    name = "exact"
    def gelu(self, x): return F.gelu(x)
    def softmax(self, s, mask): return torch.softmax(s.masked_fill(~mask, -1e9), -1)
    def layernorm(self, x, ln): return ln(x)


class PolyFHE:
    """FHE-friendly: quadratic activation, polynomial attention, LayerNorm with a fixed scale.

    * gelu(x)   -> 0.1535 x^2 + 0.5 x + 0.0723      least-squares fit over Nano's FFN range (1 level)
    * softmax   -> (1 + s/c)^2 * mask / n_keys        "2Quad"-style attention, no exp, no division (1 level)
    * LayerNorm -> gamma * (x - mean(x)) / sigma + beta, with sigma a fixed constant per LayerNorm
                   (measured on training data with the original Nano), so it is linear and folds into weights
    """
    name = "poly"
    GELU = (0.1535, 0.5, 0.0723)
    def __init__(self, c_attn: float = 3.0):
        self.c_attn = c_attn
    def gelu(self, x):
        a, b, c = self.GELU
        return a * x * x + b * x + c
    def softmax(self, s, mask):
        p = (1 + s / self.c_attn) ** 2 * mask
        n = mask.sum(-1, keepdim=True).clamp(min=1)
        return p / n
    def layernorm(self, x, ln):
        sigma = getattr(ln, "fixed_sigma", 1.0)
        return ln.weight * (x - x.mean(-1, keepdim=True)) / sigma + ln.bias
