# 🎬 Ignition H3 RunPod Deployment Guide

MiniMax H3 — 768p video with **native 32 kHz stereo audio** generated in a single pass.

## Quick Start

1. **Import Template** (or use `./template.sh --deploy` for direct API deployment):
   - Go to RunPod Templates
   - Click "New Template"
   - Upload the `ignition_template.json` file

2. **Deploy Pod**:
   - Select the Ignition H3 template
   - Choose a GPU with **24 GB+ VRAM** (5090 preferred; INT8 uses ~21 GB)
   - Deploy!

## Access URLs

Once your pod is running:

- **ComfyUI**: `http://[your-pod-id]-8188.proxy.runpod.net`
- **File Browser**: `http://[your-pod-id]-8080.proxy.runpod.net`
  - Username: `admin`
  - Password: `runpod`

## Model Presets

No HF token required — `Comfy-Org/MiniMax-H3` is ungated.

| Key | Disk | VRAM | Notes |
|-----|------|------|-------|
| `h3_int8_bundle` | ~43 GB | ~21 GB | Pruned INT8 convrot. Runs on any 24 GB+ card. **Default.** |
| `h3_fp8_bundle` | ~43 GB | ~21 GB | Pruned FP8 scaled. Native kernels on Ada/Hopper/Blackwell, emulated (slower) on older cards. |

Both bundles include the Qwen3-VL-32B NVFP4 text encoder (15.69 GB), both VAEs
(video fp16 5.21 GB + audio fp32 0.61 GB) and the 4-step Turbo LoRA (~744 MB).

Switching bundles needs no rebuild: `startup.sh` runs
`scripts/retarget_workflows.py`, which repoints every loader — including the
subgraph's promoted widget and `properties.models` — at whichever quant
actually downloaded.

Individual keys: `h3_fl2va_int8`, `h3_fl2va_fp8`, `h3_ref2va_int8`,
`h3_ref2va_fp8`, `h3_text_encoder_nvfp4`, `h3_text_encoder_int8`,
`h3_video_vae`, `h3_audio_vae`, `h3_turbo_lora`

## Workflows

Two workflows ship, both adapted from Comfy's official templates:

- `minimax_h3_i2v_turbo.json` — image to video (first/last frame)
- `minimax_h3_t2v_turbo.json` — text to video

**The Turbo LoRA is ON by default at 6 steps.** For final renders, select the
`Turbo LoRA` node inside the subgraph, press `Ctrl+B` to bypass it, and raise
`BasicScheduler` steps back to `20`. A 4 s 720p clip is roughly 7 minutes on a
4090 at full steps, so turbo is what makes prompt iteration bearable.

Constraints baked into the model: 768 px short edge, capped at 768×1344, each
axis rounded to a multiple of 32; duration snaps to a 17k+5 frame grid at 24 fps.

## Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `HUGGINGFACE_MODELS` | Model bundle or comma-separated keys | `h3_int8_bundle` |
| `HF_TOKEN` | HuggingFace token (not needed — H3 is ungated) | `hf_xxx` |
| `CIVITAI_MODELS` | CivitAI checkpoint IDs (optional) | `138977` |
| `CIVITAI_LORAS` | CivitAI LoRA IDs (optional) | `182404` |
| `CIVITAI_TOKEN` | CivitAI API token (optional) | `abc123` |
| `FORCE_MODEL_SYNC` | Re-download all models on start | `true` |

### Storage Configuration
Storage: Ephemeral volume (0GB; models redownload each start) (Container: 150GB disk, 0GB volume)

## Startup Process

1. 🔍 System check + GPU detection
2. 💾 Storage setup (creates model dirs)
3. 📥 Model downloads via HuggingFace (parallel with CivitAI if set)
4. 🎯 Workflow retargeting to the downloaded quant
5. 📁 File browser start (port 8080)
6. 🎬 ComfyUI start (port 8188) — no custom node packs, all nodes are core

## 🔄 Restarting ComfyUI

### Soft Restart (Models Preserved)
```bash
/workspace/scripts/restart-comfyui.sh
```
- Restarts ComfyUI in 2 seconds
- All models and data preserved
- Container keeps running

### Hard Stop (Triggers Nuke)
```bash
/workspace/scripts/stop-pod.sh
```
- Exits container completely
- Nuclear cleanup deletes all data

| Action | Models | Container | Nuke |
|--------|--------|-----------|------|
| Soft Restart | ✅ Preserved | Running | ❌ No |
| Hard Stop | ❌ Deleted | Exits | ✅ Yes |
| Crash | ✅ Preserved | Running | ❌ No |

## Troubleshooting

### Logs
```bash
tail -f /tmp/ignition_startup.log
```

### Common Issues
- **Models not downloading**: Verify `HUGGINGFACE_MODELS` key spelling (`h3_int8_bundle` or `h3_fp8_bundle`)
- **Out of VRAM**: Use FP8 distilled (~18GB) or NVFP4 (~14GB, Blackwell only)
- **ComfyUI not responding**: Run `/workspace/scripts/restart-comfyui.sh`
- **Want to re-download models**: Set `FORCE_MODEL_SYNC=true` and restart pod

---
**🎬 Ready to generate video + audio with Ignition H3!**
