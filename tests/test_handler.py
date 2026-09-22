"""Check the repository entrypoint without needing a GPU or RunPod account."""

import runpy
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import Mock, patch


ROOT = Path(__file__).resolve().parents[1]


class HandlerEntrypointTest(unittest.TestCase):
    def test_registers_the_official_worker_handler(self):
        official_handler = Mock(name="official_handler")
        start = Mock(name="runpod.serverless.start")
        runpod = types.ModuleType("runpod")
        runpod.serverless = types.SimpleNamespace(start=start)
        upstream = types.ModuleType("worker_comfyui_handler")
        upstream.handler = official_handler

        with patch.dict(sys.modules, {"runpod": runpod, "worker_comfyui_handler": upstream}):
            runpy.run_path(str(ROOT / "handler.py"), run_name="__main__")

        start.assert_called_once_with({"handler": official_handler})

    def test_dockerfile_preserves_upstream_and_inherited_startup(self):
        dockerfile = (ROOT / "Dockerfile").read_text()
        self.assertIn("RUN mv /handler.py /worker_comfyui_handler.py", dockerfile)
        self.assertIn("COPY handler.py /handler.py", dockerfile)
        self.assertNotIn("CMD ", dockerfile)


if __name__ == "__main__":
    unittest.main()
