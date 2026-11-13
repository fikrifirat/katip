Katip Kalkan masks Turkish personal data (KVKK) on your computer before Claude reads a document.
Originals and the name map never leave the device.

**Claude Desktop:** download `katip-kalkan.mcpb` below and double-click it (or Settings → Extensions →
Install). Pick the folder that holds your client files.

**Claude Code / Cowork:**

    claude plugin marketplace add fikrifirat/katip
    claude plugin install katip-kalkan@katip

Needs Python 3.10+. With [uv](https://docs.astral.sh/uv/) installed, Katip fetches its model runtime
and encryption library on first start; without it, it runs on rules only.

Bundled model: Katip Mask Nano · tr v1.1 (CC BY-NC 4.0). Code: AGPL-3.0, commercial licence on request.
Pre-release for testing with synthetic or public documents. See connector/README.md and DESIGN.md.
