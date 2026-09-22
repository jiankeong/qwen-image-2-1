"""Validate converted ComfyUI API graphs and RunPod image request builder."""

import base64
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from workflow_request import expand_input

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "examples"


def load_request(name):
    request = json.loads((EXAMPLES / name).read_text(encoding="utf-8"))
    assert set(request) == {"input"}
    return request["input"]


def check_links(workflow):
    for node_id, node in workflow.items():
        assert set(node) == {"class_type", "inputs"}, node_id
        for value in node["inputs"].values():
            if isinstance(value, list):
                assert len(value) == 2 and value[0] in workflow and isinstance(value[1], int), (node_id, value)


class WorkflowInputsTest(unittest.TestCase):
    def test_compact_t2i_input_expands_to_workflow(self):
        payload = load_request("simple_t2i_input.json")
        result = expand_input(payload)
        self.assertEqual(result["workflow"]["452"]["inputs"]["prompt"], payload["prompt"])
        self.assertEqual(result["workflow"]["456"]["inputs"]["width"], 1024)

    def test_compact_edit_input_expands_image_upload(self):
        image = base64.b64encode(b"\x89PNG\r\n\x1a\n" + b"demo").decode("ascii")
        result = expand_input({"prompt": "edit", "images": [image]})
        self.assertEqual(result["workflow"]["474"]["inputs"]["images.image_1"], ["470", 0])
        self.assertEqual(result["images"][0]["name"], "input_image_1.png")

    def test_edit_input_corrects_mislabeled_jpeg_data_uri(self):
        image = base64.b64encode(b"\xff\xd8\xff" + b"demo").decode("ascii")
        result = expand_input({"prompt": "edit", "images": [f"data:image/png;base64,{image}"]})
        self.assertEqual(result["images"][0]["name"], "input_image_1.jpg")
        self.assertTrue(result["images"][0]["image"].startswith("data:image/jpeg;base64,"))

    def test_text_to_image_input_uses_installed_models(self):
        request = load_request("qwen_image_2_1_t2i_input.json")
        workflow = request["workflow"]
        check_links(workflow)
        self.assertNotIn("nodes", workflow)
        self.assertEqual(workflow["451"]["inputs"]["unet_name"], "qwen-image-2.1-UC-Q4_K_M.gguf")
        self.assertEqual(workflow["453"]["inputs"]["clip_name"], "qwen3vl_8b_int8_convrot.safetensors")
        self.assertEqual(workflow["452"]["inputs"]["resolution"], 1024)
        self.assertEqual(workflow["458"]["inputs"]["latent_image"], ["456", 0])
        self.assertEqual(workflow["461"]["class_type"], "SaveImage")

    def test_edit_template_flattens_subgraph_and_has_image_slots(self):
        request = load_request("qwen_image_2_1_multi_edit_input.template.json")
        workflow = request["workflow"]
        check_links(workflow)
        self.assertEqual(workflow["474"]["inputs"]["resolution"], 0)
        self.assertEqual(workflow["474"]["inputs"]["images.image_1"], ["470", 0])
        self.assertEqual(workflow["474"]["inputs"]["images.image_2"], ["475", 0])
        self.assertEqual(workflow["458"]["inputs"]["latent_image"], ["474", 2])
        self.assertEqual(workflow["461"]["class_type"], "SaveImage")
        self.assertEqual([item["name"] for item in request["images"]], ["input_image_1.png", "input_image_2.png"])

    def test_builder_embeds_two_or_more_local_images(self):
        spec = importlib.util.spec_from_file_location("build_edit_input", EXAMPLES / "build_edit_input.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as temp:
            paths = [Path(temp) / f"{index}.png" for index in range(3)]
            for index, path in enumerate(paths):
                path.write_bytes(b"\x89PNG\r\n\x1a\n" + bytes([index]))
            request = module.build_request(paths, prompt="custom edit", seed=42)["input"]
            check_links(request["workflow"])
            self.assertEqual(len(request["images"]), 3)
            self.assertEqual(request["workflow"]["474"]["inputs"]["images.image_3"], ["503", 0])
            self.assertEqual(request["workflow"]["474"]["inputs"]["prompt"], "custom edit")
            self.assertEqual(request["workflow"]["458"]["inputs"]["seed"], 42)
            for index, image in enumerate(request["images"]):
                self.assertEqual(base64.b64decode(image["image"].split(",", 1)[1]), paths[index].read_bytes())


if __name__ == "__main__":
    unittest.main()
