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
        self.assertIn(suite["config"]["allowedCudaVersions"][0],
                      json.loads((ROOT / ".runpod/hub.json").read_text())["config"]["allowedCudaVersions"])
        test = suite["tests"][0]
        self.assertGreaterEqual(test["timeout"], 60000)
        nodes = test["input"]["workflow"]
        self.assertEqual(nodes["1"]["class_type"], "EmptyImage")
        self.assertEqual(nodes["2"]["class_type"], "SaveImage")
        self.assertEqual(nodes["2"]["inputs"]["images"], ["1", 0])

    def test_image_contains_all_model_weights(self):
        dockerfile = (ROOT / "Dockerfile").read_text()
        self.assertIn("FROM runpod/worker-comfyui:5.10.0-base", dockerfile)
        for name in (
            "qwen-image-2.1-Q4_K_M.gguf",
            "qwen3vl_8b_int8_convrot.safetensors",
            "qwen_image_2.1_vae_bf16.safetensors",
        ):
            self.assertIn(name, dockerfile)


if __name__ == "__main__":
    unittest.main()
