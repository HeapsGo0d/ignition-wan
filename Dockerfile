# Ignition WAN - ComfyUI for WAN 2.2 Video Generation
# Two-stage build: devel for compilation, runtime for deployment
# Eliminates double-torch layer bloat + strips compiler toolchain from final image
# SageAttention2++ compiled at build time for RTX 5090 (sm_120) — ready on first boot

# ── Stage 1: Builder ──────────────────────────────────────────────────────────
# Full devel image: needs nvcc to compile SageAttention CUDA kernels
FROM nvidia/cuda:12.8.1-cudnn-devel-ubuntu24.04 AS builder

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /workspace

# System deps (python3-dev needed for SA compilation)
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-pip python3-venv python3-dev \
    curl ffmpeg git aria2 git-lfs wget \
    libgl1 libglib2.0-0 \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Portable venv: --copies avoids symlinks to system Python, making it safe to
# COPY between stages without the original Python binary being present
RUN python3 -m venv --copies /opt/venv

# Core tooling
RUN pip install --no-cache-dir packaging setuptools wheel

# Install PyTorch nightly with CUDA 12.8 — installed once, no uninstall dance
RUN pip install --no-cache-dir --pre torch torchvision torchaudio \
    --index-url https://download.pytorch.org/whl/nightly/cu128

# Verify PyTorch (fail build immediately if broken)
RUN python3 -c "import torch; v=torch.__version__; print(f'✅ PyTorch: {v} CUDA: {torch.version.cuda}'); assert torch.version.cuda is not None, 'No CUDA'"

# Runtime Python libraries
RUN pip install --no-cache-dir \
    pyyaml gdown \
    requests aiohttp aiofiles \
    huggingface-hub tqdm \
    pillow numpy opencv-python \
    psutil onnx onnxruntime

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

# ComfyUI-WanVideoWrapper + KJNodes (WAN 2.2 video generation + attention patching)
RUN cd /workspace/ComfyUI/custom_nodes && \
    git clone https://github.com/kijai/ComfyUI-WanVideoWrapper.git && \
    cd ComfyUI-WanVideoWrapper && \
    pip install --no-cache-dir -r requirements.txt && \
    cd /workspace/ComfyUI/custom_nodes && \
    git clone https://github.com/kijai/ComfyUI-KJNodes.git && \
    cd ComfyUI-KJNodes && \
    pip install --no-cache-dir -r requirements.txt

# WanMoeKSampler — auto-switches high/low noise models at correct diffusion timestep
RUN cd /workspace/ComfyUI/custom_nodes && \
    git clone https://github.com/stduhpf/ComfyUI-WanMoeKSampler.git

# ComfyUI-Frame-Interpolation — RIFE VFI for smooth 60fps output
# Pinned to 26545cc (2026-04-11)
RUN cd /workspace/ComfyUI/custom_nodes && \
    git clone https://github.com/Fannovel16/ComfyUI-Frame-Interpolation.git && \
    git -C ComfyUI-Frame-Interpolation checkout 26545cc2dd95bc3d27f056016300673bdeee78f5 && \
    cd ComfyUI-Frame-Interpolation && \
    pip install --no-cache-dir -r requirements-no-cupy.txt

# Compile SageAttention2++ for RTX 5090 Blackwell (sm_120)
# AOT compile — no physical GPU needed, TORCH_CUDA_ARCH_LIST specifies the target
# nvcc is available in this devel stage; will NOT be present in final runtime image
# v2.x is not on PyPI — install from source tag
RUN git clone --depth 1 --branch v2.2.0 https://github.com/thu-ml/SageAttention /tmp/sageattention && \
    TORCH_CUDA_ARCH_LIST="12.0" MAX_JOBS=8 \
    pip install --no-cache-dir --no-build-isolation /tmp/sageattention && \
    rm -rf /tmp/sageattention

# Compile SageAttention3 for RTX 5090 Blackwell (sm_120)
# SA3 uses native Blackwell CUDA kernels — no Triton JIT at runtime (unlike SA2++)
# SA3 lives in a subdirectory of main branch, not in any release tag
# Pinned to d1a57a5 (2026-01-17) — last meaningful SA3 change: c03f15f (2025-12-22)
RUN git clone https://github.com/thu-ml/SageAttention /tmp/sageattention3 && \
    git -C /tmp/sageattention3 checkout d1a57a546c3d395b1ffcbeecc66d81db76f3b4b5 && \
    sed -i 's/cc_major, cc_minor = torch.cuda.get_device_capability()/cc_major, cc_minor = 12, 0/' \
        /tmp/sageattention3/sageattention3_blackwell/setup.py && \
    TORCH_CUDA_ARCH_LIST="12.0" MAX_JOBS=8 \
    pip install --no-cache-dir --no-build-isolation /tmp/sageattention3/sageattention3_blackwell && \
    rm -rf /tmp/sageattention3

# Smoke test: verify both SA2++ and SA3 compiled correctly and are importable
RUN python3 -c "import torch; print(f'PyTorch {torch.__version__} CUDA {torch.version.cuda}'); import sageattention; from sageattention import sageattn_qk_int8_pv_fp16_cuda; print('SA2++ import OK'); from sageattn3 import sageattn3_blackwell; print('SA3 Blackwell import OK')"


# ── Stage 2: Final (runtime) ──────────────────────────────────────────────────
# Runtime image: no compiler toolchain — strips nvcc, CUDA headers, static libs
FROM nvidia/cuda:12.8.1-cudnn-runtime-ubuntu24.04 AS final

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    NVIDIA_VISIBLE_DEVICES=all \
    NVIDIA_DRIVER_CAPABILITIES=compute,utility \
    LD_LIBRARY_PATH=/usr/local/nvidia/lib64:/usr/lib/x86_64-linux-gnu:$LD_LIBRARY_PATH \
    CUDA_DEVICE_ORDER=PCI_BUS_ID \
    PATH="/opt/venv/bin:$PATH" \
    XDG_CACHE_HOME=/workspace/.cache \
    HF_HOME=/workspace/.cache/huggingface \
    HUGGINGFACE_HUB_CACHE=/workspace/.cache/huggingface

WORKDIR /workspace

# Runtime system deps
# git + aria2 kept: install-performance-plugins.sh uses git clone on first boot
# curl kept: filebrowser install + healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    curl ffmpeg git aria2 git-lfs wget vim \
    iproute2 net-tools \
    libgl1 libglib2.0-0 \
    gcc python3-dev \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Copy compiled Python environment (torch + SA + all packages)
COPY --from=builder /opt/venv /opt/venv

# Copy ComfyUI and custom nodes
COPY --from=builder /workspace/ComfyUI /workspace/ComfyUI

# Create model directories
RUN mkdir -p \
    /workspace/ComfyUI/models/checkpoints \
    /workspace/ComfyUI/models/loras \
    /workspace/ComfyUI/models/vae \
    /workspace/ComfyUI/models/upscale_models \
    /workspace/ComfyUI/models/embeddings \
    /workspace/ComfyUI/models/controlnet \
    /workspace/ComfyUI/models/diffusion_models \
    /workspace/ComfyUI/models/text_encoders \
    /workspace/ComfyUI/models/clip \
    /workspace/ComfyUI/models/clip_vision \
    /workspace/ComfyUI/models/unet

# Create HuggingFace cache directory
RUN mkdir -p /workspace/.cache/huggingface

# Install filebrowser
RUN curl -fsSL https://raw.githubusercontent.com/filebrowser/get/master/get.sh | bash

# Copy scripts and workflows
COPY scripts/ /workspace/scripts/
COPY workflows/ /workspace/ComfyUI/user/default/workflows/
RUN chmod +x /workspace/scripts/*.sh /workspace/scripts/privacy/*.sh && \
    chmod +x /workspace/scripts/restart-comfyui.sh /workspace/scripts/stop-pod.sh

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
    ENABLE_SAGEATTN="true" \
    COMFYUI_PORT="8188" \
    FILEBROWSER_PORT="8080"

EXPOSE 8188 8080

HEALTHCHECK --interval=30s --timeout=10s --start-period=5m --retries=3 \
  CMD curl -f http://127.0.0.1:8188/ || exit 1

ENTRYPOINT ["/workspace/scripts/startup.sh"]
