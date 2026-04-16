#!/usr/bin/env python3
"""
Simple HuggingFace downloader for Ignition WAN.
Uses aria2c for reliable downloads with direct model URLs.
Models sourced from Comfy-Org/Wan_2.2_ComfyUI_Repackaged for optimized ComfyUI compatibility.
"""

import os
import sys
import argparse
from pathlib import Path
from typing import Dict, List, Optional, Union

# Import shared utilities
from download_utils import log, download_with_aria2, validate_huggingface_repo, validate_models_list

WAN_REPACKAGED_REPO = "Comfy-Org/Wan_2.2_ComfyUI_Repackaged"

WAN_MODELS = {
    # --- Text-to-Video (T2V) ---
    'wan2.2_t2v_fp8': {
        'url': f'https://huggingface.co/{WAN_REPACKAGED_REPO}/resolve/main/split_files/diffusion_models/wan2.2_t2v_low_noise_14B_fp8_scaled.safetensors',
        'filename': 'wan2.2_t2v_low_noise_14B_fp8_scaled.safetensors',
        'subdir': 'diffusion_models'
    },
    'wan2.2_t2v_high_noise_fp8': {
        'url': f'https://huggingface.co/{WAN_REPACKAGED_REPO}/resolve/main/split_files/diffusion_models/wan2.2_t2v_high_noise_14B_fp8_scaled.safetensors',
        'filename': 'wan2.2_t2v_high_noise_14B_fp8_scaled.safetensors',
        'subdir': 'diffusion_models'
    },
    'wan2.2_t2v_fp16': {
        'url': f'https://huggingface.co/{WAN_REPACKAGED_REPO}/resolve/main/split_files/diffusion_models/wan2.2_t2v_low_noise_14B_fp16.safetensors',
        'filename': 'wan2.2_t2v_low_noise_14B_fp16.safetensors',
        'subdir': 'diffusion_models'
    },
    # --- Image-to-Video (I2V) ---
    'wan2.2_i2v_fp8': {
        'url': f'https://huggingface.co/{WAN_REPACKAGED_REPO}/resolve/main/split_files/diffusion_models/wan2.2_i2v_low_noise_14B_fp8_scaled.safetensors',
        'filename': 'wan2.2_i2v_low_noise_14B_fp8_scaled.safetensors',
        'subdir': 'diffusion_models'
    },
    'wan2.2_i2v_high_noise_fp8': {
        'url': f'https://huggingface.co/{WAN_REPACKAGED_REPO}/resolve/main/split_files/diffusion_models/wan2.2_i2v_high_noise_14B_fp8_scaled.safetensors',
        'filename': 'wan2.2_i2v_high_noise_14B_fp8_scaled.safetensors',
        'subdir': 'diffusion_models'
    },
    'wan2.2_i2v_fp16': {
        'url': f'https://huggingface.co/{WAN_REPACKAGED_REPO}/resolve/main/split_files/diffusion_models/wan2.2_i2v_low_noise_14B_fp16.safetensors',
        'filename': 'wan2.2_i2v_low_noise_14B_fp16.safetensors',
        'subdir': 'diffusion_models'
    },
    # --- Text Encoder (shared by all WAN 2.2 models) ---
    'umt5_xxl_fp8': {
        'url': f'https://huggingface.co/{WAN_REPACKAGED_REPO}/resolve/main/split_files/text_encoders/umt5_xxl_fp8_e4m3fn_scaled.safetensors',
        'filename': 'umt5_xxl_fp8_e4m3fn_scaled.safetensors',
        'subdir': 'text_encoders'
    },
    # --- VAE ---
    'wan_vae': {
        'url': f'https://huggingface.co/{WAN_REPACKAGED_REPO}/resolve/main/split_files/vae/wan_2.1_vae.safetensors',
        'filename': 'wan_2.1_vae.safetensors',
        'subdir': 'vae'
    },
    # --- CLIP Vision (required for I2V image conditioning) ---
    # Note: clip_vision_h is in the WAN 2.1 repackaged repo, not 2.2
    'clip_vision_h': {
        'url': 'https://huggingface.co/Comfy-Org/Wan_2.1_ComfyUI_repackaged/resolve/main/split_files/clip_vision/clip_vision_h.safetensors',
        'filename': 'clip_vision_h.safetensors',
        'subdir': 'clip_vision'
    },
    # --- LightX2V LoRAs: T2V (4-step accelerated generation, v1.1) ---
    'lightx2v_t2v_low_noise': {
        'url': f'https://huggingface.co/{WAN_REPACKAGED_REPO}/resolve/main/split_files/loras/wan2.2_t2v_lightx2v_4steps_lora_v1.1_low_noise.safetensors',
        'filename': 'wan2.2_t2v_lightx2v_4steps_lora_v1.1_low_noise.safetensors',
        'subdir': 'loras'
    },
    'lightx2v_t2v_high_noise': {
        'url': f'https://huggingface.co/{WAN_REPACKAGED_REPO}/resolve/main/split_files/loras/wan2.2_t2v_lightx2v_4steps_lora_v1.1_high_noise.safetensors',
        'filename': 'wan2.2_t2v_lightx2v_4steps_lora_v1.1_high_noise.safetensors',
        'subdir': 'loras'
    },
    # --- NSFW/Uncensored Models ---
    # FX-FeiHou Remix NSFW v3.0 (age-gate repo - set HF_TOKEN if downloads fail)
    # fp8_e4m3fn native — improved anatomy, motion, scene consistency over v2.0
    'remix_nsfw_i2v_high': {
        'url': 'https://huggingface.co/FX-FeiHou/wan2.2-Remix/resolve/main/NSFW/Wan2.2_Remix_NSFW_i2v_14b_high_lighting_fp8_e4m3fn_v3.0.safetensors',
        'filename': 'Wan2.2_Remix_NSFW_i2v_14b_high_lighting_fp8_e4m3fn_v3.0.safetensors',
        'subdir': 'diffusion_models'
    },
    'remix_nsfw_i2v_low': {
        'url': 'https://huggingface.co/FX-FeiHou/wan2.2-Remix/resolve/main/NSFW/Wan2.2_Remix_NSFW_i2v_14b_low_lighting_fp8_e4m3fn_v3.0.safetensors',
        'filename': 'Wan2.2_Remix_NSFW_i2v_14b_low_lighting_fp8_e4m3fn_v3.0.safetensors',
        'subdir': 'diffusion_models'
    },
    # Phr00t MEGA v12.2 — single unified file (I2V+T2V), bf16 Fun/VACE base, rCM+LightX2V baked in
    # Load same file in both UNETLoader nodes. Best sampler: dpmpp_sde / beta.
    'phr00t_mega_nsfw': {
        'url': 'https://huggingface.co/Phr00t/WAN2.2-14B-Rapid-AllInOne/resolve/main/Mega-v12/wan2.2-rapid-mega-aio-nsfw-v12.2.safetensors',
        'filename': 'wan2.2-rapid-mega-aio-nsfw-v12.2.safetensors',
        'subdir': 'diffusion_models'
    },
    # General NSFW LoRA — single file works for both high and low noise stages
    'nsfw_lora_h': {
        'url': 'https://huggingface.co/rahul7star/wan2.2Lora/resolve/main/wan2.2/NSFW-22-H-e8.safetensors',
        'filename': 'NSFW-22-H-e8.safetensors',
        'subdir': 'loras'
    },
    # --- SUPIR: diffusion image super-resolution ---
    # Pruned Q variant — best quality/VRAM tradeoff (~5.3GB, .ckpt format)
    # Public mirror from camenduru/SUPIR (no HF_TOKEN required)
    # kijai/SUPIR has pruned safetensors but requires HF_TOKEN — use that repo if preferred
    'supir_v0q': {
        'url': 'https://huggingface.co/camenduru/SUPIR/resolve/main/SUPIR-v0Q.ckpt',
        'filename': 'SUPIR-v0Q.ckpt',
        'subdir': 'checkpoints'
    },
    # F variant — fidelity-preserving, less hallucination on lightly degraded images (~5.3GB)
    'supir_v0f': {
        'url': 'https://huggingface.co/camenduru/SUPIR/resolve/main/SUPIR-v0F.ckpt',
        'filename': 'SUPIR-v0F.ckpt',
        'subdir': 'checkpoints'
    },
    # SDXL base checkpoint required by SUPIR (~6.9GB) — CLIP is embedded, no separate CLIP files needed
    # Public from camenduru mirror; includes improved 0.9 VAE
    'sdxl_base': {
        'url': 'https://huggingface.co/camenduru/SUPIR/resolve/main/sd_xl_base_1.0_0.9vae.safetensors',
        'filename': 'sd_xl_base_1.0_0.9vae.safetensors',
        'subdir': 'checkpoints'
    },
    # --- LightX2V LoRAs: I2V (4-step accelerated generation, v1) ---
    'lightx2v_i2v_low_noise': {
        'url': f'https://huggingface.co/{WAN_REPACKAGED_REPO}/resolve/main/split_files/loras/wan2.2_i2v_lightx2v_4steps_lora_v1_low_noise.safetensors',
        'filename': 'wan2.2_i2v_lightx2v_4steps_lora_v1_low_noise.safetensors',
        'subdir': 'loras'
    },
    'lightx2v_i2v_high_noise': {
        'url': f'https://huggingface.co/{WAN_REPACKAGED_REPO}/resolve/main/split_files/loras/wan2.2_i2v_lightx2v_4steps_lora_v1_high_noise.safetensors',
        'filename': 'wan2.2_i2v_lightx2v_4steps_lora_v1_high_noise.safetensors',
        'subdir': 'loras'
    },
}

# Convenience bundle keys that expand to multiple models
WAN_BUNDLES = {
    # T2V: both noise variants + text encoder + VAE + LightX2V LoRAs (complete for all T2V templates)
    'wan2.2_t2v_bundle': ['wan2.2_t2v_fp8', 'wan2.2_t2v_high_noise_fp8', 'umt5_xxl_fp8', 'wan_vae', 'lightx2v_t2v_low_noise', 'lightx2v_t2v_high_noise'],
    # T2V alias kept for clarity
    'wan2.2_t2v_lightx2v_bundle': ['wan2.2_t2v_fp8', 'wan2.2_t2v_high_noise_fp8', 'umt5_xxl_fp8', 'wan_vae', 'lightx2v_t2v_low_noise', 'lightx2v_t2v_high_noise'],
    # I2V: both noise variants + text encoder + VAE + CLIP + LightX2V LoRAs (complete for all I2V templates)
    'wan2.2_i2v_bundle': ['wan2.2_i2v_fp8', 'wan2.2_i2v_high_noise_fp8', 'umt5_xxl_fp8', 'wan_vae', 'clip_vision_h', 'lightx2v_i2v_low_noise', 'lightx2v_i2v_high_noise'],
    # I2V alias kept for clarity
    'wan2.2_i2v_lightx2v_bundle': ['wan2.2_i2v_fp8', 'wan2.2_i2v_high_noise_fp8', 'umt5_xxl_fp8', 'wan_vae', 'clip_vision_h', 'lightx2v_i2v_low_noise', 'lightx2v_i2v_high_noise'],
    # Full: everything for T2V + I2V including all LightX2V LoRAs
    'wan2.2_full_bundle': ['wan2.2_t2v_fp8', 'wan2.2_t2v_high_noise_fp8', 'wan2.2_i2v_fp8', 'wan2.2_i2v_high_noise_fp8', 'umt5_xxl_fp8', 'wan_vae', 'clip_vision_h', 'lightx2v_t2v_low_noise', 'lightx2v_t2v_high_noise', 'lightx2v_i2v_low_noise', 'lightx2v_i2v_high_noise'],
    # LightX2V LoRAs only (if models already downloaded)
    'lightx2v_t2v_bundle': ['lightx2v_t2v_low_noise', 'lightx2v_t2v_high_noise'],
    'lightx2v_i2v_bundle': ['lightx2v_i2v_low_noise', 'lightx2v_i2v_high_noise'],
    # NSFW bundles
    'nsfw_lora_bundle': ['nsfw_lora_h'],
    'remix_nsfw_i2v_bundle': ['remix_nsfw_i2v_high', 'remix_nsfw_i2v_low', 'umt5_xxl_fp8', 'wan_vae', 'clip_vision_h'],
    'phr00t_mega_nsfw_bundle': ['phr00t_mega_nsfw', 'umt5_xxl_fp8', 'wan_vae', 'clip_vision_h'],
    # All 3 NSFW I2V workflows: Remix v3.0 + Phr00t MEGA + official SFW base + NSFW/LightX2V LoRAs (~70GB)
    'nsfw_i2v_full_bundle': ['remix_nsfw_i2v_high', 'remix_nsfw_i2v_low', 'phr00t_mega_nsfw', 'wan2.2_i2v_high_noise_fp8', 'wan2.2_i2v_fp8', 'lightx2v_i2v_high_noise', 'lightx2v_i2v_low_noise', 'nsfw_lora_h', 'umt5_xxl_fp8', 'wan_vae', 'clip_vision_h'],
    # SUPIR image upscaling: SUPIR-v0Q + SDXL base (~12GB total) — non-commercial license
    'supir_bundle': ['supir_v0q', 'sdxl_base'],
    # SUPIR model only — for instances that already have an SDXL checkpoint
    'supir_core_only': ['supir_v0q'],
}


def normalize_wan_key(model_input: str) -> str:
    """Expand bundle keys and normalize repo names to internal WAN keys."""
    # Expand bundles to comma-separated key lists
    if model_input in WAN_BUNDLES:
        return ','.join(WAN_BUNDLES[model_input])

    # If it's already a known key, return as-is
    if model_input in WAN_MODELS:
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


def download_wan_model(model_key: str, base_output_dir: Path, token: str = "", force: bool = False) -> bool:
    """Download a WAN model - supports both predefined models and generic HF repos."""

    model_info: Optional[Dict[str, str]] = None

    # Check if it's a predefined model
    if model_key in WAN_MODELS:
        model_info = WAN_MODELS[model_key]
        log('info', f'Downloading predefined WAN model: {model_key}')

    # Check if it's a generic repo format (contains colons)
    elif ':' in model_key:
        model_info = parse_generic_repo(model_key)
        if model_info:
            log('info', f'Downloading generic HuggingFace model: {model_key}')
        else:
            log('error', f'Invalid generic repo format: {model_key}. Use: repo:filename:subdir[:branch]')
            return False

    # Unknown model
    else:
        log('error', f'Unknown WAN model: {model_key}. Available predefined: {", ".join(WAN_MODELS.keys())}')
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
    parser = argparse.ArgumentParser(description='HuggingFace downloader for Ignition WAN')
    parser.add_argument('--repos', required=True,
                        help=('Comma-separated list of WAN model keys. '
                              f'Predefined: {", ".join(list(WAN_MODELS.keys()) + list(WAN_BUNDLES.keys()))}. '
                              'Generic format: repo:filename:subdir[:branch]'))
    parser.add_argument('--token', default='', help='HuggingFace API token')
    parser.add_argument('--output-dir', default='/workspace/ComfyUI/models',
                        help='Base ComfyUI models directory')

    args = parser.parse_args()

    # Get token from environment if not provided
    token = args.token or os.getenv('HF_TOKEN', '')

    if not token:
        log('warning', 'No HuggingFace token provided - downloads may fail for gated models')

    # Check for force sync flag
    force_sync = os.getenv('FORCE_MODEL_SYNC', 'false').lower() == 'true'
    if force_sync:
        log('info', 'FORCE_MODEL_SYNC=true - will re-download existing files')

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Validate HuggingFace repository inputs
    valid_model_inputs = validate_models_list(args.repos, validate_huggingface_repo, 'HuggingFace')

    if not valid_model_inputs:
        log('error', 'No valid HuggingFace models provided after validation')
        log('info', 'Use format: username/repository or predefined models like wan2.2_t2v_fp8')
        return 1

    # Normalize all inputs and expand bundles/multi-model keys
    all_model_keys: List[str] = []
    for model_input in valid_model_inputs:
        normalized = normalize_wan_key(model_input)
        if ',' in normalized:
            all_model_keys.extend([k.strip() for k in normalized.split(',')])
        else:
            all_model_keys.append(normalized)

    # Deduplicate while preserving order (e.g. shared text encoder from two bundles)
    seen = set()
    unique_keys = []
    for k in all_model_keys:
        if k not in seen:
            seen.add(k)
            unique_keys.append(k)
    all_model_keys = unique_keys

    log('info', f'Starting download of {len(all_model_keys)} WAN models to {output_dir}')
    log('info', f'Model keys: {", ".join(all_model_keys)}')

    success_count = 0
    for model_key in all_model_keys:
        if download_wan_model(model_key, output_dir, token, force=force_sync):
            success_count += 1
        else:
            log('warning', f'Failed to download model {model_key}')

    log('info', f'Downloaded {success_count}/{len(all_model_keys)} models successfully')
    return 0 if success_count > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
