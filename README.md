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

## 🖼️ Image Upscaling

Two upscaling workflows are available. Both are in `workflows/` and work with the `clarity_bundle`.

| Workflow | Engine | VRAM | Speed | Best for |
|---|---|---|---|---|
| `img_clarity_upscale.json` | SD1.5 + ControlNet Tile + TiledDiffusion | ~6GB | ~15–30s | Portraits, fabric, photorealistic detail |
| `img_supir_upscale_nsfw_detail.json` | SDXL (SUPIR) | ~16GB | ~200–250s | Hero shots, maximum micro-texture |
| `img_supir_upscale_nsfw.json` | SDXL (SUPIR) | ~16GB | ~110–130s | Daily driver balanced quality |
| `img_supir_upscale_nsfw_clean.json` | SDXL (SUPIR) | ~16GB | ~60–80s | Fast batch / lowest hallucination risk |

---

### Clarity Controls

The Clarity workflow does a two-stage process: ESRGAN pixel upscale → 0.5× scale → diffusion detail pass. Net output is ~2× the input resolution.

#### Node: CheckpointLoaderSimple — which diffusion model to use

Two checkpoints ship in the `clarity_bundle`:

| Checkpoint | Character | Best for |
|---|---|---|
| `Realistic_Vision_V5.1_fp16-no-ema.safetensors` *(default)* | Conservative, neutral, photorealistic. Preserves identity, age, bone structure. | Portraits, identity-critical work |
| `DreamShaper_8_pruned.safetensors` | Creative/artistic. Beautifies and adds interpretive detail. | Fashion, objects, non-portrait work |

**If faces look older or bone structure drifts — stay on Realistic Vision.** DreamShaper's creative bias is the primary cause of identity drift in upscaling.

#### Node: UpscaleModelLoader — which ESRGAN to use

| Model | Character | Best for |
|---|---|---|
| `4xLSDIR.pth` *(default)* | Balanced, clean, natural colours | General use, portraits |
| `4x-UltraSharp.pth` | Maximum sharpness, fine edge detail | Fabric weave, text, architecture |
| `4x_NMKD-Siax_200k.pth` | Soft / painterly, preserves grain | Skin, film-look photos |
| `4x_foolhardy_Remacri.pth` | Vivid, contrasty | Stylised art, illustration |
| `4xNomos8kDAT.pth` | Film grain / noise aware | Photos with natural grain |

#### Node: KSampler — the main quality dial

| Widget | Default | What it does |
|---|---|---|
| `steps` | 24 | More steps = more refined but slower. 20–30 is the useful range. |
| `cfg` | 6 | How hard the diffusion pushes toward the prompt. Lower = softer/natural. Higher = sharper/riskier. |
| `sampler` | dpmpp_2m | Leave this alone unless experimenting. |
| `denoise` | **0.30** | **The most important dial.** 0 = no change, 1 = full redraw. 0.20–0.45 is the practical range. |

#### Node: ControlNetApplyAdvanced — how much the original is respected

| Widget | Default | What it does |
|---|---|---|
| `strength` | 0.65 | How strongly original spatial structure guides output. Original Clarity spec. Lower = more creative. |
| `start` | 0.0 | When ControlNet kicks in (0 = from step 1). |
| `end` | 1.0 | When ControlNet stops. 1.0 = guides the full process. Lower = final steps are more freely diffused. |

#### Node: FreeU_V2 — sharpness booster

| Widget | Default | What it does |
|---|---|---|
| `b1` | 1.3 | Boosts backbone scale-1 features (large shapes). >1 = more structure. |
| `b2` | 1.4 | Boosts backbone scale-2 features (medium detail). |
| `s1` | 0.9 | Suppresses skip-connection scale-1 (reduces ringing). |
| `s2` | 0.2 | Suppresses skip-connection scale-2 (reduces artifacts). |

#### Node: TiledDiffusion — handles large images without OOM

| Widget | Default | What it does |
|---|---|---|
| `tile_width / tile_height` | 768 | Tile size. Larger = more context per tile but more VRAM. |
| `overlap` | 64 | Pixels shared between adjacent tiles. More = smoother seams. |
| `batch_size` | 8 | How many tiles process together. Lower if OOM. |

#### Node: ImageScaleBy — controls output resolution

Default `0.5` means: 4× ESRGAN then halve → net **2× output**. Change to `0.25` for net 1× (same size, diffusion detail only), `1.0` for net 4×.

---

#### Clarity Troubleshooting

| Symptom | Fix |
|---|---|
| **Face looks older / bone structure changed** | Switch checkpoint to `Realistic_Vision_V5.1_fp16-no-ema.safetensors` (if not already). This is the highest-impact change for identity preservation. Lower `denoise` to 0.20–0.22. |
| **Skin looks plastic / airbrushed** | Switch to `Realistic_Vision_V5.1` checkpoint. Lower `denoise` to 0.20–0.25. Switch ESRGAN to `4x_NMKD-Siax_200k.pth`. Lower `cfg` to 4–5. |
| **Over-processed / AI-looking** | Switch to `Realistic_Vision_V5.1` checkpoint. Lower `denoise` to 0.20–0.25. Lower `cfg` to 3–4. |
| **Not enough detail / still blurry** | Raise `denoise` to 0.40–0.45. Switch ESRGAN to `4x-UltraSharp.pth`. Raise `cfg` to 7–8. For more aggressive: swap to `DreamShaper_8_pruned.safetensors`. |
| **Want more creative enhancement (fashion, objects)** | Switch checkpoint to `DreamShaper_8_pruned.safetensors`. Raise `denoise` to 0.35–0.45. |
| **Fabric texture washed out** | Raise `denoise` to 0.40+. Switch ESRGAN to `4x-UltraSharp.pth`. Raise ControlNet `strength` to 0.80. |
| **Tile seams visible** | Increase `overlap` to 96 or 128 in TiledDiffusion. |
| **Colours shifted / grading changed** | Lower `denoise`. Lower ControlNet `end` to 0.8. |
| **Face distorted or anatomy wrong** | Lower `denoise` to 0.18–0.22. Lower `cfg` to 3–4. |
| **Out of memory** | Lower `batch_size` in TiledDiffusion. Change ImageScaleBy to `0.25`. |
| **Too slow** | Lower `steps` to 16–20. Switch to `4xLSDIR.pth` (fastest ESRGAN). |

---

### SUPIR Controls

SUPIR uses SDXL-scale diffusion and does its own internal upscale. The three presets (detail / balanced / clean) differ only in their sampling parameters — same nodes, different values.

#### Node: SUPIR_sample — sampling parameters

| Widget | Detail | Balanced | Clean | What it does |
|---|---|---|---|---|
| `steps` | 100 | 50 | 32 | Steps for SDXL diffusion. <50 = insufficient micro-texture synthesis. |
| `cfg_start` | 7.5 | 5.5 | 4.0 | CFG at step 1. How strongly it follows the prompt at the start. |
| `cfg_end` | 4.0 | 3.2 | 2.8 | CFG at the final step. **Critical** — this is where micro-texture (pores, weave) gets baked in. Too low = smooth/plastic result. |
| `s_churn` | 6 | 5 | 3 | Stochastic noise injected during sampling. More = variety; too much = artifacts. |
| `s_noise` | 1.003 | 1.003 | 1.002 | Noise scale for churn. Leave near 1.0. |
| `s_stage2` | **0.93** | **0.95** | **1.0** | Creative licence for micro-texture. 1.0 = anchored to source. 0.90–0.95 = generates fine texture from prompt. |
| `s_stage1` | 1.0 | 1.0 | 1.0 | Stage-1 anchor strength. Leave at 1.0. |
| `restore_cfg` | 1.0 | 1.6 | 2.2 | Face/structure restoration strength. Higher = faces preserved but less enhanced. |

#### Node: SUPIR_conditioner — prompts

The positive prompt drives micro-texture generation. Key phrases that matter: `skin pore detailing`, `fine thread texture and fabric weave visible on cloth`, `individual hair strands`. Remove phrases you don't want synthesised (e.g. remove fabric terms for portraits with no clothing).

The negative prompt prevents hallucination. Keep `lace, fishnet, mesh, see-through fabric` here for NSFW inputs.

---

#### SUPIR Troubleshooting

| Symptom | Fix |
|---|---|
| **Skin looks plastic / no pores** | Lower `s_stage2` to 0.90–0.93. Raise `cfg_end` to 4.0+. Ensure `steps` ≥ 50. |
| **Not enough fabric / hair texture** | More `steps`. Raise `cfg_end`. Lower `s_stage2` toward 0.90. |
| **Over-sharpened / haloed edges** | Lower `cfg_start` and `cfg_end`. Raise `s_stage2` toward 1.0. |
| **Face distorted or melting** | Raise `restore_cfg` to 1.6+. Lower `cfg_start`. |
| **Lace / mesh hallucinating on smooth areas** | Add to negative prompt. Raise `restore_cfg` to 1.4+. Raise `s_stage2` to 1.0. |
| **Artefacts / noise blobs** | Lower `s_churn`. Switch to clean preset (RestoreDPMPP2MSampler). |
| **Too slow** | Use the clean preset (32 steps, faster sampler). Use Clarity instead for <6GB VRAM. |

---

### Clarity vs SUPIR — which to use

| | Clarity | SUPIR |
|---|---|---|
| VRAM | ~6GB | ~16GB |
| Speed (4090) | 15–30s | 60–250s |
| Style | Adds diffusion texture on top of ESRGAN | Full SDXL hallucination of micro-detail |
| Risk of hallucination | Low | Medium (tunable with `s_stage2`) |
| Best result for portraits | Equal to SUPIR for most cases | Better for extreme hero shots |
| ESRGAN model matters | Yes — pick the right one | No — SUPIR does its own SR internally |

---

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
