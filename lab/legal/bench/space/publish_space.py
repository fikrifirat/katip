"""Publish the KVKK-Bench leaderboard to the Hugging Face Space f1k/kvkk-bench.

  huggingface-cli login            # once, with a write token for the f1k account
  python lab/legal/bench/space/publish_space.py [--repo f1k/kvkk-bench]

Uploads only the app, its README and requirements and the score files
(results/*.json). No benchmark data from lab/data is uploaded.
"""
import argparse, shutil, tempfile
from pathlib import Path
from huggingface_hub import HfApi

HERE = Path(__file__).resolve().parent
ap = argparse.ArgumentParser(); ap.add_argument("--repo", default="f1k/kvkk-bench"); a = ap.parse_args()
with tempfile.TemporaryDirectory() as d:
    d = Path(d)
    for f in ("app.py", "README.md", "requirements.txt"): shutil.copy(HERE / f, d / f)
    for sub in ("results",):
        (d / sub).mkdir()
        import app   # only publish rows the leaderboard shows; internal references (e.g. berturk-v1, tiny v1) stay in the repo
        for f in (HERE.parent / sub).glob("*.json"):
            if f.stem in app.SYSTEMS: shutil.copy(f, d / sub / f.name)
    print("uploading:", sorted(str(p.relative_to(d)) for p in d.rglob("*") if p.is_file()))
    api = HfApi()
    api.create_repo(a.repo, repo_type="space", space_sdk="gradio", exist_ok=True)
    api.upload_folder(folder_path=str(d), repo_id=a.repo, repo_type="space", commit_message="KVKK-Bench leaderboard v0.1 preview")
print(f"done: https://huggingface.co/spaces/{a.repo}")
