# 🎬 Ignition LTX RunPod Deployment Guide

## Quick Start

1. **Import Template** (or use `./template.sh --deploy` for direct API deployment):
   - Go to RunPod Templates
   - Click "New Template"
   - Upload the `ignition_template.json` file

2. **Deploy Pod**:
   - Select Ignition LTX template
   - Choose GPU (4090 for FP8; A100/H100 for BF16)
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
| `10eros_fp8_bundle` | ~29 GB | ~18-20 GB | FP8 mixed-learned, self-contained (VAE+CLIP bundled). Use `10Eros_10SNodes_I2V_v3_TiledSampler.json` workflow. |
| `10eros_bf16_bundle` | ~46 GB | ~24+ GB | Full quality, A100/H100. |

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

## Prompting for 10Eros

10Eros has minimal self-reasoning — prompts must be explicit and fully command all motion. Use the following structure (ideally via Grok or an uncensored LLM to expand):

```
Generate a video scene script based on the attached image for an LLM
with long-context understanding fed into a multimodal video model.

Strict specification:
- No timestamps
- No unnecessary embellishment
- Output only plain English text

Structure:
1. Describe the initial scene concisely (subject, appearance, composition, pose, background)
2. Formulate naturally evolving scenario describing every moving body part, composition change, and manipulation
3. Center around basic concept: [your concept]
4. Interweave dialogue or sound with descriptions of voice tone and quotations in temporal sequence
5. Describe only notable audio cues, background noise, foley, and natural sounds paired with motions
6. If no dialogue/soundscape - describe fitting genre, melodic tone, and mood for background music
```

**LoRA warning:** Larger distilled LoRAs harm the model. Only use condition-safe LoRAs from [TenStrip/LTX2.3_Distilled_Lora_1.1_Experiments](https://huggingface.co/TenStrip/LTX2.3_Distilled_Lora_1.1_Experiments/tree/main).

## Startup Process

1. 🔍 System check + GPU detection
2. 💾 Storage setup (creates model dirs incl. latent_upscale_models)
3. 📥 10Eros model downloads via HuggingFace (parallel with CivitAI if set)
4. 📁 File browser start (port 8080)
5. 🎬 ComfyUI start with ComfyUI-LTXVideo + 10S-Comfy-nodes (port 8188)

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

## Branch Reference

| Branch | Model | Status |
|--------|-------|--------|
| `feature/10eros` | 10Eros I2V (this branch) | Active |
| `spike/ltx-2.3` | Sulphur 2 GGUF + safetensors | Parked — use if switching back to Sulphur |

To switch back to Sulphur: rebuild image from `spike/ltx-2.3` and set `HUGGINGFACE_MODELS=sulphur2_fp8_bundle`.

## Troubleshooting

### Logs
```bash
tail -f /tmp/ignition_startup.log
```

### Common Issues
- **Models not downloading**: Verify `HUGGINGFACE_MODELS` key spelling (e.g. `10eros_fp8_bundle`)
- **Out of VRAM**: Use `10eros_fp8_bundle` (~18-20 GB) instead of BF16
- **Node resolution errors**: Ensure 10S-Comfy-nodes is installed; check ComfyUI Manager
- **ComfyUI not responding**: Run `/workspace/scripts/restart-comfyui.sh`
- **Want to re-download models**: Set `FORCE_MODEL_SYNC=true` and restart pod

---
**🎬 Ready to generate video with Ignition LTX / 10Eros!**
