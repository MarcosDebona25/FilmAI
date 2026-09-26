"""Pruebas del catálogo que une archivos estáticos e IDs persistidos."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import sync_avatars


class SyncAvatarsTests(unittest.TestCase):
    def test_archivo_eliminado_no_reutiliza_id(self):
        """Un usuario con un ID antiguo nunca recibe otra imagen por accidente."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            images = root / "images"
            images.mkdir()
            catalog = root / "catalog.json"
            (images / "avatar (1).png").touch()
            (images / "avatar (2).png").touch()
            with (
                patch.object(sync_avatars, "ROOT", root),
                patch.object(sync_avatars, "IMAGES", images),
                patch.object(sync_avatars, "CATALOG", catalog),
            ):
                sync_avatars.main()
                (images / "avatar (2).png").unlink()
                (images / "nuevo.png").touch()
                sync_avatars.main()
            data = json.loads(catalog.read_text(encoding="utf-8"))
            self.assertEqual({item["id"]: item["active"] for item in data}, {1: True, 2: False, 3: True})
            self.assertEqual(next(item["id"] for item in data if item["filename"] == "nuevo.png"), 3)


if __name__ == "__main__":
    unittest.main()
