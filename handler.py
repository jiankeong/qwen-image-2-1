"""RunPod entrypoint delegating jobs to the official ComfyUI worker handler."""

import runpod
from worker_comfyui_handler import handler as comfyui_handler


def handler(event):
    """Handle one job using the upstream ComfyUI worker implementation."""
    return comfyui_handler(event)


if __name__ == "__main__":
    runpod.serverless.start({"handler": handler})
