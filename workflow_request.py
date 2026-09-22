"""Expand small RunPod inputs into the two bundled ComfyUI API workflows."""

import base64
import binascii
import copy
import json
import re
from pathlib import Path

TEMPLATES = Path(__file__).resolve().parent / "examples"
_DATA_URI = re.compile(r"^data:image/(png|jpeg|webp);base64,", re.IGNORECASE)


def _template(name):
    return json.loads((TEMPLATES / name).read_text(encoding="utf-8"))["input"]["workflow"]


def _integer(value, name, minimum, maximum, multiple=None):
    if isinstance(value, bool) or not isinstance(value, int) or not minimum <= value <= maximum:
        raise ValueError(f"{name} must be an integer from {minimum} to {maximum}")
    if multiple and value % multiple:
        raise ValueError(f"{name} must be a multiple of {multiple}")
    return value


def _number(value, name, minimum, maximum):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not minimum <= value <= maximum:
        raise ValueError(f"{name} must be a number from {minimum} to {maximum}")
    return value


def _image(value, index):
    if isinstance(value, dict):
        value = value.get("image")
    if not isinstance(value, str) or not value:
        raise ValueError(f"images[{index}] must be a base64 image string")
    match = _DATA_URI.match(value)
    encoded = value[match.end():] if match else value
    try:
        raw = base64.b64decode(encoded, validate=True)
    except (ValueError, binascii.Error) as exc:
        raise ValueError(f"images[{index}] is not valid base64") from exc
    if raw.startswith(b"\x89PNG\r\n\x1a\n"):
        kind, suffix = "png", ".png"
    elif raw.startswith(b"\xff\xd8\xff"):
        kind, suffix = "jpeg", ".jpg"
    elif raw.startswith(b"RIFF") and raw[8:12] == b"WEBP":
        kind, suffix = "webp", ".webp"
    else:
        raise ValueError(f"images[{index}] must be PNG, JPEG or WebP")
    if match and match.group(1).lower() != kind:
        raise ValueError(f"images[{index}] data URI does not match image bytes")
    return f"data:image/{kind};base64,{encoded}", suffix


def expand_input(payload):
    """Return a worker-comfyui input dict; preserve explicit workflow requests."""
    if not isinstance(payload, dict):
        raise ValueError("input must be an object")
    if "workflow" in payload:
        return payload
    task = payload.get("task", "edit" if payload.get("images") else "t2i")
    if task not in {"t2i", "edit"}:
        raise ValueError("task must be t2i or edit")
    common = {"task", "prompt", "negative_prompt", "seed", "steps", "cfg"}
    allowed = common | ({"images", "resolution"} if task == "edit" else {"width", "height", "resolution"})
    unknown = set(payload) - allowed
    if unknown:
        raise ValueError(f"Unsupported input fields: {', '.join(sorted(unknown))}")
    prompt = payload.get("prompt")
    if not isinstance(prompt, str) or not prompt.strip():
        raise ValueError("prompt must be a non-empty string")
    negative = payload.get("negative_prompt", "")
    if not isinstance(negative, str):
        raise ValueError("negative_prompt must be a string")
    workflow = copy.deepcopy(_template(
        "qwen_image_2_1_multi_edit_input.template.json" if task == "edit" else "qwen_image_2_1_t2i_input.json"
    ))
    encoder = workflow["474" if task == "edit" else "452"]["inputs"]
    sampler = workflow["458"]["inputs"]
    encoder["prompt"] = prompt
    encoder["negative_prompt"] = negative
    if "seed" in payload:
        sampler["seed"] = _integer(payload["seed"], "seed", 0, 2**64 - 1)
    if "steps" in payload:
        sampler["steps"] = _integer(payload["steps"], "steps", 1, 100)
    if "cfg" in payload:
        sampler["cfg"] = _number(payload["cfg"], "cfg", 0, 20)
    if "resolution" in payload:
        encoder["resolution"] = _integer(payload["resolution"], "resolution", 0 if task == "edit" else 32, 4096, 32)
    if task == "t2i":
        latent = workflow["456"]["inputs"]
        for field in ("width", "height"):
            if field in payload:
                latent[field] = _integer(payload[field], field, 64, 2048, 32)
        return {"workflow": workflow}
    images = payload.get("images")
    if not isinstance(images, list) or not 1 <= len(images) <= 10:
        raise ValueError("edit requires 1 to 10 images")
    uploaded = []
    workflow.pop("470", None)
    workflow.pop("475", None)
    for key in list(encoder):
        if key.startswith("images.image_"):
            del encoder[key]
    for index, value in enumerate(images, 1):
        encoded, suffix = _image(value, index)
        name = f"input_image_{index}{suffix}"
        node_id = {1: "470", 2: "475"}.get(index, str(500 + index))
        uploaded.append({"name": name, "image": encoded})
        workflow[node_id] = {"class_type": "LoadImage", "inputs": {"image": name}}
        encoder[f"images.image_{index}"] = [node_id, 0]
    return {"workflow": workflow, "images": uploaded}
