"""One-time move of the Hugging Face repos to the Katip Mask names. Safe to run again.

  python hf/rename_to_katip_mask.py [hf-username]

  f1k/katip-tr-name-tagger-tiny  ->  f1k/katip-mask-nano   (v1 stays at the tag v1.0)
  f1k/katip-tr-pii-berturk       ->  f1k/katip-mask-base   (tagged v2.0)
  spaces/f1k/katip-yerel         ->  spaces/f1k/katip-mask

Hugging Face keeps redirects from the old names, so existing links and from_pretrained() calls keep working.
"""
import sys

from huggingface_hub import HfApi

u = sys.argv[1] if len(sys.argv) > 1 else "f1k"
api = HfApi()
print("signed in as", api.whoami()["name"])

MOVES = [
    (f"{u}/katip-tr-name-tagger-tiny", f"{u}/katip-mask-nano", "model", "v1.0", "Katip Mask Nano tr v1: Turkish names"),
    (f"{u}/katip-tr-pii-berturk", f"{u}/katip-mask-base", "model", "v2.0", "Katip Mask Base tr v2: BERTurk + real Turkish text"),
    (f"{u}/katip-yerel", f"{u}/katip-mask", "space", None, None),
]


def real_id(repo_id, repo_type):
    """The repo's current name, or None. Old names redirect, so ask for the id the Hub answers with."""
    try:
        return api.repo_info(repo_id, repo_type=repo_type).id
    except Exception:
        return None


for old, new, kind, tag, msg in MOVES:
    if real_id(new, kind) == new:
        print(f"ok    {new} already exists")
    elif real_id(old, kind) == old:
        api.move_repo(from_id=old, to_id=new, repo_type=kind)
        print(f"moved {old} -> {new}")
    else:
        sys.exit(f"neither {old} nor {new} found ({kind})")
    if tag:
        tags = {t.name for t in api.list_repo_refs(new, repo_type=kind).tags}
        if tag in tags:
            print(f"ok    {new} has tag {tag}")
        else:
            api.create_tag(new, tag=tag, tag_message=msg, repo_type=kind)
            print(f"tag   {new} {tag}")
