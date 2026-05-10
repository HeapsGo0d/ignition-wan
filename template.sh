#!/bin/bash
# Ignition WAN RunPod Template Creator
# Creates a RunPod template with pre-configured settings for WAN 2.2 video generation
# Supports both local file generation and direct RunPod API deployment

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
DOCKER_IMAGE="heapsgo0d/ignition-wan:latest"
TEMPLATE_NAME="Ignition WAN Latest"
TEMPLATE_DESCRIPTION="ComfyUI for WAN 2.2 video generation (T2V + I2V) with safe restart architecture and RTX 5090 support"

# Disk defaults (can be overridden interactively or via env)
CONTAINER_DISK_GB="${CONTAINER_DISK_GB:-200}"
VOLUME_GB="${VOLUME_GB:-0}"

# Check for command line arguments
DEPLOY_MODE="local"  # Default to local file generation
if [[ "$1" == "--deploy" || "$1" == "-d" ]]; then
    DEPLOY_MODE="api"
fi

# Print banner
print_banner() {
    echo -e "${CYAN}"
    echo "╔═══════════════════════════════════════════╗"
    echo "║        🎬 IGNITION WAN TEMPLATE          ║"
    echo "║     RunPod WAN 2.2 Template Creator       ║"
    echo "╚═══════════════════════════════════════════╝"
    echo -e "${NC}"
}

# Print usage information
print_usage() {
    echo -e "${YELLOW}📋 Ignition RunPod Template Creator${NC}"
    echo ""
    
    if [[ "$DEPLOY_MODE" == "api" ]]; then
        echo -e "${GREEN}🚀 API Deployment Mode${NC} - Will create template directly in RunPod"
        echo -e "${BLUE}Requirements:${NC}"
        echo "  • RunPod API key (set RUNPOD_API_KEY environment variable)"
        echo "  • curl command available"
        echo ""
    else
        echo -e "${BLUE}📁 Local File Mode${NC} - Will generate files for manual upload"
        echo -e "${YELLOW}💡 Tip: Use './template.sh --deploy' for automatic deployment${NC}"
        echo ""
    fi
    
    echo -e "${BLUE}What you'll configure:${NC}"
    echo "  • CivitAI model version IDs (optional)"
    echo "  • HuggingFace repository names (optional)"
    echo "  • API tokens for faster downloads (optional)"
    echo "  • Storage and security settings"
    echo ""
    echo -e "${GREEN}Template will include:${NC}"
    echo "  ✅ Pre-configured Docker image"
    echo "  ✅ Exposed ports (8188 for ComfyUI, 8080 for file browser)"
    echo "  ✅ Environment variables for model configuration"
    echo "  ✅ GPU support enabled"
    echo "  ✅ Network volume support"
    echo ""
}

# Check API key if in deploy mode
check_api_requirements() {
    if [[ "$DEPLOY_MODE" == "api" ]]; then
        if [[ -z "$RUNPOD_API_KEY" ]]; then
            echo -e "${RED}❌ Error: RUNPOD_API_KEY environment variable not set${NC}"
            echo ""
            echo -e "${YELLOW}To use API deployment mode:${NC}"
            echo "1. Get your API key from RunPod → Settings → API Keys"
            echo "2. Export it: export RUNPOD_API_KEY=\"your_key_here\""
            echo "3. Run the script again: ./template.sh --deploy"
            echo ""
            echo -e "${BLUE}Or use local file mode: ./template.sh${NC}"
            exit 1
        fi
        
        # curl must exist
        if ! command -v curl &> /dev/null; then
            echo -e "${RED}❌ Error: curl command not found${NC}"
            echo "Please install curl to use API deployment mode"
            exit 1
        fi

        # jq is optional
        if ! command -v jq &> /dev/null; then
            echo -e "${YELLOW}⚠️  jq not found — will show raw JSON and use a basic parser fallback${NC}"
        else
            echo -e "${GREEN}✅ jq detected — pretty JSON parsing enabled${NC}"
        fi

        echo -e "${GREEN}✅ API key found, deployment mode ready${NC}"
        echo ""
    fi
}

# Get user input for configuration
get_configuration() {
    echo -e "${YELLOW}🔧 Configuration Setup${NC}"
    echo ""
    
    # Version input (easy mode)
    echo -e "${BLUE}Version:${NC}"
    read -p "Enter version tag (e.g., v1.0.12) [latest]: " version_input
    VERSION_TAG=${version_input:-latest}
    
    # Auto-generate image and template names based on version
    if [[ "$VERSION_TAG" == "latest" ]]; then
        DOCKER_IMAGE="heapsgo0d/ignition-wan:latest"
        TEMPLATE_NAME="Ignition WAN Latest"
    else
        DOCKER_IMAGE="heapsgo0d/ignition-wan:$VERSION_TAG"
        TEMPLATE_NAME="Ignition WAN $VERSION_TAG"
    fi
    
    echo "  → Docker Image: $DOCKER_IMAGE"
    echo "  → Template Name: $TEMPLATE_NAME"
    echo ""
    
    # CivitAI Models (optional extras - LoRAs etc)
    echo -e "${BLUE}CivitAI Models (optional - for extra checkpoints):${NC}"
    read -p "CivitAI model IDs [leave blank for none]: " input_civitai
    CIVITAI_MODELS=${input_civitai:-""}
    echo ""

    # CivitAI LoRAs with default
    echo -e "${BLUE}CivitAI LoRAs (optional):${NC}"
    read -p "CivitAI LoRA IDs [leave blank for none]: " input_loras
    CIVITAI_LORAS=${input_loras:-""}
    echo ""

    # CivitAI VAEs (optional)
    echo -e "${BLUE}CivitAI VAEs (optional):${NC}"
    read -p "CivitAI VAE IDs [leave blank for none]: " input_vaes
    CIVITAI_VAES=${input_vaes:-""}
    echo ""

    # WAN 2.2 Model Preset Selection
    echo -e "${BLUE}WAN 2.2 Video Model Preset:${NC}"
    echo "  1) T2V bundle (text-to-video, both noise variants + LightX2V LoRAs, ~24GB)"
    echo "  2) I2V bundle (image-to-video, both noise variants + LightX2V LoRAs + CLIP, ~24GB)"
    echo "  3) Full bundle (T2V + I2V everything, ~45GB)"
    echo "  4) Full + NSFW LoRAs (T2V + I2V + NSFW-22-H/L LoRAs, ~46GB)"
    echo "  --- NSFW/Uncensored models ---"
    echo "  5) FX-FeiHou Remix NSFW I2V v3.0 (high + low + CLIP, ~24GB)"
    echo "  6) Phr00t MEGA NSFW v12.2 (unified I2V+T2V + CLIP, ~15GB)"
    echo "  7) NSFW I2V Full (all 3 NSFW I2V workflows, ~70GB)"
    echo "  --- Image upscaling ---"
    echo "  8) Clarity bundle (DreamShaper SD1.5 + ControlNet Tile fp16, ~2.9GB)"
    echo "  9) Custom (manual entry)"
    read -p "Select preset [1]: " model_preset

    case ${model_preset:-1} in
        1)
            HUGGINGFACE_MODELS="wan2.2_t2v_bundle"
            echo "  → Selected: T2V bundle"
            ;;
        2)
            HUGGINGFACE_MODELS="wan2.2_i2v_bundle"
            echo "  → Selected: I2V bundle"
            ;;
        3)
            HUGGINGFACE_MODELS="wan2.2_full_bundle"
            echo "  → Selected: Full bundle (T2V + I2V)"
            ;;
        4)
            HUGGINGFACE_MODELS="wan2.2_full_bundle,nsfw_lora_bundle"
            echo "  → Selected: Full bundle + NSFW LoRAs"
            ;;
        5)
            HUGGINGFACE_MODELS="remix_nsfw_i2v_bundle"
            echo "  → Selected: FX-FeiHou Remix NSFW I2V v3.0"
            ;;
        6)
            HUGGINGFACE_MODELS="phr00t_mega_nsfw_bundle"
            echo "  → Selected: Phr00t MEGA NSFW v12.2"
            echo "     Sampler tip: dpmpp_sde / beta for best motion on MEGA v12.2"
            ;;
        7)
            HUGGINGFACE_MODELS="nsfw_i2v_full_bundle"
            echo "  → Selected: NSFW I2V Full (~70GB — Remix v3.0 + MEGA + official SFW base + LoRAs)"
            ;;
        8)
            HUGGINGFACE_MODELS="clarity_bundle"
            echo "  → Selected: Clarity bundle (~2.9GB — DreamShaper SD1.5 + ControlNet Tile fp16)"
            echo "     Note: 4x_NMKD-Siax upscaler auto-downloaded by startup.sh"
            ;;
        9)
            read -p "Enter model keys (comma-separated): " input_hf
            HUGGINGFACE_MODELS=${input_hf}
            echo "  → Selected: Custom"
            ;;
        *)
            HUGGINGFACE_MODELS="wan2.2_t2v_bundle"
            echo "  → Invalid selection, defaulting to T2V bundle"
            ;;
    esac
    echo ""

    # Security settings with default
    echo -e "${BLUE}Security Settings:${NC}"
    read -p "File browser password [runpod]: " input_password
    FILEBROWSER_PASSWORD=${input_password:-runpod}
    echo ""

    # Note about storage
    echo -e "${BLUE}Storage Note:${NC}"
    echo "Persistence handled by RunPod volume settings:"
    echo "  • Volume 0GB = Ephemeral (models download each time)"  
    echo "  • Volume >0GB = Persistent (models survive restarts)"
    echo ""

    # Disk settings
    echo -e "${BLUE}Disk Settings:${NC}"
    read -p "Container disk size in GB [${CONTAINER_DISK_GB}]: " tmp_disk
    CONTAINER_DISK_GB=${tmp_disk:-$CONTAINER_DISK_GB}
    read -p "Default volume size in GB (0 = ephemeral) [${VOLUME_GB}]: " tmp_vol
    VOLUME_GB=${tmp_vol:-$VOLUME_GB}
    echo ""

}

# Generate template JSON (manual upload option; schema differs from API)
generate_template() {
    cat > ignition_template.json << EOF
{
  "name": "$TEMPLATE_NAME",
  "description": "$TEMPLATE_DESCRIPTION",
  "dockerImage": "$DOCKER_IMAGE",
  "ports": [
    {
      "privatePort": 8188,
      "publicPort": 8188,
      "type": "http",
      "description": "ComfyUI Web Interface"
    },
    {
      "privatePort": 8080,
      "publicPort": 8080,
      "type": "http",
      "description": "File Browser"
    }
  ],
  "volumeMounts": [
    {
      "containerPath": "/workspace",
      "name": "workspace"
    }
  ],
  "environmentVariables": [
    {
      "key": "CIVITAI_MODELS",
      "value": "$CIVITAI_MODELS",
      "description": "Comma-separated CivitAI model version IDs"
    },
    {
      "key": "CIVITAI_LORAS",
      "value": "$CIVITAI_LORAS",
      "description": "Comma-separated CivitAI LoRA model version IDs"
    },
    {
      "key": "CIVITAI_VAES",
      "value": "$CIVITAI_VAES",
      "description": "Comma-separated CivitAI VAE model version IDs"
    },
    {
      "key": "HUGGINGFACE_MODELS",
      "value": "$HUGGINGFACE_MODELS",
      "description": "WAN 2.2 model preset or comma-separated model keys. Bundles: wan2.2_t2v_bundle, wan2.2_i2v_bundle, wan2.2_full_bundle"
    },
    {
      "key": "CIVITAI_TOKEN",
      "value": "",
      "description": "CivitAI API token (optional, for faster downloads)"
    },
    {
      "key": "HF_TOKEN",
      "value": "",
      "description": "HuggingFace API token (optional, for private repos)"
    },
    {
      "key": "FILEBROWSER_PASSWORD",
      "value": "$FILEBROWSER_PASSWORD",
      "description": "Password for file browser access"
    },
    {
      "key": "ENABLE_SAGEATTN",
      "value": "true",
      "description": "Enable SageAttention2++ for faster attention on RTX 5090 (Blackwell). Use KJNodes patch node in workflow."
    }
  ],
  "startScript": "bash /workspace/scripts/startup.sh"
}
EOF
}

# Friendly human-readable storage note
make_storage_note() {
  if [[ "$VOLUME_GB" =~ ^[0-9]+$ ]] && (( VOLUME_GB > 0 )); then
    echo "Persistent volume ${VOLUME_GB}GB (models survive restarts)"
  else
    echo "Ephemeral volume (0GB; models redownload each start)"
  fi
}

# Print template summary
print_summary() {
    echo -e "${GREEN}📋 Template Configuration Summary:${NC}"
    echo ""
    echo -e "${BLUE}Template Details:${NC}"
    echo "  Name: $TEMPLATE_NAME"
    echo "  Docker Image: $DOCKER_IMAGE"
    echo "  Storage: $(make_storage_note)"
    echo ""
    echo -e "${BLUE}Model Configuration:${NC}"
    echo "  WAN Model Preset: ${HUGGINGFACE_MODELS:-'None specified'}"
    echo "  CivitAI Models: ${CIVITAI_MODELS:-'None'}"
    echo "  CivitAI LoRAs: ${CIVITAI_LORAS:-'None'}"
    echo "  CivitAI VAEs: ${CIVITAI_VAES:-'None'}"
    echo ""
    echo -e "${BLUE}Access:${NC}"
    echo "  ComfyUI: http://[pod-id]-8188.proxy.runpod.net"
    echo "  File Browser: http://[pod-id]-8080.proxy.runpod.net"
    echo "  File Browser Login: admin / $FILEBROWSER_PASSWORD"
    echo ""
}

# Generate usage instructions
generate_instructions() {
    cat > RUNPOD_USAGE.md << EOF
# 🎬 Ignition WAN RunPod Deployment Guide

## Quick Start

1. **Import Template** (or use \`./template.sh --deploy\` for direct API deployment):
   - Go to RunPod Templates
   - Click "New Template"
   - Upload the \`ignition_template.json\` file

2. **Deploy Pod**:
   - Select Ignition WAN template
   - Choose GPU (RTX 5090 or A100 40GB recommended for 14B FP8 models)
   - Add network volume for persistent model storage
   - Deploy!

## Access URLs

Once your pod is running:

- **ComfyUI**: \`http://[your-pod-id]-8188.proxy.runpod.net\`
- **File Browser**: \`http://[your-pod-id]-8080.proxy.runpod.net\`
  - Username: \`admin\`
  - Password: \`$FILEBROWSER_PASSWORD\`

## WAN 2.2 Model Presets

Set \`HUGGINGFACE_MODELS\` to one of these bundle keys:

| Key | Models Downloaded | VRAM | Use Case |
|-----|------------------|------|----------|
| \`wan2.2_t2v_bundle\` | T2V FP8 + text encoder + VAE | ~22GB | Text-to-video (standard) |
| \`wan2.2_t2v_lightx2v_bundle\` | Above + LightX2V LoRAs | ~22GB | T2V 4-step (5x faster) |
| \`wan2.2_i2v_bundle\` | I2V FP8 + text encoder + VAE + CLIP | ~22GB | Image-to-video (standard) |
| \`wan2.2_i2v_lightx2v_bundle\` | I2V FP8 (both variants) + LightX2V LoRAs | ~22GB | I2V 4-step (5x faster) |
| \`wan2.2_full_bundle\` | Both T2V + I2V + shared encoders | ~30GB | Both modes |

Individual keys also work: \`wan2.2_t2v_fp8\`, \`wan2.2_i2v_fp8\`, \`umt5_xxl_fp8\`, \`wan_vae\`, \`clip_vision_h\`, \`lightx2v_t2v_low_noise\`, \`lightx2v_i2v_low_noise\`

## Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| \`HUGGINGFACE_MODELS\` | WAN model bundle or comma-separated keys | \`wan2.2_t2v_bundle\` |
| \`HF_TOKEN\` | HuggingFace API token (optional) | \`hf_xxx\` |
| \`CIVITAI_MODELS\` | CivitAI checkpoint IDs (optional) | \`138977\` |
| \`CIVITAI_LORAS\` | CivitAI LoRA IDs (optional) | \`182404\` |
| \`CIVITAI_TOKEN\` | CivitAI API token (optional) | \`abc123\` |
| \`FORCE_MODEL_SYNC\` | Re-download all models on start | \`true\` |

### Storage Configuration
Storage: $(make_storage_note) (Container: ${CONTAINER_DISK_GB}GB disk, ${VOLUME_GB}GB volume)

## Startup Process

1. 🔍 System check + GPU detection
2. 💾 Storage setup (creates model dirs incl. clip_vision)
3. 📥 WAN model downloads via HuggingFace (parallel with CivitAI if set)
4. 📁 File browser start (port 8080)
5. 🎬 ComfyUI start with WanVideoWrapper (port 8188)

## 🔄 Restarting ComfyUI

### Soft Restart (Models Preserved)
\`\`\`bash
/workspace/scripts/restart-comfyui.sh
\`\`\`
- Restarts ComfyUI in 2 seconds
- All models and data preserved
- Container keeps running

### Hard Stop (Triggers Nuke)
\`\`\`bash
/workspace/scripts/stop-pod.sh
\`\`\`
- Exits container completely
- Nuclear cleanup deletes all data

| Action | Models | Container | Nuke |
|--------|--------|-----------|------|
| Soft Restart | ✅ Preserved | Running | ❌ No |
| Hard Stop | ❌ Deleted | Exits | ✅ Yes |
| Crash | ✅ Preserved | Running | ❌ No |

## Troubleshooting

### Logs
\`\`\`bash
tail -f /tmp/ignition_startup.log
\`\`\`

### Common Issues
- **Models not downloading**: Verify \`HUGGINGFACE_MODELS\` key spelling
- **Out of VRAM**: Use FP8 bundles instead of FP16; ensure 20GB+ VRAM
- **ComfyUI not responding**: Run \`/workspace/scripts/restart-comfyui.sh\`
- **Want to re-download models**: Set \`FORCE_MODEL_SYNC=true\` and restart pod

---
**🎬 Ready to generate video with Ignition WAN!**
EOF
}

# Deploy template via RunPod API
deploy_template() {
    echo -e "${YELLOW}🚀 Deploying template to RunPod...${NC}"

    # jq optional detection
    HAS_JQ=true
    if ! command -v jq &>/dev/null; then
        HAS_JQ=false
        echo -e "${YELLOW}⚠️ jq not found — responses will be raw JSON with basic parsing${NC}"
        echo ""
    fi
    
    # Build a dynamic storage note for README
    local STORAGE_NOTE
    STORAGE_NOTE="$(make_storage_note)"

    # Create API payload (GraphQL expects string with escaped newlines)
    local api_payload=$(cat << EOF
{
  "name": "$TEMPLATE_NAME",
  "imageName": "$DOCKER_IMAGE",
  "containerDiskInGb": $CONTAINER_DISK_GB,
  "volumeInGb": $VOLUME_GB,
  "volumeMountPath": "/workspace",
  "dockerArgs": "",
  "ports": "8188/http,8080/http",
  "readme": "# $TEMPLATE_NAME\\n\\n$TEMPLATE_DESCRIPTION\\n\\n## Configuration\\n- WAN Model Preset: $HUGGINGFACE_MODELS\\n- CivitAI Models: ${CIVITAI_MODELS:-none}\\n- CivitAI LoRAs: ${CIVITAI_LORAS:-none}\\n- Storage: ${STORAGE_NOTE} (${CONTAINER_DISK_GB}GB container disk, ${VOLUME_GB}GB volume)",
  "env": [
    {"key": "HUGGINGFACE_MODELS", "value": "$HUGGINGFACE_MODELS"},
    {"key": "CIVITAI_MODELS", "value": "$CIVITAI_MODELS"},
    {"key": "CIVITAI_LORAS", "value": "$CIVITAI_LORAS"},
    {"key": "CIVITAI_VAES", "value": "$CIVITAI_VAES"},
    {"key": "CIVITAI_TOKEN", "value": "{{ RUNPOD_SECRET_civitai.com }}"},
    {"key": "HF_TOKEN", "value": "{{ RUNPOD_SECRET_huggingface.co }}"},
    {"key": "FILEBROWSER_PASSWORD", "value": "$FILEBROWSER_PASSWORD"},
    {"key": "ENABLE_SAGEATTN", "value": "true"}
  ]
}
EOF
)
    
    echo -e "${BLUE}Sending request to RunPod API...${NC}"
    
    # Make API call
    local response=$(curl -s -X POST \
        "https://api.runpod.io/graphql" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer $RUNPOD_API_KEY" \
        -d "$(cat << EOF
{
  "query": "mutation saveTemplate(\$input: SaveTemplateInput!) { saveTemplate(input: \$input) { id name imageName } }",
  "variables": {
    "input": $api_payload
  }
}
EOF
)")

    # Error detection
    if echo "$response" | grep -q '"errors"'; then
        echo -e "${RED}❌ API Error:${NC}"
        if $HAS_JQ; then
            echo "$response" | jq -r '.errors[0].message'
        else
            echo "$response"
        fi
        return 1
    fi
    
    # Extract template info
    local template_id
    local template_name
    if $HAS_JQ; then
        template_id=$(echo "$response" | jq -r '.data.saveTemplate.id')
        template_name=$(echo "$response" | jq -r '.data.saveTemplate.name')
    else
        # Fallback parsing (best-effort)
        template_id=$(echo "$response" | grep -o '"id":"[^"]*' | head -n1 | cut -d'"' -f4)
        template_name=$(echo "$response" | grep -o '"name":"[^"]*' | head -n1 | cut -d'"' -f4)
    fi
    
    if [[ -n "$template_id" && "$template_id" != "null" ]]; then
        echo -e "${GREEN}✅ Template deployed successfully!${NC}"
        echo -e "${BLUE}Template ID:${NC} $template_id"
        echo -e "${BLUE}Template Name:${NC} $template_name"
        echo -e "${BLUE}RunPod Console:${NC} https://runpod.io/console/user/templates"
        return 0
    else
        echo -e "${RED}❌ Failed to deploy template${NC}"
        echo -e "${YELLOW}Response:${NC} $response"
        return 1
    fi
}

# Main execution
main() {
    print_banner
    print_usage
    
    # Check API requirements if in deploy mode
    check_api_requirements
    
    echo -e "${YELLOW}Press Enter to continue with template creation...${NC}"
    read
    
    get_configuration
    
    echo -e "${YELLOW}🔨 Generating template files...${NC}"
    generate_template
    generate_instructions
    print_summary
    
    if [[ "$DEPLOY_MODE" == "api" ]]; then
        echo -e "${YELLOW}🚀 Deploying to RunPod...${NC}"
        if deploy_template; then
            echo ""
            echo -e "${GREEN}✅ Template deployed successfully!${NC}"
            echo ""
            echo -e "${YELLOW}Next Steps:${NC}"
            echo "  1. Go to RunPod Console → Templates"
            echo "  2. Find your '$TEMPLATE_NAME' template"
            echo "  3. Deploy a pod using your new template"
            echo "  4. Access ComfyUI at http://[pod-id]-8188.proxy.runpod.net"
            echo "  5. Manage files at http://[pod-id]-8080.proxy.runpod.net"
        else
            echo ""
            echo -e "${YELLOW}⚠️  API deployment failed, but local files were created${NC}"
            echo -e "${BLUE}You can still upload ignition_template.json manually${NC}"
        fi
    else
        echo -e "${GREEN}✅ Template files created successfully!${NC}"
        echo ""
        echo -e "${BLUE}Generated Files:${NC}"
        echo "  📄 ignition_template.json - RunPod template definition"
        echo "  📖 RUNPOD_USAGE.md - Deployment and usage guide"
        echo ""
        echo -e "${YELLOW}Next Steps:${NC}"
        echo "  1. Upload ignition_template.json to RunPod Templates"
        echo "  2. Deploy a pod using your new template"
        echo "  3. Access ComfyUI at http://[pod-id]-8188.proxy.runpod.net"
        echo "  4. Manage files at http://[pod-id]-8080.proxy.runpod.net"
        echo ""
        echo -e "${BLUE}💡 Tip: Use './template.sh --deploy' for automatic deployment${NC}"
    fi
    
    echo ""
    echo -e "${GREEN}🎬 Happy generating with Ignition WAN!${NC}"
}

# Run main function
main "$@"
