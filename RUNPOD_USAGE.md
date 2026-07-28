# 🎬 Ignition LTX RunPod Deployment Guide

## Quick Start

1. **Import Template** (or use `./template.sh --deploy` for direct API deployment):
   - Go to RunPod Templates
   - Click "New Template"
   - Upload the `ignition_template.json` file

2. **Deploy Pod**:
   - Select Ignition LTX template
   - Choose GPU (RTX 5090 recommended for NVFP4; 4090/A100 for FP8 distilled)
   - Add network volume for persistent model storage
   - Deploy!

## Access URLs

Once your pod is running:

- **ComfyUI**: `http://[your-pod-id]-8188.proxy.runpod.net`
- **File Browser**: `http://[your-pod-id]-8080.proxy.runpod.net`
  - Username: `admin`
  - Password: `runpod`

## Model Presets

**10Eros I2V (recommended default, no HF token required):**

| Key | Disk | VRAM | Notes |
|-----|------|------|-------|
| `10eros_fp8_bundle` | ~44 GB | ~18-20 GB | FP8 checkpoint + Gemma FP8 + upscaler + LoRA. Filenames match the shipped workflows — no UI changes needed. |
| `10eros_bf16_bundle` | ~72 GB | ~24+ GB | BF16 checkpoint + Gemma BF16 + upscaler + LoRA. A100/H100. Requires repointing 4 loader dropdowns to the BF16 files. |

Use the `10Eros_10SNodes_I2V_v3_TiledSampler.json` workflow (or `..._LikenessGuideHelper_I2V_v3.2.json` for face-likeness work).
`RTXVideoSuperResolution` ships bypassed — it needs NVIDIA's `nvvfx` SDK, which is not available in the Linux container.

**Standard LTX-2.3 bundles (Gemma FP8, no HF token required):**

| Key | Disk | VRAM | Use Case |
|-----|------|------|----------|
| `ltx2.3_distilled_fp8_bundle` | ~41 GB | ~18-20 GB | T2V + I2V (fast) |
| `ltx2.3_dev_fp8_bundle` | ~41 GB | ~20-22 GB | T2V + I2V (quality) |
| `ltx2.3_nvfp4_bundle` | ~34 GB | ~14 GB | RTX 5090 Blackwell only |
| `ltx2.3_full_bundle` | ~51 GB | ~20 GB | FP8 + LoRA + upscalers |

**Standard LTX-2.3 bundles (Gemma BF16, full text quality):**

| Key | Disk | VRAM | Use Case |
|-----|------|------|----------|
| `ltx2.3_distilled_fp8_bundle_bf16` | ~53 GB | ~24-26 GB | T2V + I2V (max quality) |
| `ltx2.3_dev_fp8_bundle_bf16` | ~53 GB | ~24-26 GB | T2V + I2V (max quality) |
| `ltx2.3_full_bundle_bf16` | ~63 GB | ~24 GB | BF16 + LoRA + upscalers |

Individual keys: `10eros_fp8`, `10eros_bf16`, `ltx23_video_vae`, `ltx23_audio_vae`, `ltx2.3_dev_fp8`, `ltx2.3_distilled_fp8`, `gemma3_text_encoder`

## Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `HUGGINGFACE_MODELS` | Model bundle or comma-separated keys | `10eros_fp8_bundle` |
| `HF_TOKEN` | HuggingFace token (not needed for 10Eros or standard LTX bundles) | `hf_xxx` |
| `CIVITAI_MODELS` | CivitAI checkpoint IDs (optional) | `138977` |
| `CIVITAI_LORAS` | CivitAI LoRA IDs (optional) | `182404` |
| `CIVITAI_TOKEN` | CivitAI API token (optional) | `abc123` |
| `FORCE_MODEL_SYNC` | Re-download all models on start | `true` |

### Storage Configuration
Storage: Ephemeral volume (0GB; models redownload each start) (Container: 150GB disk, 0GB volume)

## Startup Process

1. 🔍 System check + GPU detection
2. 💾 Storage setup (creates model dirs incl. latent_upscale_models)
3. 📥 LTX-2.3 model downloads via HuggingFace (parallel with CivitAI if set)
4. 📁 File browser start (port 8080)
5. 🎬 ComfyUI start with ComfyUI-LTXVideo nodes (port 8188)

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
- **Models not downloading**: Verify `HUGGINGFACE_MODELS` key spelling; set `HF_TOKEN` for Gemma
- **Gemma download fails**: Accept license at huggingface.co/google/gemma-3-12b-it-qat-q4_0-unquantized
- **Out of VRAM**: Use FP8 distilled (~18GB) or NVFP4 (~14GB, Blackwell only)
- **ComfyUI not responding**: Run `/workspace/scripts/restart-comfyui.sh`
- **Want to re-download models**: Set `FORCE_MODEL_SYNC=true` and restart pod

---
**🎬 Ready to generate video with Ignition LTX!**
