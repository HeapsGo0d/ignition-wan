# 🎬 Ignition WAN RunPod Deployment Guide

## Quick Start

1. **Import Template** (or use `./template.sh --deploy` for direct API deployment):
   - Go to RunPod Templates
   - Click "New Template"
   - Upload the `ignition_template.json` file

2. **Deploy Pod**:
   - Select Ignition WAN template
   - Choose GPU (RTX 5090 or A100 40GB recommended for 14B FP8 models)
   - Add network volume for persistent model storage
   - Deploy!

## Access URLs

Once your pod is running:

- **ComfyUI**: `http://[your-pod-id]-8188.proxy.runpod.net`
- **File Browser**: `http://[your-pod-id]-8080.proxy.runpod.net`
  - Username: `admin`
  - Password: `runpod`

## WAN 2.2 Model Presets

Set `HUGGINGFACE_MODELS` to one of these bundle keys:

| Key | Models Downloaded | VRAM | Use Case |
|-----|------------------|------|----------|
| `wan2.2_t2v_bundle` | T2V FP8 + text encoder + VAE | ~22GB | Text-to-video (standard) |
| `wan2.2_t2v_lightx2v_bundle` | Above + LightX2V LoRAs | ~22GB | T2V 4-step (5x faster) |
| `wan2.2_i2v_bundle` | I2V FP8 + text encoder + VAE + CLIP | ~22GB | Image-to-video (standard) |
| `wan2.2_i2v_lightx2v_bundle` | I2V FP8 (both variants) + LightX2V LoRAs | ~22GB | I2V 4-step (5x faster) |
| `wan2.2_full_bundle` | Both T2V + I2V + shared encoders | ~30GB | Both modes |

Individual keys also work: `wan2.2_t2v_fp8`, `wan2.2_i2v_fp8`, `umt5_xxl_fp8`, `wan_vae`, `clip_vision_h`, `lightx2v_t2v_low_noise`, `lightx2v_i2v_low_noise`

## Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `HUGGINGFACE_MODELS` | WAN model bundle or comma-separated keys | `wan2.2_t2v_bundle` |
| `HF_TOKEN` | HuggingFace API token (optional) | `hf_xxx` |
| `CIVITAI_MODELS` | CivitAI checkpoint IDs (optional) | `138977` |
| `CIVITAI_LORAS` | CivitAI LoRA IDs (optional) | `182404` |
| `CIVITAI_TOKEN` | CivitAI API token (optional) | `abc123` |
| `FORCE_MODEL_SYNC` | Re-download all models on start | `true` |

### Storage Configuration

| Setup | Container Disk | Volume | Notes |
|-------|---------------|--------|-------|
| Ephemeral | 200GB | 0GB | Models redownload each start (~15-30 min) |
| Persistent (recommended) | 50GB | 100GB+ | Models cached; instant subsequent starts |

## ⚡ SageAttention2++ (Optional Speed Boost)

Set `ENABLE_SAGEATTN=true` (default). SA2++ is **pre-compiled into the image** for RTX 5090 (sm_120) — available immediately on first boot, no background build, no restart required.

**In your workflow**: Add a KJNodes **"Apply Sage Attention"** patch node, set backend to `sageattn_qk_int8_pv_fp16_cuda`. Do not use `--use-sage-attention` in `COMFY_FLAGS` — it causes black frames with WAN 2.2.

## Startup Process

1. 🔍 System check + GPU detection
2. 💾 Storage setup (creates model dirs incl. clip_vision)
3. 📥 WAN model downloads via HuggingFace (parallel with CivitAI if set)
4. 📁 File browser start (port 8080)
5. 🎬 ComfyUI start with WanVideoWrapper (port 8188)

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
- **Models not downloading**: Verify `HUGGINGFACE_MODELS` key spelling
- **Out of VRAM**: Use FP8 bundles instead of FP16; ensure 20GB+ VRAM
- **ComfyUI not responding**: Run `/workspace/scripts/restart-comfyui.sh`
- **Want to re-download models**: Set `FORCE_MODEL_SYNC=true` and restart pod

---
**🎬 Ready to generate video with Ignition WAN!**
