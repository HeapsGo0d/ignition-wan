# 🎬 Ignition WAN - ComfyUI Video Generation for RunPod

**WAN 2.2 · Text-to-Video · Image-to-Video · RTX 5090 Ready**

Ignition WAN is a RunPod-optimized Docker container for WAN 2.2 video generation via ComfyUI. Built on the same robust infrastructure as Ignition (image generation), it adds WanVideoWrapper and KJNodes at build time and downloads WAN models automatically at startup.

## ✨ Features

- **🎬 WAN 2.2 Video Generation**: Text-to-video and image-to-video via ComfyUI-WanVideoWrapper
- **⚡ Parallel Downloads**: Efficient concurrent downloading from HuggingFace and CivitAI
- **🔒 Atomic File Operations**: Download → verify → move → cleanup prevents corruption
- **🔄 Safe Restart Architecture**: Supervisor loop enables in-place restarts without data loss
- **💾 Flexible Storage**: Ephemeral or persistent model storage
- **🔐 Privacy Lite**: Automatic telemetry blocking and connection monitoring
- **📁 File Browser**: Web-based file management on port 8080
- **🚀 PyTorch Nightly + CUDA 12.8**: Optimized for RTX 5090 Blackwell architecture

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
1. **Version**: Enter tag (e.g. `v1.0.1`) or `latest`
2. **WAN Preset**: Choose from 5 presets (see below)
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
| `wan2.2_t2v_bundle` | T2V FP8 + text encoder + VAE | ~15GB | ~20GB | Text-to-video (recommended start) |
| `wan2.2_i2v_bundle` | I2V FP8 + text encoder + VAE + CLIP vision | ~15GB | ~20GB | Image-to-video |
| `wan2.2_full_bundle` | Both T2V + I2V + shared encoders | ~29GB | ~20GB | Both modes |
| `wan2.2_t2v_fp16` + extras | T2V full precision + text encoder + VAE | ~29GB | ~35GB | Max quality T2V |
| `wan2.2_i2v_fp16` + extras | I2V full precision + text encoder + VAE + CLIP | ~29GB | ~35GB | Max quality I2V |

### Individual Model Keys

You can also compose your own set:

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

**Example — T2V + I2V with shared encoders (manual):**
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
| `ENABLE_SAGEATTN` | Enable SageAttention GPU health check on boot (SA3 Blackwell-native, pre-compiled for sm_120) | `true` |
| `ENABLE_MANAGER_UI` | Show ComfyUI-Manager UI | `true` |
| `COMFY_FLAGS` | ComfyUI startup flags | `--preview-method auto` |
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

## ⚡ SageAttention (Optional Speed Boost)

Both SA2++ and SA3 are pre-compiled into the image for RTX 5090 (sm_120). SA3 is the active Blackwell-native backend — it uses native CUDA kernels and avoids the Triton JIT path that is broken on sm_120.

When `ENABLE_SAGEATTN=true` (default), a real GPU tensor test runs on boot to confirm SA3 works on the detected hardware.

**If startup log shows:**
```
⚡ SageAttention3 Blackwell ready — workflow: KJNodes patch node → sageattn3
```
Workflows are pre-configured with `sageattn3` backend — no action needed.

**If startup log shows:**
```
⚡ SageAttention3 runtime check FAILED
```
Set the KJNodes SA patch node backend to `disabled` in your workflow. Generation works normally without SA — it is a performance optimisation only.

**Important**: Do NOT use `--use-sage-attention` in `COMFY_FLAGS` — that uses the Triton backend which causes black frames with WAN 2.2's MoE architecture.

## 🔄 Restarting ComfyUI

### Soft Restart (Models Preserved)
```bash
/workspace/scripts/restart-comfyui.sh
```
Restarts ComfyUI in 2 seconds. All models and data remain intact. Container keeps running.

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
- **ComfyUI-Manager offline mode**: No network calls, no 5-min startup delay

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
| Out of VRAM | Use FP8 bundles (need ~20GB); avoid FP16 unless on A100/H100 |
| ComfyUI not responding | Run `restart-comfyui.sh` |
| Want to re-download | Set `FORCE_MODEL_SYNC=true` and restart pod |
| Check what downloaded | `tail -f /tmp/ignition_startup.log` |

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
