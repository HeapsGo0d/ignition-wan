# Ignition LTX RunPod Deployment Guide

## Quick Start

1. **Import Template** (or use `./template.sh --deploy` for direct API deployment):
   - Go to RunPod Templates
   - Click "New Template"
   - Upload the `ignition_template.json` file

2. **Deploy Pod**:
   - Select Ignition LTX template
   - Choose GPU (6 GB VRAM min for Sulphur 2 GGUF; RTX 5090 for NVFP4 safetensors)
   - Add network volume for persistent model storage
   - Deploy!

## Access URLs

Once your pod is running:

- **ComfyUI**: `http://[your-pod-id]-8188.proxy.runpod.net`
- **File Browser**: `http://[your-pod-id]-8080.proxy.runpod.net`
  - Username: `admin`
  - Password: `runpod`

## Model Presets

**Sulphur 2 GGUF (NSFW, recommended default):**

| Key | Disk | VRAM | Notes |
|-----|------|------|-------|
| `sulphur2_gguf_bundle` | ~35 GB | 6 GB min | Distilled, no HF_TOKEN needed. Use `sulphur2_gguf.json` workflow. |

**Safetensors — Gemma FP8 bundles** (no HF token required):

| Key | Disk | VRAM | Use Case |
|-----|------|------|----------|
| `ltx2.3_distilled_fp8_bundle` | ~41 GB | ~18-20 GB | T2V + I2V (fast) |
| `ltx2.3_dev_fp8_bundle` | ~41 GB | ~20-22 GB | T2V + I2V (quality) |
| `ltx2.3_nvfp4_bundle` | ~34 GB | ~14 GB | RTX 5090 Blackwell only |
| `ltx2.3_full_bundle` | ~51 GB | ~20 GB | FP8 + LoRA + upscalers |

**Safetensors — Gemma BF16 bundles** (24 GB Gemma, full text quality):

| Key | Disk | VRAM | Use Case |
|-----|------|------|----------|
| `ltx2.3_distilled_fp8_bundle_bf16` | ~53 GB | ~24-26 GB | T2V + I2V (max quality) |
| `ltx2.3_dev_fp8_bundle_bf16` | ~53 GB | ~24-26 GB | T2V + I2V (max quality) |
| `ltx2.3_full_bundle_bf16` | ~63 GB | ~24 GB | BF16 + LoRA + upscalers |

Individual keys: `sulphur2_distil_q6k`, `gemma_gguf`, `sulphur2_connector`, `ltx23_video_vae`, `ltx23_audio_vae`, `film_net`, `ltx2.3_dev_fp8`, `ltx2.3_distilled_fp8`, `gemma3_text_encoder`

## Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `HUGGINGFACE_MODELS` | Model bundle or comma-separated keys | `sulphur2_gguf_bundle` |
| `HF_TOKEN` | HuggingFace token (not needed for Sulphur 2 GGUF) | `hf_xxx` |
| `CIVITAI_MODELS` | CivitAI checkpoint IDs (optional) | `138977` |
| `CIVITAI_LORAS` | CivitAI LoRA IDs (optional) | `182404` |
| `CIVITAI_TOKEN` | CivitAI API token (optional) | `abc123` |
| `FORCE_MODEL_SYNC` | Re-download all models on start | `true` |

## Startup Process

1. System check + GPU detection
2. Storage setup (creates model dirs incl. gguf, frame_interpolation)
3. Model downloads via HuggingFace (parallel with CivitAI if set)
4. File browser start (port 8080)
5. ComfyUI start with LTXVideo + LTX2_SM + Frame-Interpolation nodes (port 8188)

## Restarting ComfyUI

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
| Soft Restart | Preserved | Running | No |
| Hard Stop | Deleted | Exits | Yes |
| Crash | Preserved | Running | No |

## Troubleshooting

### Logs
```bash
tail -f /tmp/ignition_startup.log
```

### Common Issues
- **Models not downloading**: Verify `HUGGINGFACE_MODELS` key spelling
- **Sulphur 2 GGUF loads with UnboundLocalError**: Gemma GGUF must come from smthem repo (bundled automatically — do not substitute other Gemma GGUFs)
- **Out of VRAM on safetensors**: Switch to `sulphur2_gguf_bundle` (6 GB min) or NVFP4 (~14GB, Blackwell only)
- **ComfyUI not responding**: Run `/workspace/scripts/restart-comfyui.sh`
- **Want to re-download models**: Set `FORCE_MODEL_SYNC=true` and restart pod

---
**Ready to generate video with Ignition LTX!**
