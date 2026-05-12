#!/usr/bin/env python3
"""
Simple HuggingFace downloader for Ignition LTX.
Uses aria2c for single-file downloads, huggingface_hub snapshot_download for multi-file repos.
Models sourced from Lightricks/LTX-2.3 and google/gemma-3-12b-it-qat-q4_0-unquantized.
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
    # --- Gemma 3 text encoder (snapshot: 5 safetensors shards, ~24 GB, gated — HF_TOKEN required) ---
    # Downloads entire repo to models/text_encoders/gemma-3-12b-it-qat-q4_0-unquantized/
    'gemma3_text_encoder': {
        'type': 'snapshot',
        'repo_id': 'google/gemma-3-12b-it-qat-q4_0-unquantized',
        'local_subdir': 'text_encoders/gemma-3-12b-it-qat-q4_0-unquantized'
    },
}

# Convenience bundle keys that expand to multiple models
LTX_BUNDLES = {
    # Quickstart: distilled fp8 + Gemma (~53 GB, needs HF_TOKEN for Gemma)
    'ltx2.3_distilled_fp8_bundle': ['ltx2.3_distilled_fp8', 'gemma3_text_encoder'],
    # Dev fp8 + Gemma (~53 GB)
    'ltx2.3_dev_fp8_bundle': ['ltx2.3_dev_fp8', 'gemma3_text_encoder'],
    # Blackwell: NVFP4 dev + Gemma (~46 GB, RTX 5090 only)
    'ltx2.3_nvfp4_bundle': ['ltx2.3_dev_nvfp4', 'gemma3_text_encoder'],
    # Full distilled: fp8 + distilled LoRA + Gemma + upscalers (~63 GB, two-stage pipeline)
    'ltx2.3_full_bundle': [
        'ltx2.3_distilled_fp8', 'ltx2.3_distilled_lora',
        'gemma3_text_encoder',
        'ltx2.3_spatial_x2', 'ltx2.3_temporal_x2'
    ],
    # Upscalers only (if main model already downloaded)
    'ltx2.3_upscalers_bundle': ['ltx2.3_spatial_x2', 'ltx2.3_spatial_x1_5', 'ltx2.3_temporal_x2'],
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


def download_snapshot(repo_id: str, local_dir: Path, token: str = "", force: bool = False) -> bool:
    """Download entire HuggingFace repo via snapshot_download (for multi-file repos like Gemma)."""
    try:
        from huggingface_hub import snapshot_download
        log('info', f'Snapshot downloading {repo_id} → {local_dir}')
        tokenizer_present = (local_dir / "tokenizer.model").exists()
        if not force and local_dir.exists() and any(local_dir.iterdir()) and tokenizer_present:
            log('info', f'  Skipping {repo_id} (already present at {local_dir})')
            return True
        if force and local_dir.exists():
            import shutil
            shutil.rmtree(local_dir)
            log('info', f'  Force re-download: cleared {local_dir}')
        local_dir.mkdir(parents=True, exist_ok=True)
        snapshot_download(
            repo_id=repo_id,
            local_dir=str(local_dir),
            token=token or None,
            ignore_patterns=["*.gitattributes", "*.gitignore", "*.md", "added_tokens.json"],
        )
        log('info', f'  ✅ Snapshot complete: {repo_id}')
        return True
    except Exception as e:
        log('error', f'  Snapshot download failed for {repo_id}: {e}')
        return False


def download_ltx_model(model_key: str, base_output_dir: Path, token: str = "", force: bool = False) -> bool:
    """Download an LTX model — supports predefined, snapshot, and generic HF repo formats."""

    model_info: Optional[Dict[str, str]] = None

    if model_key in LTX_MODELS:
        model_info = LTX_MODELS[model_key]

        # Snapshot download (multi-file repos like Gemma)
        if model_info.get('type') == 'snapshot':
            local_dir = base_output_dir / model_info['local_subdir']
            return download_snapshot(model_info['repo_id'], local_dir, token, force=force)

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

    if not token:
        log('warning', 'No HuggingFace token provided — Gemma downloads will fail (gated model)')

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
