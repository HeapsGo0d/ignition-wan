#!/usr/bin/env python3
"""
HuggingFace downloader for Ignition H3.

All MiniMax H3 weights come from Comfy-Org/MiniMax-H3, repackaged for ComfyUI's
native nodes. Nothing here is gated, so HF_TOKEN is optional.

Downloads use aria2c (see download_utils.download_with_aria2).
"""

import os
import sys
import argparse
from pathlib import Path
from typing import Dict, List, Optional

# Import shared utilities
from download_utils import log, download_with_aria2, validate_huggingface_repo, validate_models_list

H3_REPO = "Comfy-Org/MiniMax-H3"
TURBO_LORA_REPO = "larryvrh/MiniMax-H3-Turbo-Lora"


def _h3(path: str, subdir: str) -> Dict[str, str]:
    """Registry entry for a file in Comfy-Org/MiniMax-H3."""
    return {
        'url': f'https://huggingface.co/{H3_REPO}/resolve/main/{path}',
        'filename': path.rsplit('/', 1)[-1],
        'subdir': subdir,
    }


# Single-file model downloads.
#
# The `subdir` values are what ComfyUI's loader dropdowns list, so they must
# match the workflow widget values exactly. Note in particular that the LoRA
# goes in loras/ ROOT, not a nested folder: on the parked feature/10eros branch
# a nested loras/ltx23/ subdir silently broke every generation, because the node
# that emitted the filename used the bare name. Don't nest without a reason.
H3_MODELS = {
    # --- Diffusion models (fl2va = text/first/last-frame to video+audio) ---
    # "pruned" = precomputed adaLN curve tables, ~40% smaller than plain int8.
    # int8_convrot runs on any GPU; fp8_scaled has native kernels on Ada/Hopper/
    # Blackwell and is emulated (slower) on older cards. Same download size.
    'h3_fl2va_int8': _h3('diffusion_models/minimax_h3_fl2va_pruned_int8_convrot.safetensors',
                         'diffusion_models'),          # 20.97 GB
    'h3_fl2va_fp8': _h3('diffusion_models/minimax_h3_fl2va_pruned_fp8_scaled.safetensors',
                        'diffusion_models'),           # 20.96 GB

    # ref2va = reference-driven (up to 9 images or 3 video/audio clips).
    # Not in any default bundle — the R2V workflow is not shipped yet.
    'h3_ref2va_int8': _h3('diffusion_models/minimax_h3_ref2va_pruned_int8_convrot.safetensors',
                          'diffusion_models'),         # 20.97 GB
    'h3_ref2va_fp8': _h3('diffusion_models/minimax_h3_ref2va_pruned_fp8_scaled.safetensors',
                         'diffusion_models'),          # 20.96 GB

    # --- Text encoder (Qwen3-VL-32B) ---
    # nvfp4_awq is the default: smallest by far and runs on any GPU.
    'h3_text_encoder_nvfp4': _h3('text_encoders/qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors',
                                 'text_encoders'),     # 15.69 GB
    'h3_text_encoder_int8': _h3('text_encoders/qwen3vl_32b_minimax_h3_int8_convrot.safetensors',
                                'text_encoders'),      # 27.14 GB

    # --- VAEs — one quant each, always needed, regardless of GPU ---
    'h3_video_vae': _h3('vae/minimax_h3_video_vae_fp16.safetensors', 'vae'),   # 5.21 GB
    'h3_audio_vae': _h3('vae/minimax_h3_audio_vae_fp32.safetensors', 'vae'),   # 0.61 GB

    # --- Community 4-step Turbo LoRA (~744 MB) ---
    # Cuts ~20 sampling steps to 4-8. Strength 1.0, simple scheduler.
    # Autodetects the base variant at runtime, so it works with int8 and fp8 alike.
    'h3_turbo_lora': {
        'url': f'https://huggingface.co/{TURBO_LORA_REPO}/resolve/main/minimax_h3_turbo_v4_step600_ema.safetensors',
        'filename': 'minimax_h3_turbo_v4_step600_ema.safetensors',
        'subdir': 'loras',
    },
}

# Convenience bundle keys that expand to multiple model keys.
#
# Both bundles are ~43.2 GB and differ only in the diffusion model quant, so
# switching is a bundle-key change with no rebuild. scripts/retarget_workflows.py
# repoints the workflow loaders at whichever one actually landed on disk.
H3_BUNDLES = {
    # Default. ~21 GB VRAM in use — runs on any 24 GB+ card.
    'h3_int8_bundle': ['h3_fl2va_int8', 'h3_text_encoder_nvfp4',
                       'h3_video_vae', 'h3_audio_vae', 'h3_turbo_lora'],
    # Native fp8 kernels on Ada/Hopper/Blackwell (4090/5090/H100).
    'h3_fp8_bundle': ['h3_fl2va_fp8', 'h3_text_encoder_nvfp4',
                      'h3_video_vae', 'h3_audio_vae', 'h3_turbo_lora'],
}


def normalize_h3_key(model_input: str) -> str:
    """Expand bundle keys to comma-separated model key lists."""
    if model_input in H3_BUNDLES:
        return ','.join(H3_BUNDLES[model_input])
    if model_input in H3_MODELS:
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


def download_h3_model(model_key: str, base_output_dir: Path, token: str = "", force: bool = False) -> bool:
    """Download a model — supports predefined keys and generic HF repo format."""

    model_info: Optional[Dict[str, str]] = None

    if model_key in H3_MODELS:
        model_info = H3_MODELS[model_key]
        log('info', f'Downloading predefined H3 model: {model_key}')

    elif ':' in model_key:
        model_info = parse_generic_repo(model_key)
        if model_info:
            log('info', f'Downloading generic HuggingFace model: {model_key}')
        else:
            log('error', f'Invalid generic repo format: {model_key}. Use: repo:filename:subdir[:branch]')
            return False

    else:
        available = list(H3_MODELS.keys()) + list(H3_BUNDLES.keys())
        log('error', f'Unknown H3 model: {model_key}. Available: {", ".join(available)}')
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
    available_keys = list(H3_MODELS.keys()) + list(H3_BUNDLES.keys())
    parser = argparse.ArgumentParser(description='HuggingFace downloader for Ignition H3')
    parser.add_argument('--repos', required=True,
                        help=('Comma-separated list of H3 model keys. '
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
        log('info', 'No HuggingFace token — Comfy-Org/MiniMax-H3 is not gated, none needed')

    force_sync = os.getenv('FORCE_MODEL_SYNC', 'false').lower() == 'true'
    if force_sync:
        log('info', 'FORCE_MODEL_SYNC=true - will re-download existing files')

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    valid_model_inputs = validate_models_list(args.repos, validate_huggingface_repo, 'HuggingFace')

    if not valid_model_inputs:
        log('error', 'No valid HuggingFace models provided after validation')
        log('info', 'Use a bundle key like h3_int8_bundle, or individual model keys')
        return 1

    # Expand bundles and deduplicate
    all_model_keys: List[str] = []
    for model_input in valid_model_inputs:
        normalized = normalize_h3_key(model_input)
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

    log('info', f'Starting download of {len(all_model_keys)} models to {output_dir}')
    log('info', f'Model keys: {", ".join(all_model_keys)}')

    success_count = 0
    for model_key in all_model_keys:
        if download_h3_model(model_key, output_dir, token, force=force_sync):
            success_count += 1
        else:
            log('warning', f'Failed to download model {model_key}')

    log('info', f'Downloaded {success_count}/{len(all_model_keys)} models successfully')
    return 0 if success_count > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
