# RunPod `input` requests

For ordinary requests, send only the values that change. Text-to-image accepts
`prompt` plus optional `negative_prompt`, `seed`, `steps`, `cfg`, `width`,
`height`, and `resolution`. Editing accepts `prompt`, `images` (1–10 PNG,
JPEG, or WebP base64 strings or data URIs), and optional `negative_prompt`,
`seed`, `steps`, `cfg`, and `resolution`. See `simple_t2i_input.json` and
`simple_edit_input.template.json`. The handler expands these into bundled
workflows; `workflow` requests remain supported.

- `USE_MOCK_PIPELINE=1` is reserved for the Hub handler health check. It
  returns a tiny PNG without loading ComfyUI or model weights; it does not
  validate GPU inference. Normal deployments use the default value `0`.

- `qwen_image_2_1_t2i_input.json` is a complete `{"input":{"workflow":...}}` text-to-image request.
- `qwen_image_2_1_multi_edit_input.template.json` is an edit request with two placeholder `input.images` values. Fill them with actual local images using the builder below; do not send the placeholder template directly.

```bash
python3 examples/build_edit_input.py /path/to/image1.png /path/to/image2.png \
  --output /private/tmp/qwen_edit_input.json
# Optional: --prompt 'your edit instruction' --seed 123
curl -sS -H "Authorization: Bearer $RUNPOD_API_KEY" \
  -H 'Content-Type: application/json' \
  --data-binary @/private/tmp/qwen_edit_input.json \
  "https://api.runpod.ai/v2/$ENDPOINT_ID/run"
```

For text-to-image, send `examples/qwen_image_2_1_t2i_input.json` in the same way. The generated edit request embeds 2–10 PNG/JPEG/WebP files in `input.images`, and its `LoadImage` names match the uploaded names. Images increase JSON size; RunPod enforces request-size limits.

Both API graphs use the Q5_K_M GGUF diffusion model, int8 text encoder and BF16 VAE installed by this repository. The source UI workflows selected Q6_K and BF16 text encoder, which are not provisioned by this worker. The edit subgraph is flattened for API execution, retaining its `resolution=0` and sampler settings; UI-only notes, comparison view and selector are omitted. The edit request requires `TextEncodeQwenImage21` and `QwenImage21Cache` from recent ComfyUI plus `UnetLoaderGGUF` from the GGUF extension. Local checks validate JSON and graph links, not GPU execution.
