# Qwen-Image-2.1 GGUF on RunPod Serverless

This project extends the official RunPod ComfyUI worker with current ComfyUI and the `leejet/ComfyUI-GGUF` fork. Following the architecture of [the reference worker](https://github.com/jiankeong/qwen-image-edit-runpod), the Docker image includes code but **does not download the approximately 15.9 GB of weights during the Hub build**. At normal worker startup, `bootstrap_models.py` downloads the Q6_K transformer, int8 text encoder and BF16 VAE into `/runpod-volume/hf-cache` and links them into `/comfyui/models`. A network volume is recommended so later cold starts reuse the cache; without one, the configured container disk is used and downloads recur on new workers.

The Hub smoke test sets `USE_MOCK_PIPELINE=1`, which starts only the lightweight RunPod handler and returns a valid one-pixel PNG. It does not boot ComfyUI, download model files, or verify GPU inference. Normal inference defaults to `0` and delegates to the official ComfyUI worker.

## 1. Hub deployment

The root `Dockerfile`, `handler.py`, and `README.md`, plus `.runpod/hub.json` and `.runpod/tests.json`, provide the files required for a RunPod Hub listing. Create a new GitHub release after changes; the Hub indexes releases, not individual commits. Select the newest release. The Hub test checks handler startup and image output without starting ComfyUI; test Qwen generation separately after deployment. Model weights are downloaded at normal worker startup, not during the Hub build.

## 2. Persistent model cache

Attach a RunPod network volume to the endpoint to persist model downloads. The worker creates `/runpod-volume/hf-cache` and downloads the three Hugging Face assets on the first normal startup. Later workers with the same volume reuse the cached files. If no network volume is attached, the same path uses container disk and a new worker may need to download again. Allow at least 40 GB free for cache and runtime files. Do not pre-populate `/runpod-volume/models` with `download_models.sh` for this image; this startup path uses the Hugging Face cache instead.

## 3. Build and deploy

Push this repository to GitHub. In RunPod, choose **Serverless → New Endpoint → Start from GitHub Repo**, select the repository, set context `/` and Dockerfile `Dockerfile`. Select one GPU with at least 24 GB VRAM and adequate system RAM for the 9.35 GB text encoder; start with 0 active workers and 1 maximum worker. Allow at least 40 GB container disk for model cache and runtime when no network volume is attached. Deploy, then note the endpoint ID. The initial build installs ComfyUI and the GGUF fork; normal worker startup downloads the three model weights unless they are cached on its network volume.

## 4. Input parameters

Send a JSON object with an outer `input` key. For normal use, supply only the values that change; the handler fills in the bundled ComfyUI workflow.

### Text-to-image

```json
{
  "input": {
    "task": "t2i",
    "prompt": "A mountain lake at sunrise",
    "width": 1024,
    "height": 1024,
    "steps": 25,
    "seed": 42
  }
}
```

### Image editing

```json
{
  "input": {
    "task": "edit",
    "prompt": "Change the jacket to blue and keep the background",
    "images": ["data:image/jpeg;base64,REPLACE_WITH_IMAGE_BASE64"],
    "resolution": 1024,
    "steps": 12
  }
}
```

Replace the example image string with a real PNG, JPEG, or WebP file encoded as base64. You may pass a raw base64 string instead of a `data:image/...;base64,` URI. The image list accepts 1–10 images; each can also be an object such as `{"image":"data:image/jpeg;base64,..."}`. The handler detects the format from the bytes, including when a data URI has the wrong MIME label. To build an edit request from a local image without manually encoding it:

```bash
python3 examples/build_edit_input.py /path/to/input.jpg \
  --prompt "Change the jacket to blue" --output request.json
```

| `input` field | Applies to | Values and defaults |
| --- | --- | --- |
| `prompt` | Both | Required non-empty string. |
| `task` | Both | `t2i` or `edit`; inferred as `edit` when a non-empty `images` list is supplied, otherwise `t2i`. |
| `images` | Edit | Required list of 1–10 base64 images; PNG, JPEG, or WebP. |
| `negative_prompt` | Both | Optional string; defaults to `""`. |
| `seed` | Both | Integer from 0 to 2⁶⁴−1; if omitted, the bundled workflow's fixed seed is used. |
| `steps` | Both | Integer from 1 to 100; defaults to 25. |
| `cfg` | Both | Number from 0 to 20; defaults to 1. |
| `width`, `height` | Text-to-image | Integers from 64 to 2048, multiples of 32; default 1024×1024. |
| `resolution` | Both | Multiple of 32, up to 4096; text-to-image minimum 32 and default 1024; edit permits 0 and defaults to 0 (automatic image size). For large edit images, try 1024 to reduce memory and execution time. |

`input.workflow` is also supported for advanced use and is forwarded to the ComfyUI worker instead of expanding the compact fields. The [example requests](examples/README.md) include full workflow JSON. To construct your own, export an API workflow from ComfyUI, use **Unet Loader (GGUF)** with `qwen-image-2.1-UC-Q6_K.gguf`, the `qwen3vl_8b_int8_convrot.safetensors` text encoder, and `qwen_image_2.1_vae_bf16.safetensors` VAE.

### Submit a request

For either example above, save the JSON as `request.json`, then submit it to the endpoint:

```bash
export RUNPOD_API_KEY='YOUR_KEY'
export ENDPOINT_ID='YOUR_ENDPOINT_ID'
curl -sS -H "Authorization: Bearer ${RUNPOD_API_KEY}" -H 'Content-Type: application/json' \
  --data-binary @request.json "https://api.runpod.ai/v2/${ENDPOINT_ID}/run"
```

Poll `https://api.runpod.ai/v2/${ENDPOINT_ID}/status/JOB_ID` with the same Authorization header. The official worker returns generated images in `output.images`, normally base64 data unless S3 upload is configured. Do not commit API keys or generated `request.json`.

Sources: [model card](https://huggingface.co/abenzerps/Qwen-Image-2.1-Uncensored-GGUF), [RunPod Hub publishing guide](https://docs.runpod.io/hub/publishing-guide), [RunPod worker customization](https://github.com/runpod-workers/worker-comfyui/blob/main/docs/customization.md), [RunPod deployment](https://github.com/runpod-workers/worker-comfyui/blob/main/docs/deployment.md), [worker API](https://github.com/runpod-workers/worker-comfyui#api-specification).
