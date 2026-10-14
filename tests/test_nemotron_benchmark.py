import importlib.util
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "nemotron_benchmark.py"
SPEC = importlib.util.spec_from_file_location("nemotron_benchmark", SCRIPT)
assert SPEC and SPEC.loader
benchmark = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(benchmark)


class NemotronBenchmarkTests(unittest.TestCase):
    def test_model_reference_is_official_nvidia_q4(self):
        self.assertEqual(
            benchmark.MODEL_REF,
            "nvidia/NVIDIA-Nemotron-3-Nano-4B-GGUF:Q4_K_M",
        )

    def test_valid_cue_json(self):
        result = benchmark.validate_cue_json(
            '{"cue":"Explain the local privacy benefit.","intent":"respond","should_offer":true}'
        )
        self.assertTrue(result["valid"])

    def test_json_can_be_extracted_from_extra_text(self):
        result = benchmark.validate_cue_json(
            'Answer: {"cue":"Mention both formats.","intent":"clarify","should_offer":true}'
        )
        self.assertTrue(result["valid"])

    def test_invalid_cue_schema_is_rejected(self):
        result = benchmark.validate_cue_json(
            '{"cue":"This cue contains far too many words and should be rejected by the strict validator now.",'
            '"intent":"unknown","should_offer":false}'
        )
        self.assertFalse(result["valid"])
        self.assertGreaterEqual(len(result["errors"]), 2)

    def test_tegrastats_summary(self):
        result = benchmark.summarize_tegrastats([
            "RAM 3000/7620MB GR3D_FREQ 75% cpu@51.5C gpu@53.0C VDD_IN 7200mW/6800mW",
            "RAM 3100/7620MB GR3D_FREQ 92% cpu@54.0C gpu@56.5C VDD_IN 8100mW/6900mW",
        ])
        self.assertEqual(result["max_gpu_utilization_percent"], 92)
        self.assertEqual(result["max_temperature_c"], 56.5)
        self.assertEqual(result["max_input_power_mw"], 8100)

    def test_assessment_requires_resource_headroom(self):
        trials = [{"success": True, "json_validation": {"valid": True}}]
        result = benchmark.assessment(trials, {
            "swap_growth_bytes": 0,
            "minimum_available_ram_bytes": 2 * 1024**3,
        })
        self.assertTrue(result["isolated_benchmark_passed"])
        low_memory = benchmark.assessment(trials, {
            "swap_growth_bytes": 0,
            "minimum_available_ram_bytes": 512 * 1024**2,
        })
        self.assertFalse(low_memory["isolated_benchmark_passed"])


if __name__ == "__main__":
    unittest.main()
