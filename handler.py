"""RunPod entrypoint for Hub smoke checks and the official ComfyUI worker."""

import base64
import os
import struct
import zlib

import runpod


def _smoke_png():
    """Return a valid one-pixel RGB PNG without loading ComfyUI or CUDA."""
    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))

    png = (b"\x89PNG\r\n\x1a\n"
           + chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0))
           + chunk(b"IDAT", zlib.compress(b"\x00\x20\x40\x60"))
           + chunk(b"IEND", b""))
    return base64.b64encode(png).decode("ascii")


def handler(event):
    """Handle a Hub health check or delegate inference to the upstream worker."""
    if os.environ.get("USE_MOCK_PIPELINE") == "1":
        if event.get("input") != {"healthcheck": True}:
            raise ValueError("Smoke-test worker accepts only input.healthcheck=true")
        return {"images": [{"filename": "hub_smoke.png", "type": "base64", "data": _smoke_png()}]}

    from worker_comfyui_handler import handler as comfyui_handler
    from workflow_request import expand_input

    return comfyui_handler({**event, "input": expand_input(event.get("input"))})


if __name__ == "__main__":
    runpod.serverless.start({"handler": handler})
