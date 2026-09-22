"""Validate the Hub listing and its model-independent image smoke test."""

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class HubConfigTest(unittest.TestCase):
    def test_hub_configuration(self):
        hub = json.loads((ROOT / ".runpod/hub.json").read_text())
        self.assertEqual((hub["type"], hub["category"]), ("serverless", "image"))
        config = hub["config"]
        self.assertEqual(config["runsOn"], "GPU")
        self.assertEqual(config["gpuCount"], 1)
        self.assertGreaterEqual(config["containerDiskInGb"], 30)
        self.assertIn("12.8", config["allowedCudaVersions"])

    def test_smoke_test_is_connected_and_model_independent(self):
        suite = json.loads((ROOT / ".runpod/tests.json").read_text())
        self.assertEqual(suite["config"]["gpuCount"], 1)
        hub_versions = set(json.loads((ROOT / ".runpod/hub.json").read_text())["config"]["allowedCudaVersions"])
        test_versions = set(suite["config"]["allowedCudaVersions"])
        self.assertTrue(test_versions <= hub_versions)
        self.assertIn("13.0", test_versions)
        test = suite["tests"][0]
        self.assertEqual(test["input"], {"healthcheck": True})
        self.assertEqual(test["timeout"], 30000)

    def test_models_are_deferred_to_worker_startup(self):
        dockerfile = (ROOT / "Dockerfile").read_text()
        bootstrap = (ROOT / "bootstrap_models.py").read_text()
        startup = (ROOT / "startup.sh").read_text()
        self.assertIn("FROM runpod/worker-comfyui:5.10.0-base", dockerfile)
        self.assertNotIn("comfy model download", dockerfile)
        self.assertIn("python /bootstrap_models.py", startup)
        for name in (
            "qwen-image-2.1-Q4_K_M.gguf",
            "qwen3vl_8b_int8_convrot.safetensors",
            "qwen_image_2.1_vae_bf16.safetensors",
        ):
            self.assertIn(name, bootstrap)
        suite = json.loads((ROOT / ".runpod/tests.json").read_text())
        self.assertIn({"key": "USE_MOCK_PIPELINE", "value": "1"}, suite["config"]["env"])


if __name__ == "__main__":
    unittest.main()
