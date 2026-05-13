# Ignition LTX - ComfyUI for LTX-2.3 Video Generation
# Single-stage build: no SageAttention compilation needed for LTX-2.3
# LTX-2.3 is natively supported in ComfyUI core; ComfyUI-LTXVideo provides extra nodes

FROM nvidia/cuda:13.0.3-cudnn-runtime-ubuntu24.04

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

# System deps
# gcc + python3-dev: needed by some pip packages that compile native extensions
# git + aria2 kept: install-performance-plugins.sh and model downloader use them at runtime
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

# PyTorch nightly cu130 — LTX-2.3 requires CUDA > 12.7 and PyTorch ~2.7; nightly cu130 satisfies both
# Switch to stable cu130 once wheels are published at https://download.pytorch.org/whl/cu130
RUN pip install --no-cache-dir --pre torch torchvision torchaudio \
    --index-url https://download.pytorch.org/whl/nightly/cu130

# Verify PyTorch (fail build immediately if broken)
RUN python3 -c "import torch; v=torch.__version__; print(f'✅ PyTorch: {v} CUDA: {torch.version.cuda}'); assert torch.version.cuda is not None, 'No CUDA'"

# Runtime Python libraries
RUN pip install --no-cache-dir \
    pyyaml gdown \
    requests aiohttp aiofiles \
    huggingface-hub tqdm \
    pillow numpy opencv-python \
    psutil onnx onnxruntime \
    sentencepiece

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

# ComfyUI-LTXVideo — official Lightricks node pack for LTX-2.3 workflows
# LTX-2.3 is in ComfyUI core; this adds extra nodes + example workflows
RUN cd /workspace/ComfyUI/custom_nodes && \
    git clone https://github.com/Lightricks/ComfyUI-LTXVideo.git && \
    cd ComfyUI-LTXVideo && \
    pip install --no-cache-dir -r requirements.txt

# RES4LYF — advanced samplers (ClownSampler_Beta) used in LTX-2.3 Full workflow
RUN cd /workspace/ComfyUI/custom_nodes && \
    git clone https://github.com/ClownsharkBatwing/RES4LYF.git && \
    cd RES4LYF && \
    pip install --no-cache-dir -r requirements.txt

# ComfyUI_LTX2_SM — GGUF-based LTX-2.3 loader; required for Sulphur 2 GGUF workflows
# Uses diffusers-style GGUF loading — NOT compatible with Kijai/City96 GGUF nodes
RUN cd /workspace/ComfyUI/custom_nodes && \
    git clone https://github.com/smthemex/ComfyUI_LTX2_SM.git && \
    cd ComfyUI_LTX2_SM && \
    pip install --no-cache-dir -r requirements.txt

# ComfyUI-Frame-Interpolation — FrameInterpolate nodes used in Sulphur 2 GGUF workflow
# Uses requirements-no-cupy.txt — cupy has no cu130 wheel and isn't needed for film_net
RUN cd /workspace/ComfyUI/custom_nodes && \
    git clone https://github.com/Fannovel16/ComfyUI-Frame-Interpolation.git && \
    cd ComfyUI-Frame-Interpolation && \
    pip install --no-cache-dir -r requirements-no-cupy.txt

# Create model directories
# latent_upscale_models: LTX-2.3 spatial and temporal upscalers
# gguf: GGUF-format transformers and text encoders (Sulphur 2, vanilla LTX GGUF)
# frame_interpolation: film_net models for ComfyUI-Frame-Interpolation
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
    /workspace/ComfyUI/models/unet \
    /workspace/ComfyUI/models/latent_upscale_models \
    /workspace/ComfyUI/models/gguf \
    /workspace/ComfyUI/models/frame_interpolation

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
