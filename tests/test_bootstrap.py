"""Offline checks for runtime model caching and Hub smoke-test bypass."""

import runpy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


class BootstrapTest(unittest.TestCase):
    def test_downloads_three_assets_and_reuses_symlinks(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            source = tmp / "source"
            source.write_bytes(b"model")
            calls = []

            def downloader(**kwargs):
                calls.append(kwargs["filename"])
                return str(source)

            module = __import__("bootstrap_models")
            model_root = tmp / "models"
            with patch.dict("os.environ", {"HF_TOKEN": "test-token"}):
                module.install_models(tmp / "cache", model_root, downloader)
                module.install_models(tmp / "cache", model_root, downloader)
            self.assertEqual(len(calls), 6)
            self.assertEqual(len(module.MODELS), 3)
            self.assertEqual(calls[0], "qwen-image-2.1-UC-Q4_K_M.gguf")
            for remote, relative in module.MODELS:
                target = model_root / relative
                self.assertTrue(target.is_symlink(), remote)
                self.assertEqual(target.resolve(), source.resolve())

    def test_startup_mock_skips_bootstrap_and_comfyui(self):
        script = (ROOT / "startup.sh").read_text()
        self.assertIn('if [ "${USE_MOCK_PIPELINE:-0}" = "1" ]; then', script)
        self.assertIn("exec python /handler.py", script)
        self.assertLess(script.index("exec python /handler.py"), script.index("python /bootstrap_models.py"))
        self.assertIn("exec /start.sh", script)


if __name__ == "__main__":
    unittest.main()
