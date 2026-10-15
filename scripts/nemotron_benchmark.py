#!/usr/bin/env python3
"""Benchmark the official NVIDIA Nemotron 3 Nano 4B GGUF on a Jetson.

The script installs nothing, binds llama.cpp only to loopback, uses synthetic
prompts, and writes timestamped JSON and Markdown reports under ``reports/``.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import platform
import re
import shutil
import signal
import socket
import subprocess
import tempfile
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPORTS_DIR = PROJECT_ROOT / "reports"
MODEL_REF = "nvidia/NVIDIA-Nemotron-3-Nano-4B-GGUF:Q4_K_M"
MODEL_NAME = "NVIDIA Nemotron 3 Nano 4B Q4_K_M"
SAMPLE_INTERVAL_SECONDS = 0.5
MIN_FOLLOWUP_HEADROOM_BYTES = 1024**3
MAX_ACCEPTABLE_SWAP_GROWTH_BYTES = 256 * 1024**2

SYSTEM_PROMPT = """You are the local cue generator for Co-Wingman.
Use only the supplied synthetic conversation. Do not provide reasoning or chain-of-thought.
Return exactly one compact JSON object matching this schema:
{"cue":"string of at most 12 words","intent":"resume|clarify|respond","should_offer":true}
Do not use Markdown and do not add keys."""

SYNTHETIC_PROMPTS = (
    """Conversation:
Partner: Which part of the project should we test first?
User: I think the first thing is... I lost the phrase.
The user manually requested help. Produce a short cue that helps them resume.""",
    """Conversation:
Partner: Could you explain why the measurements need to be local?
User: Yes, because the conversation data should... one moment.
The user manually requested help. Produce a short cue that helps them respond.""",
    """Conversation:
Partner: Do you want the report in JSON or Markdown?
User: I need both, but I am trying to say how they differ.
The user manually requested help. Produce a short cue that helps them clarify.""",
)

REDACTIONS = (
    (re.compile(r"/home/[^/\s]+"), "/home/<user>"),
    (re.compile(r"/Users/[^/\s]+"), "/Users/<user>"),
    (re.compile(r"(?im)^\s*(user[-_ ]name|host[-_ ]name|cookie)\s*[:=]\s*.+$"), r"\1: <redacted>"),
    (re.compile(r"(?i)\b(?:[0-9a-f]{2}[:_-]){5}[0-9a-f]{2}\b"), "<redacted-device-id>"),
)


def read_text(path: Path, default: str = "not detected") -> str:
    try:
        value = (path.read_bytes() or b"").decode("utf-8", errors="replace").strip("\x00\n ")
        return value or default
    except OSError:
        return default


def sanitize(value: Any) -> Any:
    if isinstance(value, str):
        result = value.replace(str(PROJECT_ROOT), "<project_dir>")
        for pattern, replacement in REDACTIONS:
            result = pattern.sub(replacement, result)
        return result
    if isinstance(value, dict):
        return {key: sanitize(item) for key, item in value.items()}
    if isinstance(value, list):
        return [sanitize(item) for item in value]
    return value


def is_jetson() -> bool:
    model = read_text(Path("/proc/device-tree/model"), "")
    release = read_text(Path("/etc/nv_tegra_release"), "")
    return "jetson" in model.lower() or "tegra" in release.lower()


def parse_meminfo() -> dict[str, int]:
    values: dict[str, int] = {}
    raw = read_text(Path("/proc/meminfo"), "")
    for line in raw.splitlines():
        match = re.match(r"^(\w+):\s+(\d+)\s+kB", line)
        if match:
            values[match.group(1)] = int(match.group(2)) * 1024
    swap_total = values.get("SwapTotal", 0)
    swap_free = values.get("SwapFree", 0)
    return {
        "total_bytes": values.get("MemTotal", 0),
        "available_bytes": values.get("MemAvailable", 0),
        "swap_total_bytes": swap_total,
        "swap_used_bytes": max(0, swap_total - swap_free),
    }


def process_rss_bytes(pid: int) -> int:
    raw = read_text(Path(f"/proc/{pid}/status"), "")
    match = re.search(r"^VmRSS:\s+(\d+)\s+kB", raw, re.MULTILINE)
    return int(match.group(1)) * 1024 if match else 0


def thermal_snapshot() -> dict[str, float]:
    temperatures: dict[str, float] = {}
    for zone in Path("/sys/class/thermal").glob("thermal_zone*"):
        name = read_text(zone / "type", zone.name)
        raw = read_text(zone / "temp", "")
        try:
            value = float(raw)
        except ValueError:
            continue
        temperatures[name] = value / 1000.0 if value > 1000 else value
    return temperatures


class ResourceMonitor:
    def __init__(self, pid: int) -> None:
        self.pid = pid
        self.samples: list[dict[str, Any]] = []
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, name="resource-monitor", daemon=True)
        self._started = time.monotonic()

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        self._thread.join(timeout=3)

    def _run(self) -> None:
        while not self._stop.is_set():
            memory = parse_meminfo()
            self.samples.append({
                "elapsed_seconds": round(time.monotonic() - self._started, 3),
                **memory,
                "server_rss_bytes": process_rss_bytes(self.pid),
                "temperatures_c": thermal_snapshot(),
            })
            self._stop.wait(SAMPLE_INTERVAL_SECONDS)


class TegrastatsCapture:
    def __init__(self) -> None:
        self.process: subprocess.Popen[str] | None = None
        self.file = tempfile.TemporaryFile(mode="w+", encoding="utf-8")

    def start(self) -> None:
        executable = shutil.which("tegrastats")
        if not executable:
            return
        try:
            self.process = subprocess.Popen(
                [executable, "--interval", "1000"],
                stdout=self.file,
                stderr=subprocess.STDOUT,
                text=True,
            )
        except OSError:
            self.process = None

    def stop(self) -> list[str]:
        if self.process and self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=3)
        self.file.flush()
        self.file.seek(0)
        lines = [line.strip() for line in self.file if line.strip()]
        self.file.close()
        return lines


def summarize_tegrastats(lines: list[str]) -> dict[str, Any]:
    gpu_values: list[int] = []
    temperatures: list[float] = []
    input_power_mw: list[int] = []
    for line in lines:
        gpu_values.extend(int(value) for value in re.findall(r"GR3D_FREQ\s+(\d+)%", line))
        temperatures.extend(float(value) for value in re.findall(r"\b\w+@([0-9.]+)C", line))
        input_power_mw.extend(int(value) for value in re.findall(r"VDD_IN\s+(\d+)mW", line))
    return {
        "available": bool(lines),
        "sample_count": len(lines),
        "max_gpu_utilization_percent": max(gpu_values) if gpu_values else None,
        "max_temperature_c": max(temperatures) if temperatures else None,
        "max_input_power_mw": max(input_power_mw) if input_power_mw else None,
        "last_samples": lines[-10:],
    }


def summarize_resources(samples: list[dict[str, Any]]) -> dict[str, Any]:
    if not samples:
        return {"sample_count": 0}
    available = [sample["available_bytes"] for sample in samples if sample["available_bytes"]]
    swap = [sample["swap_used_bytes"] for sample in samples]
    rss = [sample["server_rss_bytes"] for sample in samples]
    all_temperatures = [
        temperature
        for sample in samples
        for temperature in sample["temperatures_c"].values()
    ]
    return {
        "sample_count": len(samples),
        "minimum_available_ram_bytes": min(available) if available else None,
        "maximum_server_rss_bytes": max(rss) if rss else None,
        "initial_swap_used_bytes": swap[0] if swap else None,
        "maximum_swap_used_bytes": max(swap) if swap else None,
        "swap_growth_bytes": max(swap) - swap[0] if swap else None,
        "maximum_sysfs_temperature_c": max(all_temperatures) if all_temperatures else None,
    }


def select_loopback_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def server_version(executable: Path) -> str:
    try:
        result = subprocess.run(
            [str(executable), "--version"],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return f"unavailable: {type(exc).__name__}"
    return (result.stdout or result.stderr).strip() or f"exit code {result.returncode}"


def wait_for_server(base_url: str, process: subprocess.Popen[str], timeout: int) -> float:
    started = time.monotonic()
    deadline = started + timeout
    last_error = "server not contacted"
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"llama-server exited during startup with code {process.returncode}")
        try:
            with urllib.request.urlopen(f"{base_url}/health", timeout=2) as response:
                if response.status == 200:
                    return time.monotonic() - started
        except urllib.error.HTTPError as exc:
            last_error = f"HTTP {exc.code}"
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            last_error = type(exc).__name__
        time.sleep(1)
    raise TimeoutError(f"llama-server was not ready after {timeout}s ({last_error})")


def stream_chat_request(
    base_url: str,
    prompt: str,
    max_tokens: int,
    timeout: int,
) -> dict[str, Any]:
    payload = {
        "model": MODEL_REF,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.0,
        "seed": 42,
        "max_tokens": max_tokens,
        "stream": True,
        "stream_options": {"include_usage": True},
    }
    request = urllib.request.Request(
        f"{base_url}/v1/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    started = time.monotonic()
    first_content_at: float | None = None
    chunks: list[str] = []
    usage: dict[str, Any] = {}
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            for raw_line in response:
                line = raw_line.decode("utf-8", errors="replace").strip()
                if not line.startswith("data:"):
                    continue
                value = line[5:].strip()
                if not value or value == "[DONE]":
                    continue
                event = json.loads(value)
                if isinstance(event.get("usage"), dict):
                    usage = event["usage"]
                choices = event.get("choices") or []
                if choices:
                    delta = choices[0].get("delta", {})
                    content = delta.get("content") or delta.get("reasoning_content") or ""
                    if content:
                        if first_content_at is None:
                            first_content_at = time.monotonic()
                        chunks.append(content)
    except Exception as exc:
        return {
            "success": False,
            "error": f"{type(exc).__name__}: {exc}",
            "duration_seconds": round(time.monotonic() - started, 3),
        }
    finished = time.monotonic()
    content = "".join(chunks).strip()
    ttft = first_content_at - started if first_content_at is not None else None
    completion_tokens = usage.get("completion_tokens")
    decode_seconds = finished - first_content_at if first_content_at is not None else None
    return {
        "success": bool(content),
        "duration_seconds": round(finished - started, 3),
        "time_to_first_content_seconds": round(ttft, 3) if ttft is not None else None,
        "completion_tokens": completion_tokens,
        "output_tokens_per_second": (
            round(completion_tokens / decode_seconds, 3)
            if isinstance(completion_tokens, int) and decode_seconds and decode_seconds > 0
            else None
        ),
        "usage": usage,
        "content": content,
    }


def extract_json_object(text: str) -> dict[str, Any] | None:
    decoder = json.JSONDecoder()
    for match in re.finditer(r"\{", text):
        try:
            value, _ = decoder.raw_decode(text[match.start():])
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            return value
    return None


def validate_cue_json(text: str) -> dict[str, Any]:
    value = extract_json_object(text)
    errors: list[str] = []
    if value is None:
        return {"valid": False, "errors": ["No JSON object found."], "parsed": None}
    if set(value) != {"cue", "intent", "should_offer"}:
        errors.append("JSON keys do not exactly match the requested schema.")
    cue = value.get("cue")
    if not isinstance(cue, str) or not cue.strip():
        errors.append("cue must be a non-empty string.")
    elif len(cue.split()) > 12:
        errors.append("cue exceeds 12 words.")
    if value.get("intent") not in {"resume", "clarify", "respond"}:
        errors.append("intent is not an allowed value.")
    if value.get("should_offer") is not True:
        errors.append("should_offer must be true for the manual-help fixture.")
    return {"valid": not errors, "errors": errors, "parsed": value}


def unique_report_paths() -> tuple[Path, Path]:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    stamp = dt.datetime.now().astimezone().strftime("%Y%m%d_%H%M%S")
    suffix = ""
    counter = 0
    while True:
        json_path = REPORTS_DIR / f"nemotron_benchmark_{stamp}{suffix}.json"
        markdown_path = REPORTS_DIR / f"nemotron_benchmark_{stamp}{suffix}.md"
        if not json_path.exists() and not markdown_path.exists():
            return markdown_path, json_path
        counter += 1
        suffix = f"_{counter:02d}"


def assessment(trials: list[dict[str, Any]], resources: dict[str, Any]) -> dict[str, Any]:
    all_requests_succeeded = bool(trials) and all(trial.get("success") for trial in trials)
    all_json_valid = bool(trials) and all(trial.get("json_validation", {}).get("valid") for trial in trials)
    swap_growth = resources.get("swap_growth_bytes")
    min_available = resources.get("minimum_available_ram_bytes")
    swap_ok = isinstance(swap_growth, int) and swap_growth <= MAX_ACCEPTABLE_SWAP_GROWTH_BYTES
    headroom_ok = isinstance(min_available, int) and min_available >= MIN_FOLLOWUP_HEADROOM_BYTES
    isolated_pass = all_requests_succeeded and all_json_valid and swap_ok and headroom_ok
    return {
        "isolated_benchmark_passed": isolated_pass,
        "all_requests_succeeded": all_requests_succeeded,
        "all_json_outputs_valid": all_json_valid,
        "swap_growth_within_256_mib": swap_ok,
        "at_least_1_gib_ram_headroom": headroom_ok,
        "next_gate": (
            "Review measurements, then design a separate NVIDIA ASR concurrency test."
            if isolated_pass
            else "Review failures or resource pressure before adding any concurrent model."
        ),
        "warning": "An isolated pass does not prove that the complete Co-Wingman pipeline fits or meets latency targets.",
    }


def human_bytes(value: Any) -> str:
    if not isinstance(value, int):
        return "not detected" if value is None else str(value)
    amount = float(value)
    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if amount < 1024 or unit == "TiB":
            return f"{amount:.2f} {unit}"
        amount /= 1024
    return str(value)


def render_markdown(data: dict[str, Any]) -> str:
    lines = [
        "# NVIDIA Nemotron isolated benchmark",
        "",
        f"Generated: {data['generated_at']}",
        "",
        f"- Jetson verified: **{'yes' if data['environment']['is_jetson'] else 'no'}**",
        f"- Model: `{data['model']['reference']}`",
        f"- Context size: {data['configuration']['context_size']}",
        f"- Server load time: {data.get('server_load_seconds', 'not completed')} seconds",
        f"- Isolated benchmark passed: **{'yes' if data['assessment']['isolated_benchmark_passed'] else 'no'}**",
        f"- Minimum available RAM: {human_bytes(data['resources'].get('minimum_available_ram_bytes'))}",
        f"- Maximum server RSS: {human_bytes(data['resources'].get('maximum_server_rss_bytes'))}",
        f"- Swap growth: {human_bytes(data['resources'].get('swap_growth_bytes'))}",
        "",
        "> An isolated pass is not proof that the complete concurrent speech pipeline is feasible.",
        "",
        "## Measured trials",
        "",
        "| Trial | Success | Valid JSON | First content (s) | Total (s) | Output tok/s |",
        "|---:|:---:|:---:|---:|---:|---:|",
    ]
    for index, trial in enumerate(data["trials"], 1):
        lines.append(
            f"| {index} | {'yes' if trial.get('success') else 'no'} | "
            f"{'yes' if trial.get('json_validation', {}).get('valid') else 'no'} | "
            f"{trial.get('time_to_first_content_seconds')} | {trial.get('duration_seconds')} | "
            f"{trial.get('output_tokens_per_second')} |"
        )
    lines.extend([
        "",
        "## Assessment",
        "",
        "```json",
        json.dumps(data["assessment"], indent=2),
        "```",
        "",
        "## Resource summary",
        "",
        "```json",
        json.dumps({"system": data["resources"], "tegrastats": data["tegrastats"]}, indent=2),
        "```",
        "",
        "## Outputs",
        "",
    ])
    for index, trial in enumerate(data["trials"], 1):
        lines.extend([
            f"### Trial {index}",
            "",
            "```json",
            json.dumps(trial.get("json_validation", {}), indent=2),
            "```",
            "",
        ])
    return "\n".join(lines).rstrip() + "\n"


def write_reports(data: dict[str, Any]) -> tuple[Path, Path]:
    markdown_path, json_path = unique_report_paths()
    safe = sanitize(data)
    json_path.write_text(json.dumps(safe, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    markdown_path.write_text(render_markdown(safe), encoding="utf-8")
    return markdown_path, json_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--server", required=True, type=Path, help="Path to CUDA-enabled llama-server")
    parser.add_argument("--context-size", type=int, default=4096, choices=(2048, 4096, 8192))
    parser.add_argument("--trials", type=int, default=3, choices=range(1, 11), metavar="1-10")
    parser.add_argument("--startup-timeout", type=int, default=900, help="Seconds allowed for download and load")
    parser.add_argument("--request-timeout", type=int, default=180, help="Seconds allowed per request")
    parser.add_argument("--allow-non-jetson", action="store_true", help=argparse.SUPPRESS)
    return parser.parse_args()


def terminate_process(process: subprocess.Popen[str]) -> None:
    if process.poll() is not None:
        return
    process.send_signal(signal.SIGTERM)
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def main() -> int:
    args = parse_args()
    server = args.server.expanduser().resolve()
    if not server.is_file() or not os.access(server, os.X_OK):
        print(f"Error: llama-server is not executable: {server}")
        return 2
    jetson = is_jetson()
    if not jetson and not args.allow_non_jetson:
        print("Error: NVIDIA Jetson was not detected. Run this benchmark on the target Jetson.")
        return 2

    try:
        port = select_loopback_port()
    except OSError as exc:
        print(f"Error: cannot reserve a loopback port for the local server: {exc}")
        return 2
    base_url = f"http://127.0.0.1:{port}"
    command = [
        str(server), "-hf", MODEL_REF, "-c", str(args.context_size),
        "--alias", MODEL_REF, "-ngl", "28", "--port", str(port), "--host", "127.0.0.1", "--no-reasoning-preserve",
    ]
    server_log = tempfile.TemporaryFile(mode="w+", encoding="utf-8")
    process: subprocess.Popen[str] | None = None
    monitor: ResourceMonitor | None = None
    tegrastats = TegrastatsCapture()
    trials: list[dict[str, Any]] = []
    load_seconds: float | None = None
    failure: str | None = None
    started_at = dt.datetime.now().astimezone()

    print(f"Starting local benchmark server for {MODEL_REF}")
    print("The first run may download approximately 2.84 GB to the Jetson model cache.")
    try:
        process = subprocess.Popen(
            command,
            stdout=server_log,
            stderr=subprocess.STDOUT,
            text=True,
            start_new_session=True,
        )
        monitor = ResourceMonitor(process.pid)
        monitor.start()
        tegrastats.start()
        load_seconds = wait_for_server(base_url, process, args.startup_timeout)
        print(f"Server ready after {load_seconds:.1f} seconds. Running warm-up.")
        warmup = stream_chat_request(
            base_url,
            "Return the requested JSON with cue set to ready, intent set to respond, and should_offer true.",
            160,
            args.request_timeout,
        )
        if not warmup.get("success"):
            raise RuntimeError(f"Warm-up request failed: {warmup.get('error', 'empty output')}")

        for index in range(args.trials):
            print(f"Measured trial {index + 1}/{args.trials}")
            result = stream_chat_request(
                base_url,
                SYNTHETIC_PROMPTS[index % len(SYNTHETIC_PROMPTS)],
                160,
                args.request_timeout,
            )
            result["json_validation"] = validate_cue_json(result.get("content", ""))
            trials.append(result)
    except KeyboardInterrupt:
        failure = "Interrupted by user."
    except Exception as exc:
        failure = f"{type(exc).__name__}: {exc}"
    finally:
        if monitor:
            monitor.stop()
        tegrastats_lines = tegrastats.stop()
        if process:
            terminate_process(process)
        server_log.flush()
        server_log.seek(0)
        log_tail = server_log.readlines()[-40:]
        server_log.close()

    resource_summary = summarize_resources(monitor.samples if monitor else [])
    data = {
        "report_schema_version": 1,
        "generated_at": started_at.isoformat(timespec="seconds"),
        "environment": {
            "is_jetson": jetson,
            "board_model": read_text(Path("/proc/device-tree/model")),
            "architecture": platform.machine(),
            "kernel": platform.release(),
            "l4t_release": read_text(Path("/etc/nv_tegra_release")),
        },
        "model": {
            "name": MODEL_NAME,
            "reference": MODEL_REF,
            "developer": "NVIDIA Corporation",
            "quantization": "Q4_K_M",
        },
        "configuration": {
            "context_size": args.context_size,
            "measured_trials_requested": args.trials,
            "gpu_layers_requested": 999,
            "server_bind": "127.0.0.1",
            "synthetic_prompts_only": True,
            "server_version": server_version(server),
        },
        "server_load_seconds": round(load_seconds, 3) if load_seconds is not None else None,
        "trials": trials,
        "resources": resource_summary,
        "tegrastats": summarize_tegrastats(tegrastats_lines),
        "failure": failure,
        "server_log_tail_on_failure": [line.rstrip() for line in log_tail] if failure else [],
    }
    data["assessment"] = assessment(trials, resource_summary)
    markdown_path, json_path = write_reports(data)
    print(f"Markdown report: {markdown_path.relative_to(PROJECT_ROOT)}")
    print(f"JSON report: {json_path.relative_to(PROJECT_ROOT)}")
    if failure:
        print(f"Benchmark did not complete: {failure}")
        return 1
    print("Benchmark complete. Review the reports before adding any concurrent model.")
    return 0 if data["assessment"]["isolated_benchmark_passed"] else 3


if __name__ == "__main__":
    raise SystemExit(main())
