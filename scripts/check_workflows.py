#!/usr/bin/env python3
"""Build-time consistency check for the workflow / registry / Dockerfile triangle.

Every load-blocking bug this repo has shipped was a mismatch between what a
workflow JSON names, what the download registry fetches, and what the image
installs. Each one was found by hand, on a pod, after a 78-minute build.

This fails the build instead. Two invariants:

  1. Every model filename a workflow references resolves to a registry entry,
     and the registry writes it to the directory the workflow expects.
  2. Every node type resolves to ComfyUI core. This image installs no custom
     node packs, so the allowlist below is the complete set. Adding a type
     means confirming it is core (or adding the pack to the Dockerfile).

Run: python3 scripts/check_workflows.py
"""

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from download_huggingface_simple import H3_MODELS  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
WORKFLOWS = REPO / "workflows"

# Every node type used by the shipped workflows. All ComfyUI core — verified
# against comfy_extras/ and nodes.py. Keep sorted; add only after checking that
# the type is genuinely core, since the image installs no custom node packs.
ALLOWED_NODE_TYPES = {
    "BasicGuider",              # comfy_extras/nodes_custom_sampler.py
    "BasicScheduler",           # comfy_extras/nodes_custom_sampler.py
    "CLIPLoader",               # nodes.py
    "ComfyMathExpression",      # comfy_extras/nodes_math.py       (core since 2026)
    "CreateVideo",              # comfy_extras/nodes_video.py
    "GetImageSize",             # comfy_extras/nodes_images.py
    "ImageScaleToTotalPixels",  # comfy_extras/nodes_post_processing.py
    "KSamplerSelect",           # comfy_extras/nodes_custom_sampler.py
    "LoadImage",                # nodes.py
    "LoraLoaderModelOnly",      # nodes.py
    "MarkdownNote",             # frontend
    "MiniMaxH3ImageToVideo",    # comfy_extras/nodes_minimax_h3.py
    "PrimitiveFloat",           # comfy_extras/nodes_primitive.py
    "RandomNoise",              # comfy_extras/nodes_custom_sampler.py
    "ResolutionSelector",       # comfy_extras/nodes_resolution.py (core since 2026)
    "SamplerCustomAdvanced",    # comfy_extras/nodes_custom_sampler.py
    "SaveVideo",                # comfy_extras/nodes_video.py
    "UNETLoader",               # nodes.py
    "VAEDecode",                # nodes.py
    "VAEDecodeAudio",           # comfy_extras/nodes_audio.py
    "VAELoader",                # nodes.py
}

# Non-model .safetensors-ish references that are legitimately absent from the
# registry (none today; kept so the failure mode is an explicit edit).
ALLOWED_UNREGISTERED = set()

URL_RE = re.compile(r"https://[\w./-]+\.safetensors")
SUBGRAPH_ID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-", re.I)

# filename -> expected subdir / canonical download URL, from the registry
REGISTRY = {e["filename"]: e["subdir"] for e in H3_MODELS.values()}
REGISTRY_URLS = {e["filename"]: e["url"] for e in H3_MODELS.values()}


def iter_nodes(doc):
    """Yield (context, node) for top-level nodes and every subgraph definition."""
    for n in doc.get("nodes", []):
        yield "root", n
    for sg in doc.get("definitions", {}).get("subgraphs", []):
        label = f"subgraph {sg.get('name') or sg.get('id')}"
        for n in sg.get("nodes", []):
            yield label, n


def check(path):
    errors = []
    doc = json.loads(path.read_text())

    # --- 1. node types ---
    for ctx, node in iter_nodes(doc):
        ntype = node.get("type", "")
        # A subgraph instance node's "type" is the subgraph UUID, not a node class.
        if SUBGRAPH_ID_RE.match(ntype):
            continue
        if ntype not in ALLOWED_NODE_TYPES:
            errors.append(
                f"node type {ntype!r} (id {node.get('id')}, {ctx}) is not in "
                "ALLOWED_NODE_TYPES — confirm it is ComfyUI core, or add the "
                "providing pack to the Dockerfile"
            )
        pack = (node.get("properties") or {}).get("cnr_id")
        if pack and pack != "comfy-core":
            errors.append(
                f"node {ntype} (id {node.get('id')}, {ctx}) declares cnr_id "
                f"{pack!r} — this image installs no custom node packs"
            )

    # --- 2. model references ---
    text = path.read_text()

    # 2a. URLs (properties.models entries and the Model Links note) must point
    #     at exactly the file the registry downloads — not a different repo.
    for url in sorted(set(URL_RE.findall(text))):
        base = url.rsplit("/", 1)[-1]
        if base not in REGISTRY:
            errors.append(f"URL {url} names {base!r}, which is not in H3_MODELS")
        elif url != REGISTRY_URLS[base]:
            errors.append(
                f"URL for {base!r} is {url}, but the registry downloads it from "
                f"{REGISTRY_URLS[base]} — the pod would fetch a different file"
            )

    # 2b. Loader values (widget strings). A bare filename only resolves if the
    #     registry writes the file to that model type's root; a nested path must
    #     match the registry subdir exactly. This is the bug that broke
    #     feature/10eros — loras/ltx23/<name> on disk vs a bare name in the graph.
    for ctx, node in iter_nodes(doc):
        for value in node.get("widgets_values") or []:
            if not isinstance(value, str) or not value.endswith(".safetensors"):
                continue
            base = value.rsplit("/", 1)[-1]
            if base in ALLOWED_UNREGISTERED:
                continue
            if base not in REGISTRY:
                errors.append(
                    f"{node.get('type')} (id {node.get('id')}, {ctx}) loads "
                    f"{value!r}, which has no entry in H3_MODELS — the pod will "
                    "show a missing-model dialog"
                )
                continue
            prefix = value[: -len(base)].strip("/")
            if prefix:
                errors.append(
                    f"{node.get('type')} (id {node.get('id')}, {ctx}) loads "
                    f"{value!r}, but the registry writes {base!r} to "
                    f"{REGISTRY[base]}/ root — ComfyUI will not resolve the "
                    "nested prefix"
                )
    return errors


def main():
    workflows = [Path(a) for a in sys.argv[1:]] or sorted(WORKFLOWS.glob("*.json"))
    if not workflows:
        print(f"FAIL: no workflows found in {WORKFLOWS}")
        return 1

    total = 0
    for wf in workflows:
        errors = check(wf)
        total += len(errors)
        if errors:
            print(f"FAIL {wf.name}")
            for e in errors:
                print(f"  • {e}")
        else:
            print(f"ok   {wf.name}")

    if total:
        print(f"\n{total} problem(s) found.")
        return 1
    print(f"\n{len(workflows)} workflow(s) OK.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
