# `feature/10eros` — PARKED

**Status:** parked 2026-08-08 at `v1.0.3-10eros`. Superseded by `feature/minimax-h3`.

LTX2.3-10Eros by TenStrip — a layer-scaled merge of Sulphur-2-base optimised for I2V.
Default bundle `10eros_fp8_bundle` (~44 GB). Two workflows: TiledSampler and LikenessGuideHelper.

**This branch has never been run on a pod.** It is built and pushed but has produced no
generation results. Work stopped on 2026-05-26 right after `template.sh` generated the RunPod
template, and resumed only for load-blocker audits (2026-07-28) and the LoRA fix below.

## Why parked

MiniMax H3 open-weighted on 2026-08-03 with day-0 ComfyUI support and **native 32 kHz stereo
audio** — the Grok-Imagine-style property that neither WAN 2.2 nor the LTX line ever delivered.
That made it worth spiking before investing further here. See `feature/minimax-h3`.

## What was fixed before parking (v1.0.3-10eros)

The LoRA path bug, which would have failed every generation on this branch.

Node `783` (`easy loraNames`, "Distilled Lora") emits the bare filename
`ltx-2.3-22b-distilled-lora-1.1_fro90_ceil72_condsafe.safetensors` and feeds it via links
`2184–2187` into the `lora_name` **widget input** of nodes `718/719/722/723`. A linked widget
input overrides the node's stored widget value, so commit `9fd0425`'s `ltx23\` → `ltx23/`
correction had no effect at runtime. The downloader was writing the file to
`models/loras/ltx23/`, so ComfyUI listed it as `ltx23/<name>` and the bare name never resolved.

Fix: `scripts/download_huggingface_simple.py` now writes the LoRA to `loras/` root, and the four
stored widget values had their stale `ltx23/` prefix stripped so they agree with node 783.

**Lesson worth carrying forward:** a nested LoRA subdirectory is only safe if every node that
names the file uses the same prefix. When a `lora_name` is link-driven, the emitting node is the
one that matters — the stored widget value is dead text.

## Known issues, unfixed

1. **Missing-node dialog on load.** Node `755 RTXVideoSuperResolution` is bypassed (`mode: 4`)
   but its pack `comfyui_nvidia_rtx_nodes` is not installed — it needs the NVIDIA `nvvfx` SDK,
   which is not on PyPI and unavailable on Linux. ComfyUI will still report the node type as
   missing when either workflow loads. Harmless: dismiss the dialog and generate normally.

2. **`10eros_bf16_bundle` needs manual repointing.** The workflows hardcode FP8 filenames, so
   after downloading the BF16 bundle four loader dropdowns must be repointed by hand
   (`CheckpointLoaderSimple` 646, `LTXVAudioVAELoader` 617, `LTXAVTextEncoderLoader` 616 ×2).
   The files are present, just not selected. Documented in the registry and `RUNPOD_USAGE.md`.

3. **`README.md` is stale.** It still describes WAN 2.2 / `heapsgo0d/ignition-wan` /
   SageAttention. It has never described this branch's product. `RUNPOD_USAGE.md` is current
   and LTX-accurate; read that instead.

4. **Orphaned files.** `ignition_template_t2v_nsfw.json` is a WAN-era template (v1.0.25). The
   three `sulphur2_*` registry bundles are parked leftovers from `spike/ltx-2.3` with no
   matching workflow here. The six upstream `LTX-2.3_*` example workflows are SFW references
   not wired to any bundle.

5. **Manager config-path conflict.** `scripts/startup.sh` writes `user/__manager/config.ini`
   specifically to avoid ComfyUI-Manager running a migration on every boot, then
   `scripts/optional/install-performance-plugins.sh` creates the legacy
   `user/default/ComfyUI-Manager/config.ini` that step was avoiding.

6. **Cosmetic drift.** The startup banner says `IGNITION LTX v1.0.0`; a comment in
   `download_models_once.sh` still references WAN model keys; `RUNPOD_USAGE.md` troubleshooting
   still tells you to set `HF_TOKEN` for Gemma, though the Comfy-Org Gemma is ungated.

7. **No validation of any kind.** There are no tests and no workflow/registry/Dockerfile
   consistency checks. All four load-blockers fixed in `556d995`/`9fd0425`, plus the LoRA bug
   above, were mismatches in that triangle found by hand. `feature/minimax-h3` adds
   `scripts/check_workflows.py` to close this; worth backporting if this branch is revived.

## Upstream drift

TenStrip's `10S-Comfy-nodes` now ships newer workflows than the v3 / v3.2 pinned here:
`I2VBasic_v4`, `I2V_DMD_v1`, `I2V_FaceID_v2`. Start from those if you come back.

## Reviving

```bash
git checkout feature/10eros
./template.sh -y v1.0.3-10eros --deploy    # needs RUNPOD_API_KEY
```
Default bundle `10eros_fp8_bundle` (~44 GB), container disk 150 GB, no network volume.
First real smoke test is still outstanding.
