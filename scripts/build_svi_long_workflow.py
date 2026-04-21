#!/usr/bin/env python3
"""Build workflows/i2v_svi_long.json — clean baseline long-form SVI workflow.

Source template: workflows/i2v_svi_4chunk.json (known-good 4-chunk WAN 2.2 SVI Pro graph).

Transformations applied to template:
  1. Drop PathchSageAttentionKJ nodes (12, 16). Reroute LoRA -> ModelSamplingSD3 directly.
  2. Replace ImageBatch nodes (60, 61, 62) with ImageBatchExtendWithOverlap
     (overlap=4, overlap_side=new, overlap_mode=linear_blend) for crossfade seams.
  3. High-noise KSamplers (21, 31, 41, 51) get fixed seeds 1001/1002/1003/1004.
  4. Node titles added to every chunk block + key knobs for self-documentation.
  5. Link IDs renumbered sequentially; integrity verified.

Also runnable as:
    python3 scripts/build_svi_long_workflow.py --verify workflows/i2v_svi_long.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SAGE_NODES = (12, 16)
IMAGEBATCH_NODES = (60, 61, 62)
HIGH_KSAMPLER_SEEDS = {21: 1001, 31: 1002, 41: 1003, 51: 1004}

NODE_TITLES = {
    1: "Start image  (identity anchor)",
    2: "CLIP  —  umt5_xxl",
    3: "Prompt  (shared across all chunks)",
    4: "Negative  (shared across all chunks)",
    5: "VAE  —  wan_2.1",
    10: "UNet  —  high noise",
    14: "UNet  —  low noise",
    11: "LoRA  —  SVI Pro high  v2.0",
    15: "LoRA  —  SVI Pro low  v2.0",
    13: "ModelSamplingSD3 high  —  SHIFT (3-8, default 5)",
    17: "ModelSamplingSD3 low   —  SHIFT (3-8, default 5)",
    74: "VAEEncode  ->  anchor_samples (shared to all chunks)",
    20: "Chunk 1  —  SVIPro  (length=81, motion_latent_count=1)",
    21: "Chunk 1  —  KSampler high  —  SEED 1001  —  CFG (3-6, default 4)",
    22: "Chunk 1  —  KSampler low",
    23: "Chunk 1  —  VAEDecode",
    30: "Chunk 2  —  SVIPro  (prev_samples = C1 low)",
    31: "Chunk 2  —  KSampler high  —  SEED 1002",
    32: "Chunk 2  —  KSampler low",
    33: "Chunk 2  —  VAEDecode",
    40: "Chunk 3  —  SVIPro  (prev_samples = C2 low)",
    41: "Chunk 3  —  KSampler high  —  SEED 1003",
    42: "Chunk 3  —  KSampler low",
    43: "Chunk 3  —  VAEDecode",
    50: "Chunk 4  —  SVIPro  (prev_samples = C3 low)",
    51: "Chunk 4  —  KSampler high  —  SEED 1004",
    52: "Chunk 4  —  KSampler low",
    53: "Chunk 4  —  VAEDecode",
    60: "Seam C1->C2  (overlap=4, linear_blend)",
    61: "Seam ->C3   (overlap=4, linear_blend)",
    62: "Seam ->C4   (overlap=4, linear_blend)",
    70: "VHS_VideoCombine  @  16 fps",
}


def build(template_path: Path, output_path: Path) -> dict:
    wf = json.loads(template_path.read_text())
    nodes = wf["nodes"]
    links = wf["links"]

    # --- 1. Drop PathchSageAttentionKJ nodes (bypass them in the MODEL chain) ---
    # Template wiring: LoRA_high(11) --link5--> Sage(12) --link7--> ModelSamplingSD3(13)
    #                  LoRA_low(15)  --link6--> Sage(16) --link8--> ModelSamplingSD3(17)
    # Rewrite link 7 to originate from node 11; link 8 from node 15. Drop links 5/6.
    for lk in links:
        if lk[0] == 7:
            lk[1], lk[2] = 11, 0
        elif lk[0] == 8:
            lk[1], lk[2] = 15, 0
    links[:] = [lk for lk in links if lk[0] not in (5, 6)]
    nodes[:] = [n for n in nodes if n["id"] not in SAGE_NODES]
    for n in nodes:
        if n["id"] == 11:
            n["outputs"][0]["links"] = [7]
        elif n["id"] == 15:
            n["outputs"][0]["links"] = [8]

    # --- 2. ImageBatch -> ImageBatchExtendWithOverlap ---
    for n in nodes:
        if n["id"] in IMAGEBATCH_NODES and n["type"] == "ImageBatch":
            n["type"] = "ImageBatchExtendWithOverlap"
            n["properties"]["Node name for S&R"] = "ImageBatchExtendWithOverlap"
            n["widgets_values"] = [4, "new", "linear_blend"]
            for inp in n["inputs"]:
                if inp["name"] == "image1":
                    inp["name"] = "source_images"
                elif inp["name"] == "image2":
                    inp["name"] = "new_images"
            existing_outgoing = n["outputs"][0]["links"] or []
            n["outputs"] = [
                {"name": "source_images",   "type": "IMAGE", "links": [],               "slot_index": 0},
                {"name": "start_images",    "type": "IMAGE", "links": [],               "slot_index": 1},
                {"name": "extended_images", "type": "IMAGE", "links": existing_outgoing, "slot_index": 2},
            ]
    # Each original outgoing link from 60/61/62 was on slot 0; it is now on slot 2.
    # Links 68 (60->61), 70 (61->62), 72 (62->70) are those outgoing edges.
    for lk in links:
        if lk[0] in (68, 70, 72):
            lk[2] = 2  # source slot index

    # --- 3. Fixed seeds on high-noise KSamplers ---
    # KSamplerAdvanced widgets_values layout:
    #   [add_noise, seed, control_after_generate, steps, cfg,
    #    sampler, scheduler, start_at_step, end_at_step, return_with_leftover_noise]
    for n in nodes:
        if n["id"] in HIGH_KSAMPLER_SEEDS:
            n["widgets_values"][1] = HIGH_KSAMPLER_SEEDS[n["id"]]
            n["widgets_values"][2] = "fixed"

    # --- 4. Titles ---
    for n in nodes:
        if n["id"] in NODE_TITLES:
            n["title"] = NODE_TITLES[n["id"]]

    # --- Rename the output video file so it does not clash with the old workflow ---
    for n in nodes:
        if n["id"] == 70 and n["type"] == "VHS_VideoCombine":
            n["widgets_values"][2] = "video/WAN_SVI_Long"

    # --- 5. Renumber link IDs sequentially; remap all references ---
    old_to_new: dict[int, int] = {}
    remapped_links = []
    for new_id, lk in enumerate(links, start=1):
        old_to_new[lk[0]] = new_id
        new_lk = list(lk)
        new_lk[0] = new_id
        remapped_links.append(new_lk)
    links[:] = remapped_links

    for n in nodes:
        for inp in n.get("inputs", []) or []:
            if inp.get("link") in old_to_new:
                inp["link"] = old_to_new[inp["link"]]
        for out in n.get("outputs", []) or []:
            out["links"] = [old_to_new[l] for l in (out.get("links") or []) if l in old_to_new]

    wf["last_link_id"] = len(links)
    wf["last_node_id"] = max(n["id"] for n in nodes)

    output_path.write_text(json.dumps(wf, indent=2) + "\n")
    return wf


def verify(path: Path) -> bool:
    wf = json.loads(path.read_text())
    nodes = wf["nodes"]
    links = wf["links"]
    node_ids = {n["id"] for n in nodes}
    link_ids = [lk[0] for lk in links]
    link_id_set = set(link_ids)
    errors: list[str] = []

    if len({n["id"] for n in nodes}) != len(nodes):
        errors.append("duplicate node IDs")
    if len(link_id_set) != len(link_ids):
        errors.append("duplicate link IDs")

    for lk in links:
        lid, src_node, src_slot, tgt_node, tgt_slot, _ltype = lk
        if src_node not in node_ids:
            errors.append(f"link {lid}: src node {src_node} missing")
        if tgt_node not in node_ids:
            errors.append(f"link {lid}: tgt node {tgt_node} missing")

    for n in nodes:
        for inp in n.get("inputs", []) or []:
            lid = inp.get("link")
            if lid is not None and lid not in link_id_set:
                errors.append(f"node {n['id']} input '{inp['name']}' -> missing link {lid}")
        for out in n.get("outputs", []) or []:
            for lid in out.get("links") or []:
                if lid not in link_id_set:
                    errors.append(f"node {n['id']} output '{out['name']}' -> missing link {lid}")

    # Chunk-chain sanity: each WanImageToVideoSVIPro after chunk 1 must have prev_samples wired.
    svipro_nodes = sorted([n for n in nodes if n["type"] == "WanImageToVideoSVIPro"], key=lambda n: n["id"])
    for i, n in enumerate(svipro_nodes):
        has_prev = any(inp["name"] == "prev_samples" and inp.get("link") is not None for inp in n.get("inputs", []))
        if i == 0 and has_prev:
            errors.append(f"chunk 1 node {n['id']} has prev_samples (expected none)")
        if i > 0 and not has_prev:
            errors.append(f"chunk {i + 1} node {n['id']} missing prev_samples")

    print(f"Nodes: {len(nodes)}  Links: {len(links)}")
    print(f"  SVIPro chunks: {len(svipro_nodes)}")
    print(f"  IBEwO seams:   {sum(1 for n in nodes if n['type'] == 'ImageBatchExtendWithOverlap')}")
    print(f"  Sage patches:  {sum(1 for n in nodes if n['type'] == 'PathchSageAttentionKJ')}")
    if errors:
        print("ERRORS:")
        for e in errors:
            print(f"  {e}")
        return False
    print("OK  —  no dangling links, no duplicates, chunk chain valid.")
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--verify", type=Path, help="verify an existing file, skip build")
    args = ap.parse_args()

    root = Path(__file__).resolve().parent.parent
    if args.verify:
        sys.exit(0 if verify(args.verify) else 1)
    template = root / "workflows" / "i2v_svi_4chunk.json"
    output = root / "workflows" / "i2v_svi_long.json"
    build(template, output)
    print(f"Wrote {output}")
    if not verify(output):
        sys.exit(1)


if __name__ == "__main__":
    main()
