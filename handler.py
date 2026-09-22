"""RunPod entrypoint delegating jobs to the official ComfyUI worker handler."""

import runpod
from worker_comfyui_handler import handler


if __name__ == "__main__":
    runpod.serverless.start({"handler": handler})
