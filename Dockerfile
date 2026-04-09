# Ignition WAN - ComfyUI for WAN 2.2 Video Generation
# Optimized for RTX 5090 and RunPod deployment
# Using NVIDIA's official PyTorch container with RTX 5090 support

FROM pytorch/pytorch:2.5.1-cuda12.4-cudnn9-devel AS base

# Consolidated environment variables
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    NVIDIA_VISIBLE_DEVICES=all \
    NVIDIA_DRIVER_CAPABILITIES=compute,utility \
    LD_LIBRARY_PATH=/usr/local/nvidia/lib64:/usr/lib/x86_64-linux-gnu:$LD_LIBRARY_PATH \
    CUDA_DEVICE_ORDER=PCI_BUS_ID \
    PIP_NO_CACHE_DIR=1 \
    XDG_CACHE_HOME=/workspace/.cache \
    HF_HOME=/workspace/.cache/huggingface \
    HUGGINGFACE_HUB_CACHE=/workspace/.cache/huggingface

# Set working directory
WORKDIR /workspace

# Install additional system dependencies including aria2 for downloads
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ffmpeg git aria2 git-lfs wget vim \
    iproute2 net-tools \
    libgl1-mesa-glx libglib2.0-0 \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Core Python tooling (PyTorch already included in base image)
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install packaging setuptools wheel

# Remove base image PyTorch to ensure clean nightly installation
RUN pip uninstall -y torch torchvision torchaudio

# Install PyTorch nightly with CUDA 12.8 for RTX 5090 Blackwell support
# Let pip install required CUDA dependencies
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --pre --force-reinstall \
    torch torchvision torchaudio --index-url https://download.pytorch.org/whl/nightly/cu128

# Verify nightly installation succeeded (build fails if not)
RUN python3 -c "import torch; v=torch.__version__; print(f'✅ PyTorch: {v} CUDA: {torch.version.cuda}'); assert 'dev' in v, f'Expected nightly, got: {v}'"

# Runtime libraries (triton comes with PyTorch nightly)
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install pyyaml gdown

# Install ComfyUI directly (more reliable than comfy-cli)
# Filter out torch packages to prevent downgrade from nightly (but keep torchsde)
RUN git clone https://github.com/comfyanonymous/ComfyUI.git /workspace/ComfyUI && \
    cd /workspace/ComfyUI && \
    grep -v "^torch$" requirements.txt | \
    grep -v "^torchvision$" | \
    grep -v "^torchaudio$" | \
    pip install --no-cache-dir -r /dev/stdin

# Install ComfyUI-Manager for custom node management
RUN cd /workspace/ComfyUI/custom_nodes && \
    git clone https://github.com/Comfy-Org/ComfyUI-Manager.git && \
    cd ComfyUI-Manager && \
    pip install --no-cache-dir -r requirements.txt

# Install ComfyUI-WanVideoWrapper and KJNodes for WAN 2.2 video generation
RUN cd /workspace/ComfyUI/custom_nodes && \
    git clone https://github.com/kijai/ComfyUI-WanVideoWrapper.git && \
    cd ComfyUI-WanVideoWrapper && \
    pip install --no-cache-dir -r requirements.txt && \
    cd /workspace/ComfyUI/custom_nodes && \
    git clone https://github.com/kijai/ComfyUI-KJNodes.git && \
    cd ComfyUI-KJNodes && \
    pip install --no-cache-dir -r requirements.txt

# Install WanMoeKSampler - auto-switches high/low noise models at correct diffusion timestep
RUN cd /workspace/ComfyUI/custom_nodes && \
    git clone https://github.com/stduhpf/ComfyUI-WanMoeKSampler.git

# Install additional dependencies for Ignition
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install \
        requests \
        aiohttp \
        aiofiles \
        huggingface-hub \
        tqdm \
        pillow \
        numpy \
        opencv-python \
        psutil \
        onnx \
        onnxruntime

FROM base AS final

# Final stage setup

# Create model directories (explicit paths - /bin/sh doesn't support brace expansion)
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

# Install filebrowser for file management
RUN curl -fsSL https://raw.githubusercontent.com/filebrowser/get/master/get.sh | bash

# Copy our scripts and workflows
COPY scripts/ /workspace/scripts/
COPY workflows/ /workspace/ComfyUI/user/default/workflows/
RUN chmod +x /workspace/scripts/*.sh /workspace/scripts/privacy/*.sh && \
    chmod +x /workspace/scripts/restart-comfyui.sh /workspace/scripts/stop-pod.sh

# Install nuke script for nuclear cleanup
COPY scripts/nuke /usr/local/bin/nuke
RUN chmod +x /usr/local/bin/nuke

# Note: Performance plugins are installed at runtime via startup.sh
# This ensures reliable installation with proper volume context

# Set environment defaults (simplified approach)
ENV CIVITAI_MODELS=""
ENV CIVITAI_LORAS=""
ENV CIVITAI_VAES=""
ENV HUGGINGFACE_MODELS=""
ENV CIVITAI_TOKEN=""
ENV HF_TOKEN=""
ENV FILEBROWSER_PASSWORD="runpod"
ENV COMFYUI_PORT="8188"
ENV FILEBROWSER_PORT="8080"

# Expose ports
EXPOSE 8188 8080

# Add basic healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=5m --retries=3 \
  CMD curl -f http://127.0.0.1:8188/ || exit 1

# Set entrypoint
ENTRYPOINT ["/workspace/scripts/startup.sh"]