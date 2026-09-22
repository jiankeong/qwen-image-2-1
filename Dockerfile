FROM runpod/worker-comfyui:5.10.0-base

# Qwen-Image-2.1 needs current ComfyUI model definitions and the maintained GGUF fork.
RUN git -C /comfyui pull --ff-only && \
    python -m pip install --no-cache-dir -r /comfyui/requirements.txt && \
    git clone https://github.com/leejet/ComfyUI-GGUF.git /comfyui/custom_nodes/ComfyUI-GGUF && \
    python -m pip install --no-cache-dir -r /comfyui/custom_nodes/ComfyUI-GGUF/requirements.txt

# Hub build/test workers have no attached network volume. Bake the model so
# the published image can generate Qwen images without separate storage setup.
RUN comfy model download \
    --url https://huggingface.co/abenzerps/Qwen-Image-2.1-GGUF/resolve/main/qwen-image-2.1-Q4_K_M.gguf \
    --relative-path models/diffusion_models --filename qwen-image-2.1-Q4_K_M.gguf && \
    comfy model download \
    --url https://huggingface.co/abenzerps/Qwen-Image-2.1-GGUF/resolve/main/text_encoders/qwen3vl_8b_int8_convrot.safetensors \
    --relative-path models/text_encoders --filename qwen3vl_8b_int8_convrot.safetensors && \
    comfy model download \
    --url https://huggingface.co/abenzerps/Qwen-Image-2.1-GGUF/resolve/main/vae/qwen_image_2.1_vae_bf16.safetensors \
    --relative-path models/vae --filename qwen_image_2.1_vae_bf16.safetensors

# Preserve the official worker's complete image-handling implementation, then
# expose its RunPod startup explicitly in this repository for GitHub validation.
RUN mv /handler.py /worker_comfyui_handler.py
COPY handler.py /handler.py

# The inherited /start.sh starts ComfyUI before invoking our handler wrapper.
