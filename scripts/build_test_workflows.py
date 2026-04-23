#!/usr/bin/env python3
"""Build Step 1 and Step 2 test workflows for SVI debugging.

Outputs:
  workflows/i2v_wan_baseline.json  — neutral WAN 2.2 I2V, no LoRAs, 25 steps, 41 frames
  workflows/i2v_svi_single.json    — SVIPro single chunk, SVI LoRAs, 25 steps, 41 frames

Usage:
  python3 scripts/build_test_workflows.py
  python3 scripts/build_test_workflows.py --verify
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# Shared utilities
# ---------------------------------------------------------------------------

def _renumber_links(nodes: list, links: list) -> list:
    """Assign sequential IDs to links and update all node input/output refs."""
    old_to_new: dict[int, int] = {}
    new_links = []
    for new_id, lk in enumerate(links, start=1):
        old_to_new[lk[0]] = new_id
        new_lk = list(lk)
        new_lk[0] = new_id
        new_links.append(new_lk)
    for n in nodes:
        for inp in n.get("inputs", []) or []:
            if inp.get("link") in old_to_new:
                inp["link"] = old_to_new[inp["link"]]
        for out in n.get("outputs", []) or []:
            out["links"] = [old_to_new[l] for l in (out.get("links") or []) if l in old_to_new]
    return new_links


def _drop_nodes_and_links(nodes: list, links: list, drop_ids: set) -> None:
    """Remove nodes and all links touching them; clean dangling refs. In-place."""
    dead_links = {lk[0] for lk in links if lk[1] in drop_ids or lk[3] in drop_ids}
    nodes[:] = [n for n in nodes if n["id"] not in drop_ids]
    links[:] = [lk for lk in links if lk[0] not in dead_links]
    for n in nodes:
        for inp in n.get("inputs", []) or []:
            if inp.get("link") in dead_links:
                inp["link"] = None
        for out in n.get("outputs", []) or []:
            out["links"] = [l for l in (out.get("links") or []) if l not in dead_links]


def _add_link(nodes: list, links: list, src_id: int, src_slot: int,
              tgt_id: int, tgt_slot: int, type_str: str) -> int:
    """Append a link and wire its endpoint refs. Returns the new link ID."""
    new_id = max((lk[0] for lk in links), default=0) + 1
    links.append([new_id, src_id, src_slot, tgt_id, tgt_slot, type_str])
    for n in nodes:
        if n["id"] == src_id:
            outs = n.get("outputs", []) or []
            if src_slot < len(outs):
                outs[src_slot].setdefault("links", [])
                if new_id not in outs[src_slot]["links"]:
                    outs[src_slot]["links"].append(new_id)
        if n["id"] == tgt_id:
            inps = n.get("inputs", []) or []
            if tgt_slot < len(inps):
                inps[tgt_slot]["link"] = new_id
    return new_id


def _save(wf: dict, nodes: list, links: list, path: Path) -> None:
    wf["nodes"] = nodes
    wf["links"] = links
    wf["last_link_id"] = len(links)
    wf["last_node_id"] = max(n["id"] for n in nodes)
    path.write_text(json.dumps(wf, indent=2) + "\n")


# ---------------------------------------------------------------------------
# Step 1: neutral WAN 2.2 I2V baseline
# ---------------------------------------------------------------------------

def build_wan_baseline(src: Path, out: Path) -> None:
    """Strip LightX2V LoRAs from i2v_standard.json and fix step counts.

    Changes:
      - Remove LoraLoaderModelOnly nodes 18/19 (LightX2V LoRAs)
      - Rewire UNETLoader(7/8) directly to PathchSageAttentionKJ(9/10)
      - KSamplers: 25 steps, high 0→12, low 12→25
      - WanImageToVideo: 41 frames
      - Output filename: video/WAN_Baseline
    """
    wf = json.loads(src.read_text())
    nodes = wf["nodes"]
    links = wf["links"]

    # Drop LightX2V LoRA nodes (18=high, 19=low)
    _drop_nodes_and_links(nodes, links, {18, 19})

    # Rewire: UNETLoader(7) → SagePatch(9), UNETLoader(8) → SagePatch(10)
    _add_link(nodes, links, 7, 0, 9, 0, "MODEL")
    _add_link(nodes, links, 8, 0, 10, 0, "MODEL")

    # Fix KSampler step counts
    # widgets_values: [add_noise, seed, control_after_gen, steps, cfg,
    #                  sampler, scheduler, start_at_step, end_at_step, return_leftover]
    for n in nodes:
        if n["id"] == 13:  # high-noise KSampler
            wv = n["widgets_values"]
            wv[3] = 25   # steps
            wv[8] = 12   # end_at_step
        elif n["id"] == 14:  # low-noise KSampler
            wv = n["widgets_values"]
            wv[3] = 25   # steps
            wv[7] = 12   # start_at_step
            wv[8] = 25   # end_at_step

    # 41 frames (faster test iteration)
    for n in nodes:
        if n["id"] == 6 and n["type"] == "WanImageToVideo":
            n["widgets_values"][2] = 41

    # Output filename
    for n in nodes:
        if n["id"] == 17 and n["type"] == "SaveVideo":
            n["widgets_values"][0] = "video/WAN_Baseline"

    links[:] = _renumber_links(nodes, links)
    _save(wf, nodes, links, out)
    print(f"Wrote {out}  ({len(nodes)} nodes, {len(links)} links)")


# ---------------------------------------------------------------------------
# Step 2: SVIPro single chunk
# ---------------------------------------------------------------------------

def build_svi_single(src: Path, out: Path) -> None:
    """Extract chunk 1 from i2v_svi_4chunk.json as a standalone single-chunk workflow.

    Keeps: shared infrastructure (1,2,3,4,5,10,11,12,13,14,15,16,17,74)
           + chunk 1 (20,21,22,23) + output (70)
    Drops: chunks 2-4 (30-33, 40-43, 50-53) and ImageBatch cascade (60,61,62)
    Wires: VAEDecode(23) → VHS_VideoCombine(70) replacing the removed ImageBatch chain

    SVIPro(20) length set to 41 frames.
    """
    wf = json.loads(src.read_text())
    nodes = wf["nodes"]
    links = wf["links"]

    KEEP = {1, 2, 3, 4, 5, 10, 11, 12, 13, 14, 15, 16, 17, 74, 20, 21, 22, 23, 70}
    drop = {n["id"] for n in nodes if n["id"] not in KEEP}
    _drop_nodes_and_links(nodes, links, drop)

    # Wire VAEDecode(23) output slot 0 → VHS_VideoCombine(70) input slot 0 ("images")
    _add_link(nodes, links, 23, 0, 70, 0, "IMAGE")

    # Set SVIPro(20) length to 41 frames; widgets_values = [length, motion_latent_count]
    for n in nodes:
        if n["id"] == 20 and n["type"] == "WanImageToVideoSVIPro":
            n["widgets_values"][0] = 41

    # Update VHS filename
    for n in nodes:
        if n["id"] == 70 and n["type"] == "VHS_VideoCombine":
            n["widgets_values"][2] = "video/WAN_SVI_Single"

    # Titles
    TITLES = {
        1: "Start image",
        2: "CLIP — umt5_xxl",
        3: "Positive prompt",
        4: "Negative prompt",
        5: "VAE — wan_2.1",
        10: "UNet — high noise",
        11: "LoRA — SVI_v2_PRO HIGH fp16 (Kijai)",
        12: "Sage patch (high) — sageattn3",
        13: "ModelSamplingSD3 high — shift=5.0",
        14: "UNet — low noise",
        15: "LoRA — SVI_v2_PRO LOW fp16 (Kijai)",
        16: "Sage patch (low) — sageattn3",
        17: "ModelSamplingSD3 low — shift=5.0",
        74: "VAEEncode — anchor_samples",
        20: "WanImageToVideoSVIPro — length=41, mlc=1",
        21: "KSampler high — CFG 4.0 — steps 0→12",
        22: "KSampler low  — CFG 4.0 — steps 12→25",
        23: "VAEDecode",
        70: "VHS output — 16 fps",
    }
    for n in nodes:
        if n["id"] in TITLES:
            n["title"] = TITLES[n["id"]]

    links[:] = _renumber_links(nodes, links)
    _save(wf, nodes, links, out)
    print(f"Wrote {out}  ({len(nodes)} nodes, {len(links)} links)")


# ---------------------------------------------------------------------------
# Verification
# ---------------------------------------------------------------------------

def verify(path: Path) -> bool:
    wf = json.loads(path.read_text())
    nodes = wf["nodes"]
    links = wf["links"]
    node_ids = {n["id"] for n in nodes}
    link_id_set = {lk[0] for lk in links}
    errors: list[str] = []

    if len(node_ids) != len(nodes):
        errors.append("duplicate node IDs")
    if len(link_id_set) != len(links):
        errors.append("duplicate link IDs")

    for lk in links:
        lid, src_node, src_slot, tgt_node, tgt_slot, _ = lk
        if src_node not in node_ids:
            errors.append(f"link {lid}: src node {src_node} missing")
        if tgt_node not in node_ids:
            errors.append(f"link {lid}: tgt node {tgt_node} missing")

    for n in nodes:
        for inp in n.get("inputs", []) or []:
            lid = inp.get("link")
            if lid is not None and lid not in link_id_set:
                errors.append(f"node {n['id']} ({n['type']}) input '{inp['name']}' → missing link {lid}")
        for out in n.get("outputs", []) or []:
            for lid in out.get("links") or []:
                if lid not in link_id_set:
                    errors.append(f"node {n['id']} ({n['type']}) output '{out['name']}' → missing link {lid}")

    label = path.name
    print(f"  {label}: {len(nodes)} nodes, {len(links)} links", end="")
    if errors:
        print()
        for e in errors:
            print(f"    ERROR: {e}")
        return False
    print(" — OK")
    return True


# ---------------------------------------------------------------------------
# Step 3: SVIPro 2-chunk
# ---------------------------------------------------------------------------

def build_svi_2chunk(src: Path, out: Path) -> None:
    """Extract chunks 1+2 from i2v_svi_4chunk.json as a 2-chunk workflow.

    Keeps: shared infrastructure (1,2,3,4,5,10,11,12,13,14,15,16,17,74)
           + chunk 1 (20,21,22,23) + chunk 2 (30,31,32,33)
           + ImageBatch(60) + output (70)
    Drops: chunks 3-4 (40-43, 50-53) and extra ImageBatch nodes (61,62)
    Wires: ImageBatch(60) → VHS_VideoCombine(70)

    prev_samples chain (KSamplerLow_C1(22) → SVIPro_C2(30)) already present in source.
    SVIPro lengths set to 81 frames (full chunk).
    """
    wf = json.loads(src.read_text())
    nodes = wf["nodes"]
    links = wf["links"]

    KEEP = {1, 2, 3, 4, 5, 10, 11, 12, 13, 14, 15, 16, 17, 74,
            20, 21, 22, 23, 30, 31, 32, 33, 60, 70}
    drop = {n["id"] for n in nodes if n["id"] not in KEEP}
    _drop_nodes_and_links(nodes, links, drop)

    # Wire ImageBatch(60) output slot 0 → VHS_VideoCombine(70) input slot 0 ("images")
    _add_link(nodes, links, 60, 0, 70, 0, "IMAGE")

    # Set both SVIPro lengths to 81 frames
    for n in nodes:
        if n["type"] == "WanImageToVideoSVIPro":
            n["widgets_values"][0] = 81

    # Update VHS filename
    for n in nodes:
        if n["id"] == 70 and n["type"] == "VHS_VideoCombine":
            n["widgets_values"][2] = "video/WAN_SVI_2chunk"

    TITLES = {
        1: "Start image",
        2: "CLIP — umt5_xxl",
        3: "Positive prompt",
        4: "Negative prompt",
        5: "VAE — wan_2.1",
        10: "UNet — high noise",
        11: "LoRA — SVI_v2_PRO HIGH fp16 (Kijai)",
        12: "Sage patch (high) — sageattn3",
        13: "ModelSamplingSD3 high — shift=5.0",
        14: "UNet — low noise",
        15: "LoRA — SVI_v2_PRO LOW fp16 (Kijai)",
        16: "Sage patch (low) — sageattn3",
        17: "ModelSamplingSD3 low — shift=5.0",
        74: "VAEEncode — anchor_samples",
        20: "C1 SVIPro — length=81, mlc=1",
        21: "C1 KSampler high — CFG 4.0 — steps 0→12",
        22: "C1 KSampler low  — CFG 4.0 — steps 12→25",
        23: "C1 VAEDecode",
        30: "C2 SVIPro — length=81, mlc=1",
        31: "C2 KSampler high — CFG 4.0 — steps 0→12",
        32: "C2 KSampler low  — CFG 4.0 — steps 12→25",
        33: "C2 VAEDecode",
        60: "ImageBatch C1+C2",
        70: "VHS output — 16 fps",
    }
    for n in nodes:
        if n["id"] in TITLES:
            n["title"] = TITLES[n["id"]]

    links[:] = _renumber_links(nodes, links)
    _save(wf, nodes, links, out)
    print(f"Wrote {out}  ({len(nodes)} nodes, {len(links)} links)")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--verify", action="store_true", help="verify outputs without rebuilding")
    args = ap.parse_args()

    root = Path(__file__).resolve().parent.parent
    baseline = root / "workflows" / "i2v_wan_baseline.json"
    svi_single = root / "workflows" / "i2v_svi_single.json"
    svi_2chunk = root / "workflows" / "i2v_svi_2chunk.json"

    if not args.verify:
        build_wan_baseline(root / "workflows" / "i2v_standard.json", baseline)
        build_svi_single(root / "workflows" / "i2v_svi_4chunk.json", svi_single)
        build_svi_2chunk(root / "workflows" / "i2v_svi_4chunk.json", svi_2chunk)

    ok = verify(baseline) & verify(svi_single) & verify(svi_2chunk)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
