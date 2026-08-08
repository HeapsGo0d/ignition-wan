# Ignition H3 - ComfyUI for MiniMax H3 video + native audio generation
# Single-stage build, and no custom node packs at all: every node the H3
# workflows use ships in ComfyUI core (comfy_extras/nodes_minimax_h3.py,
# nodes_video.py, nodes_math.py, nodes_resolution.py, nodes_audio.py).

# Base is the plain runtime, NOT the -cudnn variant. The PyTorch wheel bundles
# its own cuDNN; shipping the base image's copy as well gives two installs, and
# whichever one the loader picks for libcudnn.so.9 then fails to dlopen the
# other's sublibraries:
#   RuntimeError: CUDNN_BACKEND_TENSOR_DESCRIPTOR cudnnFinalize failed
#   cudnn_status: CUDNN_STATUS_SUBLIBRARY_LOADING_FAILED
# That surfaced on v2.0.0-h3 at the first conv3d (the Qwen3-VL vision tower's
# patch_embed), long after gpu_preflight passed — torch.cuda.is_available()
# never touches cuDNN. One cuDNN only.
FROM nvidia/cuda:13.0.3-runtime-ubuntu24.04

# LD_LIBRARY_PATH deliberately does NOT include /usr/lib/x86_64-linux-gnu:
# it is already on the default loader path via ldconfig, and prepending it put
# a system cuDNN ahead of the wheel's. /usr/local/nvidia/lib64 is where RunPod
# injects the driver libraries.
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    NVIDIA_VISIBLE_DEVICES=all \
    NVIDIA_DRIVER_CAPABILITIES=compute,utility \
    LD_LIBRARY_PATH=/usr/local/nvidia/lib64:$LD_LIBRARY_PATH \
    CUDA_DEVICE_ORDER=PCI_BUS_ID \
    PATH="/opt/venv/bin:$PATH" \
    XDG_CACHE_HOME=/workspace/.cache \
    HF_HOME=/workspace/.cache/huggingface \
    HUGGINGFACE_HUB_CACHE=/workspace/.cache/huggingface

WORKDIR /workspace

# System deps
# gcc + python3-dev: needed by some pip packages that compile native extensions
# git + aria2 kept: aria2c does all model downloads; git is used by ComfyUI-Manager
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-pip python3-venv python3-dev \
    curl ffmpeg git aria2 git-lfs wget vim \
    iproute2 net-tools \
    libgl1 libglib2.0-0 \
    gcc \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Portable venv
RUN python3 -m venv --copies /opt/venv

# Core tooling
RUN pip install --no-cache-dir packaging setuptools wheel

# PyTorch nightly cu130 — needed for the optimized fp8/int8 CUDA kernels
# comfy-kitchen uses; on cu128 it falls back to eager dequantization.
# Switch to stable cu130 once wheels are published at https://download.pytorch.org/whl/cu130
RUN pip install --no-cache-dir --pre torch torchvision torchaudio \
    --index-url https://download.pytorch.org/whl/nightly/cu130

# Verify PyTorch (fail build immediately if broken)
RUN python3 -c "import torch; v=torch.__version__; print(f'✅ PyTorch: {v} CUDA: {torch.version.cuda}'); assert torch.version.cuda is not None, 'No CUDA'"

# Verify there is exactly one cuDNN and it is the wheel's.
# No GPU in the build runner, so this checks linkage and provenance, not kernels:
#   1. the wheel actually ships cuDNN (if a future wheel stops bundling it, the
#      plain -runtime base would leave us with none — fail here, not on a pod)
#   2. every sublibrary is present alongside it
#   3. no second copy in the system lib dir to be picked up instead
RUN python3 - <<'PY'
import glob, pathlib, torch
lib = pathlib.Path(torch.__file__).parent.parent / "nvidia/cudnn/lib"
libs = sorted(p.name for p in lib.glob("libcudnn*.so*")) if lib.is_dir() else []
assert libs, f"PyTorch wheel bundles no cuDNN at {lib} — re-add a -cudnn base image"
subs = [n for n in libs if n.startswith("libcudnn_")]
assert subs, f"cuDNN sublibraries missing in {lib}: {libs}"
system = glob.glob("/usr/lib/x86_64-linux-gnu/libcudnn*.so*")
assert not system, f"second cuDNN found in system lib dir: {system}"
print(f"✅ cuDNN: {torch.backends.cudnn.version()} from wheel, {len(subs)} sublibraries, no system copy")
PY

# Runtime Python libraries
# Our scripts fetch with aria2c and use only `requests` directly (see
# scripts/download_utils.py). Everything else that used to be listed here
# — gdown, opencv, onnx/onnxruntime, sentencepiece, pillow, psutil, tqdm —
# existed for custom node packs that this image no longer installs.
# ComfyUI's own requirements.txt covers the rest.
RUN pip install --no-cache-dir requests

# ComfyUI — filter torch packages to prevent nightly downgrade
RUN git clone https://github.com/comfyanonymous/ComfyUI.git /workspace/ComfyUI && \
    cd /workspace/ComfyUI && \
    grep -v "^torch$" requirements.txt | \
    grep -v "^torchvision$" | \
    grep -v "^torchaudio$" | \
    pip install --no-cache-dir -r /dev/stdin

# ComfyUI-Manager
RUN cd /workspace/ComfyUI/custom_nodes && \
    git clone https://github.com/Comfy-Org/ComfyUI-Manager.git && \
    cd ComfyUI-Manager && \
    pip install --no-cache-dir -r requirements.txt

# No custom node packs.
#
# Every node type in the shipped H3 workflows resolves to ComfyUI core:
#   MiniMaxH3ImageToVideo, MiniMaxH3ReferenceToVideo,
#   MiniMaxH3SigmaShift, EmptyMiniMaxH3LatentAV   comfy_extras/nodes_minimax_h3.py
#   SaveVideo, CreateVideo                        comfy_extras/nodes_video.py
#   ComfyMathExpression                           comfy_extras/nodes_math.py
#   ResolutionSelector                            comfy_extras/nodes_resolution.py
#   VAEDecodeAudio                                comfy_extras/nodes_audio.py
#   LoraLoaderModelOnly, GetImageSize, ...        nodes.py
#
# ComfyMathExpression and ResolutionSelector in particular were third-party
# (evanspearman/ComfyMath, ControlAltAI) when the LTX branch shipped and are
# core now — do not re-add those packs without checking core first.
# scripts/check_workflows.py enforces this at build time.

# Create model directories — keep in sync with setup_storage() in scripts/startup.sh
RUN mkdir -p \
    /workspace/ComfyUI/models/diffusion_models \
    /workspace/ComfyUI/models/text_encoders \
    /workspace/ComfyUI/models/vae \
    /workspace/ComfyUI/models/loras \
    /workspace/ComfyUI/models/checkpoints \
    /workspace/ComfyUI/models/upscale_models \
    /workspace/ComfyUI/models/embeddings \
    /workspace/ComfyUI/models/controlnet \
    /workspace/ComfyUI/models/clip \
    /workspace/ComfyUI/models/clip_vision

# Create HuggingFace cache directory
RUN mkdir -p /workspace/.cache/huggingface

# Install filebrowser — pinned v2.63.3 to avoid GitHub API rate-limit on get.sh
RUN curl -fsSL -o /tmp/filebrowser.tar.gz \
    "https://github.com/filebrowser/filebrowser/releases/download/v2.63.3/linux-amd64-filebrowser.tar.gz" \
    && tar -xzf /tmp/filebrowser.tar.gz -C /usr/local/bin filebrowser \
    && rm /tmp/filebrowser.tar.gz

# Copy scripts and workflows
COPY scripts/ /workspace/scripts/
COPY workflows/ /workspace/ComfyUI/user/default/workflows/
RUN chmod +x /workspace/scripts/*.sh /workspace/scripts/privacy/*.sh && \
    chmod +x /workspace/scripts/restart-comfyui.sh /workspace/scripts/stop-pod.sh

# Fail the build on a workflow/registry mismatch rather than discovering it on
# a pod 78 minutes later. Every load-blocker this project has shipped was one.
COPY workflows/ /tmp/check/workflows/
RUN python3 /workspace/scripts/check_workflows.py /tmp/check/workflows/*.json && \
    rm -rf /tmp/check

# Install nuke script
COPY scripts/nuke /usr/local/bin/nuke
RUN chmod +x /usr/local/bin/nuke

# Environment defaults
ENV CIVITAI_MODELS="" \
    CIVITAI_LORAS="" \
    CIVITAI_VAES="" \
    HUGGINGFACE_MODELS="" \
    CIVITAI_TOKEN="" \
    HF_TOKEN="" \
    FILEBROWSER_PASSWORD="runpod" \
    COMFYUI_PORT="8188" \
    FILEBROWSER_PORT="8080"

EXPOSE 8188 8080

HEALTHCHECK --interval=30s --timeout=10s --start-period=5m --retries=3 \
  CMD curl -f http://127.0.0.1:8188/ || exit 1

ENTRYPOINT ["/workspace/scripts/startup.sh"]
