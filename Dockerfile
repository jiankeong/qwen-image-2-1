FROM runpod/worker-comfyui:5.1.0-base

# Qwen-Image-2.1 needs current ComfyUI model definitions and the maintained GGUF fork.
RUN git -C /comfyui pull --ff-only && \
    python -m pip install --no-cache-dir -r /comfyui/requirements.txt && \
    git clone https://github.com/leejet/ComfyUI-GGUF.git /comfyui/custom_nodes/ComfyUI-GGUF && \
    python -m pip install --no-cache-dir -r /comfyui/custom_nodes/ComfyUI-GGUF/requirements.txt

# Preserve the official worker's complete image-handling implementation, then
# expose its RunPod startup explicitly in this repository for GitHub validation.
RUN mv /handler.py /worker_comfyui_handler.py
COPY handler.py /handler.py

# The official worker discovers models on an attached volume at /runpod-volume/models.
# Its inherited /start.sh starts ComfyUI before invoking our handler wrapper.
