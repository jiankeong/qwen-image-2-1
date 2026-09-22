# Qwen-Image-2.1 GGUF on RunPod Serverless

This project extends the official RunPod ComfyUI worker with current ComfyUI and the `leejet/ComfyUI-GGUF` fork required by the linked model. The Q4_K_M transformer, int8 text encoder and BF16 VAE are baked into the image so a Hub deployment does not require a network volume. These three files total approximately 14.6 GB; allow build time and disk space for the download.

The repository's root `handler.py` defines `handler(event)` and explicitly calls `runpod.serverless.start()` for RunPod's repository check. The Dockerfile preserves the official worker implementation as `/worker_comfyui_handler.py` and delegates every job to it; the inherited `/start.sh` still starts ComfyUI first. Select the `main` branch (or the newest release), not `v0.1.0`: that original tag predates the handler file.

## 1. Hub deployment

The root `Dockerfile`, `handler.py`, and `README.md`, plus `.runpod/hub.json` and `.runpod/tests.json`, provide the files required for a RunPod Hub listing. Create a new GitHub release after changes; the Hub indexes releases, not individual commits. Select the newest release. The Hub test uses a tiny ComfyUI `EmptyImage` → `SaveImage` workflow to check startup, request handling and image output without spending time on diffusion; test Qwen generation with the workflow below after deployment. The Docker build downloads the weights from Hugging Face.

## 2. Optional: populate a network volume

The default image already contains the model files. For a custom image without baked weights, create a RunPod network volume in the same region as your endpoint. Attach it to a temporary Pod and, inside that Pod, run:

```bash
curl -fsSL https://raw.githubusercontent.com/jiankeong/qwen-image-2-1/main/download_models.sh -o /tmp/download_models.sh
bash /tmp/download_models.sh /runpod-volume/models
```

Alternatively copy this repository's `download_models.sh` into the Pod and run it there. Confirm these files exist:

```text
/runpod-volume/models/diffusion_models/qwen-image-2.1-Q4_K_M.gguf
/runpod-volume/models/text_encoders/qwen3vl_8b_int8_convrot.safetensors
/runpod-volume/models/vae/qwen_image_2.1_vae_bf16.safetensors
```

## 3. Build and deploy

Push this repository to GitHub. In RunPod, choose **Serverless → New Endpoint → Start from GitHub Repo**, select the repository, set context `/` and Dockerfile `Dockerfile`. Select one GPU with at least 24 GB VRAM and adequate system RAM for the 9.35 GB text encoder; start with 0 active workers and 1 maximum worker. Allow at least 40 GB container disk for the baked weights and runtime. Deploy, then note the endpoint ID. The initial build downloads the model and installs ComfyUI and the GGUF fork, so it can take time.

## 4. Prepare and submit a workflow

Use the [official Qwen-Image-2.1 text-to-image workflow](https://github.com/Comfy-Org/workflow_templates/blob/main/templates/image_qwen_image_2_1_t2i.json) in ComfyUI. Replace its diffusion loader with **Unet Loader (GGUF)**, choose `qwen-image-2.1-Q4_K_M.gguf`, choose `qwen3vl_8b_int8_convrot.safetensors` in CLIPLoader with type `qwen_image`, and choose `qwen_image_2.1_vae_bf16.safetensors` in VAELoader. Set the prompt and save through **Workflow → Export (API)**. Send the exported JSON as `input.workflow`:

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
