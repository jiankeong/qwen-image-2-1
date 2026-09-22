# Qwen-Image-2.1 GGUF on RunPod Serverless

This project extends the official RunPod ComfyUI worker with current ComfyUI and the `leejet/ComfyUI-GGUF` fork. Following the architecture of [the reference worker](https://github.com/jiankeong/qwen-image-edit-runpod), the Docker image includes code but **does not download the approximately 14.6 GB of weights during the Hub build**. At normal worker startup, `bootstrap_models.py` downloads the Q4_K_M transformer, int8 text encoder and BF16 VAE into `/runpod-volume/hf-cache` and links them into `/comfyui/models`. A network volume is recommended so later cold starts reuse the cache; without one, the configured container disk is used and downloads recur on new workers.

The Hub smoke test sets `USE_MOCK_PIPELINE=1`, which starts only the lightweight RunPod handler and returns a valid one-pixel PNG. It does not boot ComfyUI, download model files, or verify GPU inference. Normal inference defaults to `0` and delegates to the official ComfyUI worker.

## 1. Hub deployment

The root `Dockerfile`, `handler.py`, and `README.md`, plus `.runpod/hub.json` and `.runpod/tests.json`, provide the files required for a RunPod Hub listing. Create a new GitHub release after changes; the Hub indexes releases, not individual commits. Select the newest release. The Hub test checks handler startup and image output without starting ComfyUI; test Qwen generation separately after deployment. Model weights are downloaded at normal worker startup, not during the Hub build.

## 2. Persistent model cache

Attach a RunPod network volume to the endpoint to persist model downloads. The worker creates `/runpod-volume/hf-cache` and downloads the three Hugging Face assets on the first normal startup. Later workers with the same volume reuse the cached files. If no network volume is attached, the same path uses container disk and a new worker may need to download again. Allow at least 40 GB free for cache and runtime files. Do not pre-populate `/runpod-volume/models` with `download_models.sh` for this image; this startup path uses the Hugging Face cache instead.

## 3. Build and deploy

Push this repository to GitHub. In RunPod, choose **Serverless → New Endpoint → Start from GitHub Repo**, select the repository, set context `/` and Dockerfile `Dockerfile`. Select one GPU with at least 24 GB VRAM and adequate system RAM for the 9.35 GB text encoder; start with 0 active workers and 1 maximum worker. Allow at least 40 GB container disk for model cache and runtime when no network volume is attached. Deploy, then note the endpoint ID. The initial build installs ComfyUI and the GGUF fork; normal worker startup downloads the three model weights unless they are cached on its network volume.

## 4. Prepare and submit a workflow

For routine calls, send only changing values; see [`examples/README.md`](examples/README.md). For example, `{"input":{"prompt":"A mountain lake","width":1024,"height":1024}}` uses the bundled text-to-image workflow. For editing, include `input.images` as one to ten base64-encoded reference images. Full `input.workflow` requests remain supported. To construct a custom workflow, use the [official Qwen-Image-2.1 text-to-image workflow](https://github.com/Comfy-Org/workflow_templates/blob/main/templates/image_qwen_image_2_1_t2i.json) in ComfyUI. Replace its diffusion loader with **Unet Loader (GGUF)**, choose `qwen-image-2.1-Q4_K_M.gguf`, choose `qwen3vl_8b_int8_convrot.safetensors` in CLIPLoader with type `qwen_image`, and choose `qwen_image_2.1_vae_bf16.safetensors` in VAELoader. Set the prompt and save through **Workflow → Export (API)**. Send the exported JSON as `input.workflow`:

```bash
export RUNPOD_API_KEY='YOUR_KEY'
export ENDPOINT_ID='YOUR_ENDPOINT_ID'
python3 - <<'PY' > request.json
import json
with open('workflow_api.json', encoding='utf-8') as f:
    workflow = json.load(f)
print(json.dumps({'input': {'workflow': workflow}}))
PY
curl -sS -H "Authorization: Bearer ${RUNPOD_API_KEY}" -H 'Content-Type: application/json' \
  --data-binary @request.json "https://api.runpod.ai/v2/${ENDPOINT_ID}/run"
```

Poll `https://api.runpod.ai/v2/${ENDPOINT_ID}/status/JOB_ID` with the same Authorization header. The official worker returns generated images in `output.images`, normally base64 data unless S3 upload is configured. Do not commit API keys or generated `request.json`.

Sources: [model card](https://huggingface.co/abenzerps/Qwen-Image-2.1-GGUF), [RunPod Hub publishing guide](https://docs.runpod.io/hub/publishing-guide), [RunPod worker customization](https://github.com/runpod-workers/worker-comfyui/blob/main/docs/customization.md), [RunPod deployment](https://github.com/runpod-workers/worker-comfyui/blob/main/docs/deployment.md), [worker API](https://github.com/runpod-workers/worker-comfyui#api-specification).
