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
            namespace = runpy.run_path(str(ROOT / "handler.py"), run_name="__main__")

        registered_handler = start.call_args.args[0]["handler"]
        self.assertIs(registered_handler, namespace["handler"])
        event = {"input": {"workflow": {}}}
        official_handler.return_value = {"images": []}
        self.assertEqual(registered_handler(event), {"images": []})
        official_handler.assert_called_once_with(event)

    def test_dockerfile_preserves_upstream_and_uses_bootstrap(self):
        dockerfile = (ROOT / "Dockerfile").read_text()
        self.assertIn("git -C /comfyui fetch --no-tags --depth 1 origin main", dockerfile)
        self.assertIn("git -C /comfyui checkout --detach FETCH_HEAD", dockerfile)
        self.assertNotIn("git -C /comfyui pull --ff-only", dockerfile)
        self.assertIn("RUN mv /handler.py /worker_comfyui_handler.py", dockerfile)
        self.assertIn("COPY handler.py /handler.py", dockerfile)
        self.assertIn('CMD ["sh", "/startup.sh"]', dockerfile)
        self.assertIn("COPY bootstrap_models.py /bootstrap_models.py", dockerfile)


if __name__ == "__main__":
    unittest.main()
