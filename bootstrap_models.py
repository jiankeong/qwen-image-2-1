"""Cache Qwen-Image-2.1 GGUF assets at worker startup, not during Hub build."""

import os
from pathlib import Path

REPO = "abenzerps/Qwen-Image-2.1-GGUF"
MODELS = (
    ("qwen-image-2.1-Q4_K_M.gguf", "diffusion_models/qwen-image-2.1-Q4_K_M.gguf"),
    ("text_encoders/qwen3vl_8b_int8_convrot.safetensors", "text_encoders/qwen3vl_8b_int8_convrot.safetensors"),
    ("vae/qwen_image_2.1_vae_bf16.safetensors", "vae/qwen_image_2.1_vae_bf16.safetensors"),
)


def install_models(cache=None, model_root=Path("/comfyui/models"), downloader=None):
    if downloader is None:
        from huggingface_hub import hf_hub_download
        downloader = hf_hub_download
    cache = Path(cache or os.getenv("HF_HUB_CACHE", "/runpod-volume/hf-cache"))
    cache.mkdir(parents=True, exist_ok=True)
    for remote, relative_target in MODELS:
        source = Path(downloader(repo_id=REPO, filename=remote, cache_dir=str(cache), token=os.getenv("HF_TOKEN") or None))
        if not source.is_file() or source.stat().st_size == 0:
            raise RuntimeError(f"Model download is missing or empty: {remote}")
        target = Path(model_root) / relative_target
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.is_symlink() and target.resolve() == source.resolve():
            continue
        if target.exists() or target.is_symlink():
            raise RuntimeError(f"Refusing to replace existing model: {target}")
        target.symlink_to(source)
        print(f"[qwen-bootstrap] {remote} -> {target}", flush=True)


if __name__ == "__main__":
    install_models()
