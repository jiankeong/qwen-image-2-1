#!/usr/bin/env python3
"""Fill the RunPod Qwen-Image-2.1 edit input with local reference images."""

import argparse
import base64
import json
import sys
from pathlib import Path

TEMPLATE = Path(__file__).with_name("qwen_image_2_1_multi_edit_input.template.json")
SUFFIXES = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp"}


def build_request(paths, prompt=None, seed=None):
    if not 2 <= len(paths) <= 10:
        raise ValueError("Supply 2 to 10 input images")
    payload = json.loads(TEMPLATE.read_text(encoding="utf-8"))
    request = payload["input"]
    workflow = request["workflow"]
    request["images"] = []
    for index, path in enumerate(paths, 1):
        path = Path(path)
        kind = SUFFIXES.get(path.suffix.lower())
        if kind is None:
            raise ValueError(f"Use PNG, JPEG or WebP: {path}")
        data = path.read_bytes()
        if not data:
            raise ValueError(f"Empty image: {path}")
        filename = f"input_image_{index}{path.suffix.lower()}"
        request["images"].append({
            "name": filename,
            "image": f"data:{kind};base64,{base64.b64encode(data).decode('ascii')}",
        })
        node_id = {1: "470", 2: "475"}.get(index, str(500 + index))
        workflow[node_id] = {"class_type": "LoadImage", "inputs": {"image": filename}}
        workflow["474"]["inputs"][f"images.image_{index}"] = [node_id, 0]
    if prompt is not None:
        workflow["474"]["inputs"]["prompt"] = prompt
    if seed is not None:
        workflow["458"]["inputs"]["seed"] = seed
    return payload


def build_simple_request(paths, prompt=None, seed=None):
    """Build the compact input accepted by this repository's handler."""
    if not 1 <= len(paths) <= 10:
        raise ValueError("Supply 1 to 10 input images")
    template = json.loads(TEMPLATE.read_text(encoding="utf-8"))
    default_prompt = template["input"]["workflow"]["474"]["inputs"]["prompt"]
    result = {"input": {"prompt": prompt or default_prompt, "images": []}}
    for path in paths:
        path = Path(path)
        kind = SUFFIXES.get(path.suffix.lower())
        if kind is None:
            raise ValueError(f"Use PNG, JPEG or WebP: {path}")
        data = path.read_bytes()
        if not data:
            raise ValueError(f"Empty image: {path}")
        result["input"]["images"].append(
            f"data:{kind};base64,{base64.b64encode(data).decode('ascii')}"
        )
    if seed is not None:
        result["input"]["seed"] = seed
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("images", nargs="+", type=Path, help="1–10 local reference images, in order")
    parser.add_argument("--prompt", help="Override the edit instruction")
    parser.add_argument("--seed", type=int, help="Override the sampler seed")
    parser.add_argument("--output", type=Path, help="Write request JSON here (default: stdout)")
    parser.add_argument("--full-workflow", action="store_true", help="Emit the legacy full workflow request")
    args = parser.parse_args(argv)
    try:
        builder = build_request if args.full_workflow else build_simple_request
        payload = builder(args.images, args.prompt, args.seed)
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    result = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.write_text(result, encoding="utf-8")
    else:
        sys.stdout.write(result)


if __name__ == "__main__":
    main()
