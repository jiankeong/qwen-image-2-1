FROM runpod/worker-comfyui:5.10.0-base

# Install code at build time; cache model weights at runtime on the RunPod volume
# (or the configured container disk), following the reference worker pattern.
RUN git -C /comfyui pull --ff-only && \
    python -m pip install --no-cache-dir -r /comfyui/requirements.txt && \
    git clone --depth 1 https://github.com/leejet/ComfyUI-GGUF.git /comfyui/custom_nodes/ComfyUI-GGUF && \
    python -m pip install --no-cache-dir -r /comfyui/custom_nodes/ComfyUI-GGUF/requirements.txt && \
    python -m pip install --no-cache-dir 'huggingface-hub>=0.34,<1'

RUN mv /handler.py /worker_comfyui_handler.py
COPY handler.py /handler.py
COPY bootstrap_models.py /bootstrap_models.py
COPY startup.sh /startup.sh
CMD ["sh", "/startup.sh"]
