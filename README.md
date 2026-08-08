# Ignition H3

A RunPod deployment kit for **MiniMax H3** — 768p video with **native 32 kHz stereo audio**
generated in a single pass. Docker image + bootstrap scripts + ComfyUI workflows.

```bash
./template.sh -y v2.0.0-h3 --deploy    # needs RUNPOD_API_KEY
```

Image: `heapsgo0d/ignition-h3`. Ports: 8188 (ComfyUI), 8080 (file browser).

## What this is

MiniMax H3 open-weighted on 2026-08-03: a 33.1B dense omni transformer with a
Qwen3-VL-32B text encoder, up to 15 s of video with synchronised dialogue,
ambient sound and score. Native ComfyUI support landed the same day.

This repo is a **spike** — the goal is to find out whether H3 beats the WAN 2.2
and LTX-2.3 attempts that came before it. The parked `feature/10eros` branch
and its `PARKED.md` record that lineage; `main` is still the WAN 2.2 platform.

## Design

**Zero custom node packs.** Every node type the workflows use is ComfyUI core:

| Node | Source |
|---|---|
| `MiniMaxH3ImageToVideo`, `MiniMaxH3ReferenceToVideo`, `MiniMaxH3SigmaShift`, `EmptyMiniMaxH3LatentAV` | `comfy_extras/nodes_minimax_h3.py` |
| `SaveVideo`, `CreateVideo` | `comfy_extras/nodes_video.py` |
| `ComfyMathExpression` | `comfy_extras/nodes_math.py` |
| `ResolutionSelector` | `comfy_extras/nodes_resolution.py` |
| `VAEDecodeAudio` | `comfy_extras/nodes_audio.py` |
| `LoraLoaderModelOnly`, `UNETLoader`, `CLIPLoader`, `VAELoader`, … | `nodes.py` |

Note that `ComfyMathExpression` and `ResolutionSelector` were third-party packs
as recently as the LTX branch and are core now — check core before re-adding a
dependency. `scripts/check_workflows.py` enforces this.

**Two guard scripts.** Every load-blocking bug this project has shipped was a
mismatch between what a workflow names, what the registry downloads, and what
the image installs — each found by hand, on a pod, after a long build:

- `scripts/check_workflows.py` — runs in CI (and again in the Dockerfile) and
  fails the build if a workflow names a model with no registry entry, points at
  a different HF repo than we download from, uses a nested path the registry
  doesn't write to, or uses a node type outside core.
- `scripts/retarget_workflows.py` — runs at boot and repoints every loader at
  whichever quant actually downloaded, so switching bundles needs no rebuild
  and no manual dropdown fiddling.

The retarget script rewrites the **parent subgraph instance's** widget values,
not just the inner node's. In these workflows the inner `UNETLoader` widget is
dead text — overridden by a link from the subgraph input node. The same trap
(a link-driven widget silently overriding a stored value) is what broke the
parked 10Eros branch.

## Model bundles

No HF token needed — `Comfy-Org/MiniMax-H3` is ungated.

| Key | Disk | VRAM | Notes |
|---|---|---|---|
| `h3_int8_bundle` | ~43 GB | ~21 GB | Pruned INT8 convrot. Any 24 GB+ card. **Default.** |
| `h3_fp8_bundle` | ~43 GB | ~21 GB | Pruned FP8 scaled. Native kernels on Ada/Hopper/Blackwell. |

Both include the Qwen3-VL-32B NVFP4 text encoder (15.69 GB), the video VAE
(fp16, 5.21 GB), the audio VAE (fp32, 0.61 GB) and the 4-step Turbo LoRA.

Full bf16 would be 123.6 GB; the pruned-int8 stack is the 42.5 GB figure Comfy
quote, staged across CPU/GPU with dynamic offloading.

## Workflows

Adapted from Comfy's official templates, with the Turbo LoRA wired in:

- `workflows/minimax_h3_i2v_turbo.json` — image to video (first/last frame)
- `workflows/minimax_h3_t2v_turbo.json` — text to video

**Turbo LoRA is ON at 6 steps.** A 4 s 720p clip is ~7 minutes on a 4090 at the
stock 20 steps, which makes prompt iteration painful. For finals, select the
`Turbo LoRA` node inside the subgraph, `Ctrl+B` to bypass, and put
`BasicScheduler` steps back to 20. The LoRA is new — compare before trusting it.

Model constraints: 768 px short edge, capped at 768×1344, axes rounded to a
multiple of 32; duration snaps to a 17k+5 frame grid at 24 fps.

R2V (reference-driven, up to 9 images or 3 video/audio clips) is not shipped —
it needs a second 20.97 GB diffusion model. The registry keys exist
(`h3_ref2va_int8`, `h3_ref2va_fp8`) if you want to add it.

## Layout

```
Dockerfile                      single stage, CUDA 13.0.3 runtime, cu130 nightly torch
template.sh                     RunPod template generator / API deployer
scripts/startup.sh              bootstrap + ComfyUI supervisor loop
scripts/download_*.py           model registry and aria2c downloaders
scripts/check_workflows.py      build-time consistency gate
scripts/retarget_workflows.py   boot-time quant retargeting
scripts/nuke                    4-phase wipe on clean shutdown
workflows/                      the two shipped workflows
```

## Privacy

Carried over from the earlier images and still wired into `startup.sh`:
a telemetry blocklist applied to `/etc/hosts` before any download (19 domains,
IPv4 + IPv6), connection monitoring, ComfyUI-Manager forced to
`network_mode = offline`, and `nuke` on clean shutdown — which deliberately
does *not* run if ComfyUI failed to start, so a broken pod stays debuggable.
It is "privacy lite": a hosts-file blocklist stops name resolution, not
direct-IP traffic.

Two deliberate choices in the default `COMFY_FLAGS`:

- **No `--enable-cors-header`.** It used to be set, annotated "required for
  RunPod reverse proxy access" — which is wrong, the proxy is same-origin.
  Passed without a value it means `*`, and since ComfyUI has no authentication,
  that let any page you visited script this pod's API. Add it back only if you
  genuinely drive the pod cross-origin.
- **`--disable-metadata`.** ComfyUI otherwise embeds prompt text and the full
  workflow JSON in every output file, which travels with the file when it
  leaves the pod. The cost is that you can no longer drag an output back into
  ComfyUI to recover its workflow.

`COMFY_FLAGS` replaces both wholesale if you set it.

Dropping the ten custom node packs also removed the largest untrusted-code
surface in the image — nothing third-party now executes at startup.

**Still open:** `FILEBROWSER_PASSWORD` defaults to `runpod` (and `-y` takes the
default), with filebrowser rooted at all of `/workspace` on a public proxy URL.
Set a real password when deploying.

## Notes

- Everything lives under `/workspace` and `VOLUME_GB` defaults to `0`
  (ephemeral). Mounting a non-empty network volume at `/workspace` would shadow
  the baked ComfyUI install.
- ComfyUI-Manager is forced offline (`network_mode = offline`).
- There is no runtime plugin installer. The previous
  `install-performance-plugins.sh` (Custom-Scripts, Crystools, comfyui-various)
  was removed: it installed custom node packs at boot, contradicting the
  zero-packs design, and it recreated the legacy Manager config directory that
  `startup.sh` deliberately avoids. Re-add deliberately if you want those.

## Open questions

- **Licence.** H3 ships under the MiniMax H3 Community License Agreement. Read
  it before treating this as a product foundation rather than a spike.
- **Content ceiling.** H3 base is not NSFW-tuned, unlike 10Eros. If that is a
  blocker, `ostris/ai-toolkit` has built-in `minimax_h3` T2V/I2V LoRA training
  with NVFP4 quantization for consumer GPUs.
