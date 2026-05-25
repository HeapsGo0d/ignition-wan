#!/usr/bin/env python3
"""
Simple HuggingFace downloader for Ignition LTX.
Uses aria2c for all downloads. LTX models from Lightricks/LTX-2.3.
10Eros model from TenStrip/LTX2.3-10Eros (self-contained, no HF_TOKEN required).
Gemma text encoder from Comfy-Org/ltx-2 (single-file, spiece_model embedded, no token needed).
"""

import os
import sys
import argparse
from pathlib import Path
from typing import Dict, List, Optional

# Import shared utilities
from download_utils import log, download_with_aria2, validate_huggingface_repo, validate_models_list

LTX_MAIN_REPO = "Lightricks/LTX-2.3"
LTX_FP8_REPO = "Lightricks/LTX-2.3-fp8"
LTX_NVFP4_REPO = "Lightricks/LTX-2.3-nvfp4"

# Single-file model downloads (aria2c)
# All main LTX-2.3 model files go into models/checkpoints/ (ComfyUI-LTXVideo convention)
# Upscalers go into models/latent_upscale_models/
# VAE is bundled inside the main model — no separate VAE download needed
LTX_MODELS = {
    # --- Main models (BF16, ~46 GB each) ---
    'ltx2.3_dev': {
        'url': f'https://huggingface.co/{LTX_MAIN_REPO}/resolve/main/ltx-2.3-22b-dev.safetensors',
        'filename': 'ltx-2.3-22b-dev.safetensors',
        'subdir': 'checkpoints'
    },
    'ltx2.3_distilled': {
        'url': f'https://huggingface.co/{LTX_MAIN_REPO}/resolve/main/ltx-2.3-22b-distilled-1.1.safetensors',
        'filename': 'ltx-2.3-22b-distilled-1.1.safetensors',
        'subdir': 'checkpoints'
    },
    # --- FP8 models (~29 GB each) ---
    'ltx2.3_dev_fp8': {
        'url': f'https://huggingface.co/{LTX_FP8_REPO}/resolve/main/ltx-2.3-22b-dev-fp8.safetensors',
        'filename': 'ltx-2.3-22b-dev-fp8.safetensors',
        'subdir': 'checkpoints'
    },
    'ltx2.3_distilled_fp8': {
        'url': f'https://huggingface.co/{LTX_FP8_REPO}/resolve/main/ltx-2.3-22b-distilled-fp8.safetensors',
        'filename': 'ltx-2.3-22b-distilled-fp8.safetensors',
        'subdir': 'checkpoints'
    },
    # --- NVFP4 model (~21.7 GB, RTX 5090 / Blackwell only) ---
    'ltx2.3_dev_nvfp4': {
        'url': f'https://huggingface.co/{LTX_NVFP4_REPO}/resolve/main/ltx-2.3-22b-dev-nvfp4.safetensors',
        'filename': 'ltx-2.3-22b-dev-nvfp4.safetensors',
        'subdir': 'checkpoints'
    },
    # --- Distilled LoRA (7.61 GB, required for two-stage upscale pipelines) ---
    'ltx2.3_distilled_lora': {
        'url': f'https://huggingface.co/{LTX_MAIN_REPO}/resolve/main/ltx-2.3-22b-distilled-lora-384-1.1.safetensors',
        'filename': 'ltx-2.3-22b-distilled-lora-384-1.1.safetensors',
        'subdir': 'loras'
    },
    # --- Spatial upscalers (~1 GB each, latent_upscale_models/) ---
    'ltx2.3_spatial_x2': {
        'url': f'https://huggingface.co/{LTX_MAIN_REPO}/resolve/main/ltx-2.3-spatial-upscaler-x2-1.1.safetensors',
        'filename': 'ltx-2.3-spatial-upscaler-x2-1.1.safetensors',
        'subdir': 'latent_upscale_models'
    },
    'ltx2.3_spatial_x1_5': {
        'url': f'https://huggingface.co/{LTX_MAIN_REPO}/resolve/main/ltx-2.3-spatial-upscaler-x1.5-1.0.safetensors',
        'filename': 'ltx-2.3-spatial-upscaler-x1.5-1.0.safetensors',
        'subdir': 'latent_upscale_models'
    },
    # --- Temporal upscaler (262 MB) ---
    'ltx2.3_temporal_x2': {
        'url': f'https://huggingface.co/{LTX_MAIN_REPO}/resolve/main/ltx-2.3-temporal-upscaler-x2-1.0.safetensors',
        'filename': 'ltx-2.3-temporal-upscaler-x2-1.0.safetensors',
        'subdir': 'latent_upscale_models'
    },
    # --- Gemma 3 12B text encoder — ComfyUI-repackaged single file with spiece_model embedded ---
    # Comfy-Org/ltx-2 is not gated; no HF_TOKEN required.
    # FP8 (~12 GB): default, pairs well with FP8/NVFP4 LTX checkpoints
    'gemma3_text_encoder': {
        'url': 'https://huggingface.co/Comfy-Org/ltx-2/resolve/main/split_files/text_encoders/gemma_3_12B_it_fp8_scaled.safetensors',
        'filename': 'comfy_gemma_3_12B_it.safetensors',
        'subdir': 'text_encoders'
    },
    # BF16 (~24 GB): full precision, for A100/H100 or maximum quality
    'gemma3_text_encoder_bf16': {
        'url': 'https://huggingface.co/Comfy-Org/ltx-2/resolve/main/split_files/text_encoders/gemma_3_12B_it.safetensors',
        'filename': 'comfy_gemma_3_12B_it.safetensors',
        'subdir': 'text_encoders'
    },

    # --- Sulphur 2 safetensors (from SulphurAI/Sulphur-2-base) ---
    # Used by ComfyUI-LTXVideo nodes (same as standard LTX-2.3 safetensors path)
    # Pair with gemma3_text_encoder or gemma3_text_encoder_bf16
    'sulphur2_dev_fp8': {
        'url': 'https://huggingface.co/SulphurAI/Sulphur-2-base/resolve/main/sulphur_dev_fp8mixed.safetensors',
        'filename': 'sulphur_dev_fp8mixed.safetensors',
        'subdir': 'checkpoints'
    },
    'sulphur2_dev_bf16': {
        'url': 'https://huggingface.co/SulphurAI/Sulphur-2-base/resolve/main/sulphur_dev_bf16.safetensors',
        'filename': 'sulphur_dev_bf16.safetensors',
        'subdir': 'checkpoints'
    },
    'sulphur2_distil_bf16': {
        'url': 'https://huggingface.co/SulphurAI/Sulphur-2-base/resolve/main/sulphur_distil_bf16.safetensors',
        'filename': 'sulphur_distil_bf16.safetensors',
        'subdir': 'checkpoints'
    },

    # --- 10Eros (TenStrip/LTX2.3-10Eros) — transformer checkpoints (image VAE+CLIP bundled) ---
    # Fine-tune of Sulphur-2-base optimised for I2V; loads via ComfyUI-LTXVideo nodes
    # No HF_TOKEN required. Pair with gemma3_text_encoder_10eros + spatial upscaler + condsafe LoRA.
    '10eros_fp8': {
        'url': 'https://huggingface.co/TenStrip/LTX2.3-10Eros/resolve/main/10Eros_v1-fp8mixed_learned.safetensors',
        'filename': '10Eros_v1-fp8mixed_learned.safetensors',
        'subdir': 'checkpoints'
    },
    '10eros_bf16': {
        'url': 'https://huggingface.co/TenStrip/LTX2.3-10Eros/resolve/main/10Eros_v1_bf16.safetensors',
        'filename': '10Eros_v1_bf16.safetensors',
        'subdir': 'checkpoints'
    },

    # Gemma text encoder saved as the filename the 10Eros workflow hardcodes
    # (workflow was built against gemma_3_12B_it_fp8_e4m3fn.safetensors; closest public file is fp8_scaled)
    'gemma3_text_encoder_10eros': {
        'url': 'https://huggingface.co/Comfy-Org/ltx-2/resolve/main/split_files/text_encoders/gemma_3_12B_it_fp8_scaled.safetensors',
        'filename': 'gemma_3_12B_it_fp8_e4m3fn.safetensors',
        'subdir': 'text_encoders'
    },

    # Condition-safe distilled LoRA from TenStrip's experiments repo (~662 MB)
    # Stored in loras/ltx23/ to match the workflow's hardcoded path
    '10eros_condsafe_lora': {
        'url': 'https://huggingface.co/TenStrip/LTX2.3_Distilled_Lora_1.1_Experiments/resolve/main/ltx-2.3-22b-distilled-lora-1.1_fro90_ceil72_condsafe.safetensors',
        'filename': 'ltx-2.3-22b-distilled-lora-1.1_fro90_ceil72_condsafe.safetensors',
        'subdir': 'loras/ltx23'
    },

    # --- Standalone VAE files (optional — ERos checkpoints bundle VAEs, but available separately) ---
    'ltx23_video_vae': {
        'url': 'https://huggingface.co/Kijai/LTX2.3_comfy/resolve/main/vae/LTX23_video_vae_bf16.safetensors',
        'filename': 'LTX23_video_vae_bf16.safetensors',
        'subdir': 'vae'
    },
    'ltx23_audio_vae': {
        'url': 'https://huggingface.co/Kijai/LTX2.3_comfy/resolve/main/vae/LTX23_audio_vae_bf16.safetensors',
        'filename': 'LTX23_audio_vae_bf16.safetensors',
        'subdir': 'vae'
    },
}

# Convenience bundle keys that expand to multiple models
# _fp8 bundles use Gemma FP8 (~12 GB); _bf16 bundles use Gemma BF16 (~24 GB, full quality)
LTX_BUNDLES = {
    # --- 10Eros bundles ---
    # FP8: checkpoint (~29 GB) + Gemma FP8 (~13 GB) + spatial upscaler (~1 GB) + condsafe LoRA (~0.7 GB) ≈ 44 GB
    '10eros_fp8_bundle': ['10eros_fp8', 'gemma3_text_encoder_10eros', 'ltx2.3_spatial_x2', '10eros_condsafe_lora'],
    # BF16: checkpoint (~46 GB) + Gemma BF16 (~24 GB) + spatial upscaler (~1 GB) + condsafe LoRA (~0.7 GB) ≈ 72 GB
    '10eros_bf16_bundle': ['10eros_bf16', 'gemma3_text_encoder_bf16', 'ltx2.3_spatial_x2', '10eros_condsafe_lora'],

    # --- Standard LTX-2.3 bundles (_fp8 use Gemma FP8; _bf16 use Gemma BF16) ---
    # Quickstart: distilled fp8 + Gemma FP8 (~41 GB)
    'ltx2.3_distilled_fp8_bundle': ['ltx2.3_distilled_fp8', 'gemma3_text_encoder'],
    # Quickstart BF16 Gemma: distilled fp8 + Gemma BF16 (~53 GB, full text encoder quality)
    'ltx2.3_distilled_fp8_bundle_bf16': ['ltx2.3_distilled_fp8', 'gemma3_text_encoder_bf16'],
    # Dev fp8 + Gemma FP8 (~41 GB)
    'ltx2.3_dev_fp8_bundle': ['ltx2.3_dev_fp8', 'gemma3_text_encoder'],
    # Dev fp8 + Gemma BF16 (~53 GB)
    'ltx2.3_dev_fp8_bundle_bf16': ['ltx2.3_dev_fp8', 'gemma3_text_encoder_bf16'],
    # Blackwell: NVFP4 dev + Gemma FP8 (~34 GB, RTX 5090 only)
    'ltx2.3_nvfp4_bundle': ['ltx2.3_dev_nvfp4', 'gemma3_text_encoder'],
    # Blackwell BF16 Gemma: NVFP4 dev + Gemma BF16 (~46 GB, RTX 5090 only)
    'ltx2.3_nvfp4_bundle_bf16': ['ltx2.3_dev_nvfp4', 'gemma3_text_encoder_bf16'],
    # Full distilled: fp8 + distilled LoRA + Gemma FP8 + upscalers (~51 GB, two-stage pipeline)
    'ltx2.3_full_bundle': [
        'ltx2.3_distilled_fp8', 'ltx2.3_distilled_lora',
        'gemma3_text_encoder',
        'ltx2.3_spatial_x2', 'ltx2.3_temporal_x2'
    ],
    # Full BF16 Gemma: fp8 + distilled LoRA + Gemma BF16 + upscalers (~63 GB)
    'ltx2.3_full_bundle_bf16': [
        'ltx2.3_distilled_fp8', 'ltx2.3_distilled_lora',
        'gemma3_text_encoder_bf16',
        'ltx2.3_spatial_x2', 'ltx2.3_temporal_x2'
    ],
    # Upscalers only (if main model already downloaded)
    'ltx2.3_upscalers_bundle': ['ltx2.3_spatial_x2', 'ltx2.3_spatial_x1_5', 'ltx2.3_temporal_x2'],

    # --- Sulphur 2 safetensors — parked on spike/ltx-2.3; kept here for reference ---
    # Uses ComfyUI-LTXVideo nodes (same workflows as standard LTX-2.3); pair with Gemma text encoder
    'sulphur2_fp8_bundle': ['sulphur2_dev_fp8', 'gemma3_text_encoder'],
    'sulphur2_fp8_bundle_bf16': ['sulphur2_dev_fp8', 'gemma3_text_encoder_bf16'],
    'sulphur2_bf16_bundle': ['sulphur2_dev_bf16', 'gemma3_text_encoder_bf16'],
}


def normalize_ltx_key(model_input: str) -> str:
    """Expand bundle keys to comma-separated model key lists."""
    if model_input in LTX_BUNDLES:
        return ','.join(LTX_BUNDLES[model_input])
    if model_input in LTX_MODELS:
        return model_input
    return model_input


def parse_generic_repo(model_input: str) -> Optional[Dict[str, str]]:
    """Parse generic HuggingFace repo format: repo:filename:subdir[:branch]"""
    parts: List[str] = model_input.split(':')
    if len(parts) < 3:
        return None

    repo: str = parts[0]
    filename: str = parts[1]
    subdir: str = parts[2]
    branch: str = parts[3] if len(parts) > 3 else 'main'

    url: str = f"https://huggingface.co/{repo}/resolve/{branch}/{filename}"

    return {
        'url': url,
        'filename': filename,
        'subdir': subdir
    }


def download_ltx_model(model_key: str, base_output_dir: Path, token: str = "", force: bool = False) -> bool:
    """Download an LTX model — supports predefined and generic HF repo formats."""

    model_info: Optional[Dict[str, str]] = None

    if model_key in LTX_MODELS:
        model_info = LTX_MODELS[model_key]
        log('info', f'Downloading predefined LTX model: {model_key}')

    elif ':' in model_key:
        model_info = parse_generic_repo(model_key)
        if model_info:
            log('info', f'Downloading generic HuggingFace model: {model_key}')
        else:
            log('error', f'Invalid generic repo format: {model_key}. Use: repo:filename:subdir[:branch]')
            return False

    else:
        available = list(LTX_MODELS.keys()) + list(LTX_BUNDLES.keys())
        log('error', f'Unknown LTX model: {model_key}. Available: {", ".join(available)}')
        log('info', 'Or use generic format: repo:filename:subdir[:branch]')
        return False

    url = model_info['url']
    filename = model_info['filename']
    subdir = model_info['subdir']
    target_dir = base_output_dir / subdir

    log('info', f'Target directory: {subdir}/')
    return download_with_aria2(url, target_dir, filename, token, force=force)


def main() -> int:
    """Main entry point."""
    available_keys = list(LTX_MODELS.keys()) + list(LTX_BUNDLES.keys())
    parser = argparse.ArgumentParser(description='HuggingFace downloader for Ignition LTX')
    parser.add_argument('--repos', required=True,
                        help=('Comma-separated list of LTX model keys. '
                              f'Predefined: {", ".join(available_keys)}. '
                              'Generic format: repo:filename:subdir[:branch]'))
    parser.add_argument('--token', default='', help='HuggingFace API token')
    parser.add_argument('--output-dir', default='/workspace/ComfyUI/models',
                        help='Base ComfyUI models directory')

    args = parser.parse_args()

    token = args.token or os.getenv('HF_TOKEN', '')

    if token:
        log('info', 'HuggingFace token provided (used for private/gated repos)')
    else:
        log('info', 'No HuggingFace token — public models only (Comfy-Org Gemma is not gated)')

    force_sync = os.getenv('FORCE_MODEL_SYNC', 'false').lower() == 'true'
    if force_sync:
        log('info', 'FORCE_MODEL_SYNC=true - will re-download existing files')

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    valid_model_inputs = validate_models_list(args.repos, validate_huggingface_repo, 'HuggingFace')

    if not valid_model_inputs:
        log('error', 'No valid HuggingFace models provided after validation')
        log('info', 'Use predefined bundle keys like ltx2.3_distilled_fp8_bundle or individual keys')
        return 1

    # Expand bundles and deduplicate
    all_model_keys: List[str] = []
    for model_input in valid_model_inputs:
        normalized = normalize_ltx_key(model_input)
        if ',' in normalized:
            all_model_keys.extend([k.strip() for k in normalized.split(',')])
        else:
            all_model_keys.append(normalized)

    seen = set()
    unique_keys = []
    for k in all_model_keys:
        if k not in seen:
            seen.add(k)
            unique_keys.append(k)
    all_model_keys = unique_keys

    log('info', f'Starting download of {len(all_model_keys)} LTX models to {output_dir}')
    log('info', f'Model keys: {", ".join(all_model_keys)}')

    success_count = 0
    for model_key in all_model_keys:
        if download_ltx_model(model_key, output_dir, token, force=force_sync):
            success_count += 1
        else:
            log('warning', f'Failed to download model {model_key}')

    log('info', f'Downloaded {success_count}/{len(all_model_keys)} models successfully')
    return 0 if success_count > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
