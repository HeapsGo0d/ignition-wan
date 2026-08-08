#!/usr/bin/env python3
"""Point the shipped workflows at the model quant that actually landed on disk.

The workflows are authored against the int8 profile. Selecting h3_fp8_bundle
downloads a different diffusion model, and without this step ComfyUI would show
a missing-model dialog and offer to download the int8 file to the user's own PC.

The rule is deliberately narrow: if the file a loader asks for is present, do
nothing. Only when it is missing and exactly one interchangeable sibling is
present do we repoint. That way a pod with both variants downloaded keeps
whatever the user chose in the UI.

Substitution is a recursive walk over every string in the document, which
matters more than it looks: in these workflows the value that actually drives
UNETLoader lives in the PARENT subgraph instance's widgets_values, not in the
UNETLoader node — its own widget value is dead text overridden by a link. The
same walk also fixes properties.models, which is what the frontend's
"Missing Models" dialog reads.

Run: python3 scripts/retarget_workflows.py [--models-root DIR] [--workflows DIR]
"""

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from download_huggingface_simple import H3_MODELS  # noqa: E402

# Registry keys that are interchangeable — same role, different quantization.
# Order is preference order when more than one sibling is present.
ROLES = {
    "diffusion model (fl2va)": ["h3_fl2va_int8", "h3_fl2va_fp8"],
    "diffusion model (ref2va)": ["h3_ref2va_int8", "h3_ref2va_fp8"],
    "text encoder": ["h3_text_encoder_nvfp4", "h3_text_encoder_int8"],
}


def log(msg):
    print(f"[retarget] {msg}", flush=True)


def substitute(obj, pattern, mapping):
    """Recursively rewrite strings, returning (new_obj, n_replacements).

    Substrings are replaced, not just whole values, so the "Model Links"
    MarkdownNote stops contradicting the graph. One regex pass with an
    alternation of all keys means a replacement can never be re-replaced.
    """
    if isinstance(obj, str):
        new, n = pattern.subn(lambda m: mapping[m.group(0)], obj)
        return new, n
    if isinstance(obj, list):
        out, n = [], 0
        for v in obj:
            nv, c = substitute(v, pattern, mapping)
            out.append(nv)
            n += c
        return out, n
    if isinstance(obj, dict):
        out, n = {}, 0
        for k, v in obj.items():
            nv, c = substitute(v, pattern, mapping)
            out[k] = nv
            n += c
        return out, n
    return obj, 0


def build_mapping(models_root: Path):
    """Map absent-file strings -> the present sibling, for filenames and URLs."""
    mapping = {}
    for role, keys in ROLES.items():
        entries = [H3_MODELS[k] for k in keys]
        present = [e for e in entries
                   if (models_root / e["subdir"] / e["filename"]).is_file()]
        if not present:
            log(f"{role}: none on disk — leaving workflows untouched")
            continue
        if len(present) == len(entries):
            log(f"{role}: all variants on disk — leaving the workflow's choice alone")
            continue
        winner = present[0]
        for e in entries:
            if e["filename"] == winner["filename"]:
                continue
            mapping[e["filename"]] = winner["filename"]
            mapping[e["url"]] = winner["url"]
        log(f"{role}: using {winner['filename']}")
    return mapping


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--models-root", default="/workspace/ComfyUI/models")
    ap.add_argument("--workflows",
                    default="/workspace/ComfyUI/user/default/workflows")
    args = ap.parse_args()

    models_root = Path(args.models_root)
    workflows = Path(args.workflows)

    if not workflows.is_dir():
        log(f"workflows dir not found: {workflows} — nothing to do")
        return 0

    mapping = build_mapping(models_root)
    if not mapping:
        log("no retargeting needed")
        return 0

    # Longest key first so a URL is matched before the bare filename inside it.
    pattern = re.compile("|".join(re.escape(k) for k in
                                  sorted(mapping, key=len, reverse=True)))

    for wf in sorted(workflows.glob("*.json")):
        try:
            doc = json.loads(wf.read_text())
        except json.JSONDecodeError as exc:
            log(f"skipping {wf.name}: {exc}")
            continue
        new, changed = substitute(doc, pattern, mapping)
        if changed:
            wf.write_text(json.dumps(new, indent=2, ensure_ascii=False) + "\n")
            log(f"{wf.name}: {changed} reference(s) repointed")
        else:
            log(f"{wf.name}: already correct")
    return 0


if __name__ == "__main__":
    sys.exit(main())
