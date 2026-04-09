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

| Key | What's Downloaded | Size | Use Case |
|-----|-------------------|------|----------|
| `wan2.2_t2v_bundle` | T2V (low+high noise) + text encoder + VAE + LightX2V LoRAs | ~24GB | Text-to-video |
| `wan2.2_i2v_bundle` | I2V (low+high noise) + text encoder + VAE + CLIP + LightX2V LoRAs | ~24GB | Image-to-video |
| `wan2.2_full_bundle` | Everything above combined | ~45GB | Both T2V + I2V |
| `wan2.2_full_bundle,nsfw_lora_bundle` | Full + NSFW-22-H/L LoRAs | ~46GB | SFW + NSFW toggle |
| `remix_nsfw_i2v_bundle` | FX-FeiHou Remix NSFW I2V v2.0 + encoders + CLIP | ~24GB | Dedicated NSFW I2V |
| `phr00t_nsfw_i2v_bundle` | Phr00t Rapid AIO NSFW I2V + encoders + CLIP | ~23GB | Dedicated NSFW I2V |

Multiple bundles can be combined with commas — shared files (text encoder, VAE) are only downloaded once.

## Adding Models to a Running Pod

You can download additional models via SSH without restarting the pod. ComfyUI will pick them up after a soft restart.

```bash
# Add NSFW LoRAs to an existing full bundle pod
HUGGINGFACE_MODELS=nsfw_lora_bundle bash /workspace/scripts/download_models_once.sh

# Add FX-FeiHou Remix NSFW models (text encoder/VAE already cached)
HUGGINGFACE_MODELS=remix_nsfw_i2v_bundle bash /workspace/scripts/download_models_once.sh

# Add Phr00t NSFW models
HUGGINGFACE_MODELS=phr00t_nsfw_i2v_bundle bash /workspace/scripts/download_models_once.sh

# Add any individual model key
HUGGINGFACE_MODELS=wan2.2_t2v_high_noise_fp8 bash /workspace/scripts/download_models_once.sh
```

Then soft restart ComfyUI to rescan model directories:
```bash
bash /workspace/scripts/restart-comfyui.sh
```

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
Storage: Ephemeral volume (0GB; models redownload each start) (Container: 200GB disk, 0GB volume)

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
