"""Katip Mask Nano as a plain PyTorch module, rebuilt from the published int8 ONNX (f1k/katip-mask-nano).

The int8 weights are dequantized (w = scale * (q - zero_point)), so this float model is what the browser's
int8 model approximates. `NanoNet` takes the same weights and lets each non-linearity be swapped for an
FHE-friendly stand-in (see fhe_ops.py), which is how the encrypted variant is built and trained.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import onnx
import torch
from onnx import numpy_helper
from torch import nn

NANO_REPO = "f1k/katip-mask-nano"


def nano_dir() -> Path:
    from huggingface_hub import snapshot_download
    return Path(snapshot_download(NANO_REPO))


def dequantized_weights(onnx_file) -> dict[str, np.ndarray]:
    """Float weights from the int8 ONNX, keyed by HF BertForTokenClassification names."""
    m = onnx.load(str(onnx_file))
    init = {t.name: numpy_helper.to_array(t) for t in m.graph.initializer}
    deq = lambda base: (init[base + "_quantized"].astype(np.float32) - init[base + "_zero_point"].astype(np.float32)) * init[base + "_scale"]
    W = {k[2:]: v for k, v in init.items() if k.startswith("m.") and not k.endswith(("_scale", "_zero_point", "_quantized"))}
    for e in ("word", "token_type", "position"):
        W[f"bert.embeddings.{e}_embeddings.weight"] = deq(f"m.bert.embeddings.{e}_embeddings.weight")
    # MatMul weights appear in graph order: per layer Q, K, V, attention out, intermediate, output; then classifier.
    mm = [n.input[1].removesuffix("_quantized") for n in m.graph.node if n.op_type == "MatMulInteger"]
    names = []
    for l in range(2):
        p = f"bert.encoder.layer.{l}."
        names += [p + "attention.self.query", p + "attention.self.key", p + "attention.self.value",
                  p + "attention.output.dense", p + "intermediate.dense", p + "output.dense"]
    names.append("classifier")
    assert len(mm) == len(names), (len(mm), mm)
    for base, name in zip(mm, names):
        W[name + ".weight"] = deq(base).T.copy()        # ONNX stores x @ W; torch Linear stores W^T
    return W


class NanoNet(nn.Module):
    """2-layer BERT token classifier with pluggable non-linearities.

    ops: object with gelu(x), softmax(scores, mask), layernorm(x, ln_module) methods (fhe_ops.Exact by default).
    window: if set, each token attends only to tokens within +-window positions (local attention).
    """

    def __init__(self, vocab=16000, hidden=128, heads=2, inter=512, layers=2, maxpos=256, labels=3, ops=None, window=None):
        super().__init__()
        from fhe_ops import Exact
        self.ops = ops or Exact()
        self.window, self.heads, self.hidden = window, heads, hidden
        self.word = nn.Embedding(vocab, hidden); self.pos = nn.Embedding(maxpos, hidden); self.typ = nn.Embedding(2, hidden)
        self.emb_ln = nn.LayerNorm(hidden, eps=1e-12)
        self.layers = nn.ModuleList()
        for _ in range(layers):
            L = nn.Module()
            L.q, L.k, L.v, L.o = (nn.Linear(hidden, hidden) for _ in range(4))
            L.ln1 = nn.LayerNorm(hidden, eps=1e-12)
            L.f1, L.f2 = nn.Linear(hidden, inter), nn.Linear(inter, hidden)
            L.ln2 = nn.LayerNorm(hidden, eps=1e-12)
            self.layers.append(L)
        self.cls = nn.Linear(hidden, labels)

    # The client computes this part in plaintext: embedding lookup + first LayerNorm.
    def embed(self, ids):
        pos = torch.arange(ids.shape[1], device=ids.device)
        x = self.word(ids) + self.pos(pos)[None] + self.typ(torch.zeros_like(ids))
        return self.emb_ln(x)

    def attn_mask(self, mask):
        """[B, T, T] bool: which key each query may see (padding, and the local window if set)."""
        B, T = mask.shape
        m = mask[:, None, :].bool().expand(B, T, T)
        if self.window is not None:
            i = torch.arange(T, device=mask.device)
            m = m & ((i[None, :] - i[:, None]).abs() <= self.window)[None]
        return m

    # The server computes this part (encrypted in the FHE version).
    def encoder(self, x, mask):
        B, T, H = x.shape; h = self.heads; d = H // h
        am = self.attn_mask(mask)
        for L in self.layers:
            q = L.q(x).view(B, T, h, d).transpose(1, 2)
            k = L.k(x).view(B, T, h, d).transpose(1, 2)
            v = L.v(x).view(B, T, h, d).transpose(1, 2)
            s = q @ k.transpose(-1, -2) / d ** 0.5
            p = self.ops.softmax(s, am[:, None])
            a = (p @ v).transpose(1, 2).reshape(B, T, H)
            x = self.ops.layernorm(x + L.o(a), L.ln1)
            x = self.ops.layernorm(x + L.f2(self.ops.gelu(L.f1(x))), L.ln2)
        return self.cls(x)

    def forward(self, ids, mask):
        return self.encoder(self.embed(ids), mask)

    def load_hf(self, W: dict):
        t = lambda a: torch.tensor(np.asarray(a))
        sd = {"word.weight": W["bert.embeddings.word_embeddings.weight"], "pos.weight": W["bert.embeddings.position_embeddings.weight"],
              "typ.weight": W["bert.embeddings.token_type_embeddings.weight"],
              "emb_ln.weight": W["bert.embeddings.LayerNorm.weight"], "emb_ln.bias": W["bert.embeddings.LayerNorm.bias"],
              "cls.weight": W["classifier.weight"], "cls.bias": W["classifier.bias"]}
        for l in range(len(self.layers)):
            p = f"bert.encoder.layer.{l}."
            for ours, theirs in (("q", "attention.self.query"), ("k", "attention.self.key"), ("v", "attention.self.value"),
                                 ("o", "attention.output.dense"), ("ln1", "attention.output.LayerNorm"),
                                 ("f1", "intermediate.dense"), ("f2", "output.dense"), ("ln2", "output.LayerNorm")):
                for w in ("weight", "bias"):
                    sd[f"layers.{l}.{ours}.{w}"] = W[p + theirs + "." + w]
        self.load_state_dict({k: t(v) for k, v in sd.items()})
        return self


# Mean per-token standard deviation at each LayerNorm input, measured with the original Nano on training data
# (synthetic train + Wiki NER train). The FHE-friendly LayerNorm divides by these constants instead of the live value.
FIXED_SIGMA = {(0, "ln1"): 1.04, (0, "ln2"): 1.40, (1, "ln1"): 1.03, (1, "ln2"): 1.85}

def load_nano(ops=None, window=None) -> NanoNet:
    d = nano_dir()
    net = NanoNet(ops=ops, window=window).load_hf(dequantized_weights(d / "onnx" / "model_quantized.onnx")).eval()
    for (l, name), s in FIXED_SIGMA.items():
        getattr(net.layers[l], name).fixed_sigma = s
    return net


class TorchSession:
    """Drop-in for onnxruntime.InferenceSession inside katiplab.Tagger: runs a NanoNet instead."""

    def __init__(self, net):
        self.net = net

    def get_inputs(self):
        class I:  # noqa: E701
            def __init__(s, n): s.name = n
        return [I("input_ids"), I("attention_mask"), I("token_type_ids")]

    @torch.no_grad()
    def run(self, _out, feed):
        ids = torch.tensor(feed["input_ids"]); mask = torch.tensor(feed["attention_mask"])
        return [self.net(ids, mask).numpy()]
