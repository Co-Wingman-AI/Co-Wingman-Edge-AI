import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "jetson_inventory.py"
SPEC = importlib.util.spec_from_file_location("jetson_inventory", SCRIPT)
assert SPEC and SPEC.loader
inventory = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(inventory)


class InventoryTests(unittest.TestCase):
    def test_missing_command_is_graceful(self):
        with mock.patch.object(inventory.shutil, "which", return_value=None):
            result = inventory.run_command(["missing-tool", "--version"])
        self.assertEqual(result["status"], inventory.NOT_DETECTED)

    def test_meminfo_parsing(self):
        fixture = "MemTotal: 1000 kB\nMemAvailable: 400 kB\nSwapTotal: 200 kB\nSwapFree: 50 kB\nShmem: 10 kB\n"
        with mock.patch.object(inventory, "read_text", return_value=fixture):
            result = inventory.parse_meminfo()
        self.assertEqual(result["used_bytes"], 600 * 1024)
        self.assertEqual(result["swap_used_bytes"], 150 * 1024)

    def test_sanitization_redacts_identity_and_project_path(self):
        raw = {
            "path": str(inventory.PROJECT_ROOT / "reports"),
            "home": "/home/alice/models",
            "serial": "Serial Number: ABC123",
            "pipewire": '\tuser-name: "alice"\n\thost-name: "jetson-one"\n\tcookie: 12345',
            "bluetooth": "bluez_source.DE_B7_11_4D_BC_30.handsfree_head_unit",
        }
        safe = inventory.sanitize(raw)
        rendered = json.dumps(safe)
        self.assertNotIn("alice", rendered)
        self.assertNotIn("ABC123", rendered)
        self.assertNotIn("jetson-one", rendered)
        self.assertNotIn("DE_B7_11_4D_BC_30", rendered)
        self.assertNotIn("12345", rendered)
        self.assertNotIn(str(inventory.PROJECT_ROOT), rendered)

    def test_reports_are_timestamped_and_valid(self):
        data = {
            "generated_at": "2026-01-01T00:00:00+00:00",
            "privacy": {},
            "device": {"is_jetson": False, "board_model": "test", "architecture": "arm64"},
            "compute": {},
            "memory": {"total_bytes": 1024},
            "storage": {},
            "python": {},
            "audio": {},
            "monitoring": {},
            "assessment": {
                "local_nemotron_feasibility_test_can_be_planned": False,
                "note": "test only",
            },
        }
        with tempfile.TemporaryDirectory() as temp:
            with mock.patch.object(inventory, "REPORTS_DIR", Path(temp)):
                md_path, json_path = inventory.write_reports(data)
            self.assertTrue(md_path.name.startswith("jetson_inventory_"))
            self.assertEqual(json.loads(json_path.read_text())["device"]["board_model"], "test")


if __name__ == "__main__":
    unittest.main()
