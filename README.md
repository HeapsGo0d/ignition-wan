# 🎬 Ignition WAN - ComfyUI Video Generation for RunPod

**WAN 2.2 · Text-to-Video · Image-to-Video · RTX 5090 Ready**

Ignition WAN is a RunPod-optimized Docker container for WAN 2.2 video generation via ComfyUI. Built on the same infrastructure as Ignition (image generation), it adds WanVideoWrapper, KJNodes, and SageAttention at build time and downloads WAN models automatically at startup.

## ✨ Features

- **🎬 WAN 2.2 Video Generation**: Text-to-video and image-to-video via ComfyUI-WanVideoWrapper
- **⚡ Parallel Downloads**: Concurrent downloading from HuggingFace and CivitAI
- **🔒 Atomic File Operations**: Download → verify → move → cleanup prevents corruption
- **🔄 Safe Restart Architecture**: Supervisor loop enables in-place restarts without data loss
- **💾 Flexible Storage**: Ephemeral or persistent model storage
- **🔐 Privacy Lite**: Automatic telemetry blocking and connection monitoring
- **📁 File Browser**: Web-based file management on port 8080 (v2.63.3 pinned)
- **🚀 PyTorch Nightly + CUDA 13.0**: Upgraded from CUDA 12.8 — RTX 5090 Blackwell optimized

## 🆕 v2.0.0 — CUDA 13 Upgrade

- Base images updated: `nvidia/cuda:13.0.3-cudnn-*-ubuntu24.04` (was 12.8.1)
- PyTorch nightly from `cu130` index (was `cu128`)
- SageAttention2++ and SA3 unchanged — recompiled against new CUDA toolchain
- Filebrowser pinned to v2.63.3 direct download (avoids GitHub API rate-limits)

## 🚀 Quick Start

### Automated Template Creation

```bash
# Local file generation
./template.sh

# Direct RunPod API deployment
export RUNPOD_API_KEY="your_runpod_api_key"
./template.sh --deploy
```

**Interactive prompts:**
1. **Version**: Enter tag (e.g. `v2.0.0`) or `latest`
2. **WAN Preset**: Choose from 8 presets (see below)
3. **Storage**: Container disk and volume sizes
4. **Password**: File browser password

### Manual Docker Run

```bash
docker run -d \
  --gpus all \
  -p 8188:8188 \
  -p 8080:8080 \
  -e HUGGINGFACE_MODELS="wan2.2_t2v_bundle" \
  -e HF_TOKEN="your_hf_token" \
  heapsgo0d/ignition-wan:latest
```

## 🎬 WAN 2.2 Model Presets

Set `HUGGINGFACE_MODELS` to one of these bundle keys. All models sourced from `Comfy-Org/Wan_2.2_ComfyUI_Repackaged`.

| Preset Key | Downloads | Size | VRAM | Use Case |
|---|---|---|---|---|
| `wan2.2_t2v_bundle` | T2V FP8 + text encoder + VAE | ~24GB | ~20GB | Text-to-video (recommended start) |
| `wan2.2_i2v_bundle` | I2V FP8 + text encoder + VAE + CLIP vision | ~24GB | ~20GB | Image-to-video |
| `wan2.2_full_bundle` | Both T2V + I2V + shared encoders | ~45GB | ~20GB | Both modes |
| `wan2.2_full_bundle,nsfw_lora_bundle` | Full bundle + NSFW LoRAs | ~46GB | ~20GB | Both modes + NSFW |
| `remix_nsfw_i2v_bundle` | FX-FeiHou Remix NSFW I2V v3.0 | ~24GB | ~20GB | NSFW image-to-video |
| `phr00t_mega_nsfw_bundle` | Phr00t MEGA NSFW v12.2 | ~15GB | ~20GB | Unified NSFW T2V+I2V |
| `nsfw_i2v_full_bundle` | All 3 NSFW I2V workflows | ~70GB | ~20GB | Full NSFW I2V suite |

### Individual Model Keys

Compose your own set:

| Key | File | Directory |
|---|---|---|
| `wan2.2_t2v_fp8` | wan2.2_t2v_low_noise_14B_fp8_scaled.safetensors | diffusion_models/ |
| `wan2.2_t2v_high_noise_fp8` | wan2.2_t2v_high_noise_14B_fp8_scaled.safetensors | diffusion_models/ |
| `wan2.2_t2v_fp16` | wan2.2_t2v_low_noise_14B_fp16.safetensors | diffusion_models/ |
| `wan2.2_i2v_fp8` | wan2.2_i2v_low_noise_14B_fp8_scaled.safetensors | diffusion_models/ |
| `wan2.2_i2v_high_noise_fp8` | wan2.2_i2v_high_noise_14B_fp8_scaled.safetensors | diffusion_models/ |
| `wan2.2_i2v_fp16` | wan2.2_i2v_low_noise_14B_fp16.safetensors | diffusion_models/ |
| `umt5_xxl_fp8` | umt5_xxl_fp8_e4m3fn_scaled.safetensors | text_encoders/ |
| `wan_vae` | wan_2.1_vae.safetensors | vae/ |
| `clip_vision_h` | clip_vision_h.safetensors | clip_vision/ |

**Example — T2V + I2V with shared encoders:**
```
HUGGINGFACE_MODELS="wan2.2_t2v_fp8,wan2.2_i2v_fp8,umt5_xxl_fp8,wan_vae,clip_vision_h"
```

## 📋 Environment Variables

### Model Sources
| Variable | Description | Example |
|---|---|---|
| `HUGGINGFACE_MODELS` | WAN bundle key or comma-separated individual keys | `wan2.2_t2v_bundle` |
| `CIVITAI_MODELS` | CivitAI checkpoint version IDs (optional) | `"123456"` |
| `CIVITAI_LORAS` | CivitAI LoRA version IDs (optional) | `"345678"` |
| `CIVITAI_VAES` | CivitAI VAE version IDs (optional) | `"567890"` |

### Authentication
| Variable | Description |
|---|---|
| `HF_TOKEN` | HuggingFace API token (optional, for private repos) |
| `CIVITAI_TOKEN` | CivitAI API token (optional, for faster downloads) |

### Configuration
| Variable | Description | Default |
|---|---|---|
| `FILEBROWSER_PASSWORD` | File browser login password | `runpod` |
| `ENABLE_SAGEATTN` | Run SA3 GPU health check on boot; if passed, SA3 Blackwell kernels are active | `true` |
| `ENABLE_MANAGER_UI` | Show ComfyUI-Manager UI (adds ~2-3s load time) | `false` |
| `COMFY_FLAGS` | ComfyUI startup flags | `--preview-method auto --enable-cors-header` |
| `FORCE_MODEL_SYNC` | Re-download all models on start | `false` |

## 📁 File Organization

```
/workspace/ComfyUI/models/
├── diffusion_models/   # WAN T2V and I2V models
├── text_encoders/      # UMT5-XXL text encoder
├── vae/                # WAN VAE
├── clip_vision/        # CLIP vision encoder (I2V)
├── checkpoints/        # CivitAI checkpoints (optional)
├── loras/              # LoRA models (optional)
└── upscale_models/     # Upscalers (optional)
```

## ⚡ SageAttention (Required for WAN 2.2 Performance)

Both SA2++ (v2.2.0) and SA3 are pre-compiled into the image for RTX 5090 (sm_120). SA3 is the active Blackwell-native backend — it uses native CUDA kernels and avoids the Triton JIT path that is broken on sm_120 with WAN 2.2's MoE architecture.

When `ENABLE_SAGEATTN=true` (default), a real GPU tensor test runs on boot to confirm SA3 works on the detected hardware:

**If startup log shows:**
```
⚡ SageAttention3 Blackwell ready — workflow: KJNodes patch node → sageattn3
```
Workflows are pre-configured with `sageattn3` backend — no action needed.

**If startup log shows:**
```
⚡ SageAttention3 runtime check FAILED
```
Set the KJNodes SA patch node backend to `disabled` in your workflow. Generation still works — SA is a performance optimisation only.

**Important**: Do NOT use `--use-sage-attention` in `COMFY_FLAGS` — that activates the Triton backend which causes black frames with WAN 2.2 MoE.

## 🔄 Restarting ComfyUI

### Soft Restart (Models Preserved)
```bash
/workspace/scripts/restart-comfyui.sh
```
Restarts ComfyUI in 2 seconds. All models and data remain intact.

### Hard Stop (Triggers Nuke)
```bash
/workspace/scripts/stop-pod.sh
```
Exits container and runs nuclear cleanup (deletes all data).

| Action | Models | Container | Nuke |
|---|---|---|---|
| Soft Restart | ✅ Preserved | Running | ❌ No |
| Hard Stop | ❌ Deleted | Exits | ✅ Yes |
| Crash | ✅ Preserved | Running | ❌ No |

## 🔒 Privacy

- **Telemetry blocklist**: Blocks 17+ analytics domains via `/etc/hosts` before any downloads
- **Connection monitoring**: Logs external connections every 2 mins
- **ComfyUI-Manager offline mode**: No network calls, no startup delay

```bash
# View connection log
/workspace/scripts/privacy/show-connections.sh
```

## 📟 SSH Command Reference

```bash
# Restart ComfyUI (preserves models)
/workspace/scripts/restart-comfyui.sh

# Stop pod with cleanup
/workspace/scripts/stop-pod.sh

# Manual nuclear cleanup
nuke

# View startup logs
tail -f /tmp/ignition_startup.log

# View connection monitoring
/workspace/scripts/privacy/show-connections.sh

# List downloaded models
ls -lh /workspace/ComfyUI/models/diffusion_models/
ls -lh /workspace/ComfyUI/models/text_encoders/
ls -lh /workspace/ComfyUI/models/clip_vision/
```

## 🐛 Troubleshooting

| Issue | Fix |
|---|---|
| Models not downloading | Check `HUGGINGFACE_MODELS` key spelling; verify `HF_TOKEN` if needed |
| Out of VRAM | Use FP8 bundles (~20GB VRAM); avoid FP16 unless on A100/H100 |
| ComfyUI not responding | Run `restart-comfyui.sh` |
| Want to re-download | Set `FORCE_MODEL_SYNC=true` and restart pod |
| Check what downloaded | `tail -f /tmp/ignition_startup.log` |
| Black frames with SA | Do NOT set `--use-sage-attention`; use KJNodes patch node with `sageattn3` instead |

## 🏗️ Building Locally

```bash
git clone https://github.com/HeapsGo0d/ignition-wan.git
cd ignition-wan
docker build -t ignition-wan:dev .
```

## 🔐 Security Notes

- Use a strong `FILEBROWSER_PASSWORD` — file browser has admin access to the container filesystem
- Store API tokens in RunPod secrets rather than plaintext env vars
- Telemetry blocking activates automatically before any model downloads

---

**🎬 Ready to generate video with Ignition WAN? Deploy on RunPod today!**
