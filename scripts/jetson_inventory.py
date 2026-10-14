#!/usr/bin/env python3
"""Create a privacy-conscious, read-only NVIDIA Jetson inventory report."""

from __future__ import annotations

import datetime as dt
import importlib.metadata
import importlib.util
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


UNKNOWN = "unknown"
NOT_DETECTED = "not detected"
COMMAND_TIMEOUT_SECONDS = 5
PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPORTS_DIR = PROJECT_ROOT / "reports"


def read_text(path: Path, default: str = UNKNOWN) -> str:
    try:
        value = path.read_text(encoding="utf-8", errors="replace").strip("\x00\n ")
        return value or default
    except (OSError, PermissionError):
        return default


def run_command(command: list[str], timeout: int = COMMAND_TIMEOUT_SECONDS) -> dict[str, Any]:
    executable = shutil.which(command[0])
    if not executable:
        return {"status": NOT_DETECTED, "command": command[0]}
    try:
        result = subprocess.run(
            [executable, *command[1:]],
            capture_output=True,
            text=True,
            errors="replace",
            timeout=timeout,
            check=False,
            env={**os.environ, "LC_ALL": "C", "LANG": "C"},
        )
    except subprocess.TimeoutExpired:
        return {"status": "timeout", "command": command[0]}
    except OSError as exc:
        return {"status": "error", "command": command[0], "detail": str(exc)}
    output = (result.stdout or result.stderr).strip()
    return {
        "status": "ok" if result.returncode == 0 else "unavailable",
        "command": command[0],
        "return_code": result.returncode,
        "output": output or NOT_DETECTED,
    }


def parse_os_release() -> dict[str, str]:
    values: dict[str, str] = {}
    raw = read_text(Path("/etc/os-release"), "")
    for line in raw.splitlines():
        if "=" in line and not line.startswith("#"):
            key, value = line.split("=", 1)
            values[key] = value.strip().strip('"')
    return values


def parse_meminfo() -> dict[str, int | str]:
    values: dict[str, int] = {}
    raw = read_text(Path("/proc/meminfo"), "")
    for line in raw.splitlines():
        match = re.match(r"^(\w+):\s+(\d+)\s+kB", line)
        if match:
            values[match.group(1)] = int(match.group(2)) * 1024
    total = values.get("MemTotal")
    available = values.get("MemAvailable")
    free = values.get("MemFree")
    buffers = values.get("Buffers", 0)
    cached = values.get("Cached", 0)
    if available is None and free is not None:
        available = free + buffers + cached
    used = total - available if total is not None and available is not None else None
    return {
        "total_bytes": total if total is not None else UNKNOWN,
        "available_bytes": available if available is not None else UNKNOWN,
        "used_bytes": used if used is not None else UNKNOWN,
        "swap_total_bytes": values.get("SwapTotal", UNKNOWN),
        "swap_free_bytes": values.get("SwapFree", UNKNOWN),
        "swap_used_bytes": (
            values["SwapTotal"] - values["SwapFree"]
            if "SwapTotal" in values and "SwapFree" in values
            else UNKNOWN
        ),
        "shared_memory_bytes": values.get("Shmem", UNKNOWN),
    }


def find_mount(path: Path) -> dict[str, Any]:
    resolved = path.resolve()
    best: tuple[Path, str, str] | None = None
    raw = read_text(Path("/proc/self/mounts"), "")
    for line in raw.splitlines():
        fields = line.split()
        if len(fields) < 4:
            continue
        mount = Path(fields[1].replace("\\040", " "))
        try:
            resolved.relative_to(mount)
        except ValueError:
            continue
        if best is None or len(mount.parts) > len(best[0].parts):
            best = (mount, fields[2], fields[3])
    usage = shutil.disk_usage(resolved)
    fs_type = best[1] if best else UNKNOWN
    linux_semantics = fs_type.lower() not in {
        "vfat", "msdos", "exfat", "ntfs", "fuseblk", "hfs", "hfsplus"
    } if fs_type != UNKNOWN else UNKNOWN
    return {
        "filesystem_type": fs_type,
        "mount_category": (
            "removable_media" if best and str(best[0]).startswith(("/media/", "/run/media/"))
            else "system_or_other"
        ),
        "total_bytes": usage.total,
        "free_bytes": usage.free,
        "project_writable": os.access(resolved, os.W_OK),
        "likely_linux_permissions": linux_semantics,
        "mount_options": sorted(
            option for option in (best[2].split(",") if best else [])
            if option in {"ro", "rw", "noexec", "nosuid", "nodev"}
        ),
    }


def test_symlink_support() -> bool | str:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    try:
        with tempfile.TemporaryDirectory(prefix="inventory_probe_", dir=REPORTS_DIR) as temp:
            root = Path(temp)
            target = root / "target"
            link = root / "link"
            target.write_text("probe", encoding="utf-8")
            link.symlink_to(target.name)
            return link.is_symlink() and link.resolve() == target.resolve()
    except (OSError, NotImplementedError):
        return False


def package_version(*names: str) -> str:
    for name in names:
        try:
            return importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            continue
    return NOT_DETECTED


def debian_package_version(name: str) -> str:
    result = run_command(["dpkg-query", "-W", "-f=${Version}", name])
    return str(result.get("output", NOT_DETECTED)) if result["status"] == "ok" else NOT_DETECTED


def module_status(module: str, *packages: str) -> dict[str, Any]:
    installed = importlib.util.find_spec(module) is not None
    return {
        "installed": installed,
        "version": package_version(*(packages or (module,))) if installed else NOT_DETECTED,
    }


def python_environment() -> dict[str, Any]:
    pip = run_command([sys.executable, "-m", "pip", "--version"])
    torch = module_status("torch", "torch")
    torch["cuda_available"] = UNKNOWN
    torch["cuda_version"] = UNKNOWN
    if torch["installed"]:
        try:
            import torch as torch_module  # type: ignore
            torch["cuda_available"] = bool(torch_module.cuda.is_available())
            torch["cuda_version"] = torch_module.version.cuda or NOT_DETECTED
        except Exception as exc:  # installed packages can fail to load on mismatched architectures
            torch["import_error"] = type(exc).__name__
    return {
        "version": platform.python_version(),
        "implementation": platform.python_implementation(),
        "pip": pip.get("output", pip["status"]),
        "virtual_environment": bool(
            os.environ.get("VIRTUAL_ENV") or getattr(sys, "base_prefix", sys.prefix) != sys.prefix
        ),
        "packages": {
            "torch": torch,
            "torchvision": module_status("torchvision", "torchvision"),
            "torchaudio": module_status("torchaudio", "torchaudio"),
            "nvidia_nemo": module_status("nemo", "nemo-toolkit"),
            "onnxruntime": module_status("onnxruntime", "onnxruntime", "onnxruntime-gpu"),
            "tensorrt": module_status("tensorrt", "tensorrt"),
            "tensorrt_llm": module_status("tensorrt_llm", "tensorrt-llm"),
        },
        "executables": {
            "llama_cpp": (
                shutil.which("llama-cli") or shutil.which("llama-server") or NOT_DETECTED
            ),
            "trtllm_build": shutil.which("trtllm-build") or NOT_DETECTED,
        },
    }


def dpkg_nvidia_packages() -> list[dict[str, str]] | str:
    result = run_command([
        "dpkg-query", "-W", "-f=${binary:Package}\t${Version}\n",
        "cuda*", "libcudnn*", "libnvinfer*", "nvidia*", "nvidia-l4t*",
    ])
    if result["status"] not in {"ok", "unavailable"}:
        return NOT_DETECTED
    packages = []
    for line in str(result.get("output", "")).splitlines():
        if "\t" in line and not line.startswith("dpkg-query:"):
            name, version = line.split("\t", 1)
            packages.append({"name": name, "version": version})
    return packages or NOT_DETECTED


def command_output(command: list[str]) -> str:
    result = run_command(command)
    return str(result.get("output", result["status"]))


def accelerator_device_nodes() -> list[str] | str:
    nodes = {
        path.name
        for pattern in ("nvhost*", "nvidia*", "tegra*")
        for path in Path("/dev").glob(pattern)
    }
    return sorted(nodes) or NOT_DETECTED


def collect_inventory() -> dict[str, Any]:
    model = read_text(Path("/proc/device-tree/model"))
    l4t = read_text(Path("/etc/nv_tegra_release"), NOT_DETECTED)
    is_jetson = "jetson" in model.lower() or "tegra" in l4t.lower()
    os_release = parse_os_release()
    cuda_version = read_text(Path("/usr/local/cuda/version.json"), NOT_DETECTED)
    if cuda_version == NOT_DETECTED:
        cuda_version = command_output(["nvcc", "--version"])

    memory = parse_meminfo()
    storage = {
        "internal_root": find_mount(Path("/")),
        "project_volume": find_mount(PROJECT_ROOT),
    }
    storage["project_volume"]["symlink_supported"] = test_symlink_support()
    python = python_environment()

    missing_for_next_step = []
    if not is_jetson:
        missing_for_next_step.append("Execution on an NVIDIA Jetson was not verified.")
    if l4t == NOT_DETECTED:
        missing_for_next_step.append("L4T release was not detected.")
    if memory["total_bytes"] == UNKNOWN:
        missing_for_next_step.append("Total physical memory was not detected.")
    if storage["project_volume"]["filesystem_type"] == UNKNOWN:
        missing_for_next_step.append("Project filesystem type was not detected.")

    return {
        "report_schema_version": 1,
        "generated_at": dt.datetime.now().astimezone().isoformat(timespec="seconds"),
        "privacy": {
            "identifiers_omitted": [
                "device serial numbers", "user names", "home directory", "full mount paths"
            ],
            "review_before_sharing": True,
        },
        "device": {
            "is_jetson": is_jetson,
            "board_model": model,
            "architecture": platform.machine() or UNKNOWN,
            "linux_distribution": os_release.get("PRETTY_NAME", UNKNOWN),
            "kernel": platform.release() or UNKNOWN,
            "jetpack_version": debian_package_version("nvidia-jetpack"),
            "l4t_release": l4t,
            "nvidia_board_release": l4t,
        },
        "compute": {
            "cuda_toolkit": cuda_version,
            "nvidia_driver": read_text(Path("/proc/driver/nvidia/version"), NOT_DETECTED),
            "cuda_runtime_libraries": command_output(["ldconfig", "-p"]),
            "cudnn_packages": command_output(["dpkg-query", "-W", "libcudnn*"]),
            "tensorrt_packages": command_output(["dpkg-query", "-W", "libnvinfer*"]),
            "nvidia_packages": dpkg_nvidia_packages(),
            "cpu": command_output(["lscpu"]),
            "gpu_or_accelerators": command_output(["lspci"]),
            "accelerator_device_nodes": accelerator_device_nodes(),
            "device_tree_compatible": read_text(
                Path("/proc/device-tree/compatible"), NOT_DETECTED
            ).replace("\x00", ", "),
            "power_mode": command_output(["nvpmodel", "-q"]),
            "nvidia_smi": command_output(["nvidia-smi"]),
        },
        "memory": memory,
        "storage": storage,
        "python": python,
        "audio": {
            "alsa_available": shutil.which("arecord") is not None or Path("/proc/asound").exists(),
            "input_devices": command_output(["arecord", "-l"]),
            "output_devices": command_output(["aplay", "-l"]),
            "pulseaudio": command_output(["pactl", "info"]),
            "pipewire": command_output(["pw-cli", "info", "0"]),
            "sample_rate_note": "Not probed to avoid opening or disrupting audio devices.",
        },
        "monitoring": {
            name: {"available": shutil.which(name) is not None, "path": shutil.which(name) or NOT_DETECTED}
            for name in ("tegrastats", "jetson_clocks", "nvpmodel", "jtop")
        },
        "assessment": {
            "local_nemotron_feasibility_test_can_be_planned": not missing_for_next_step,
            "support_claim": False,
            "note": (
                "Inventory sufficient to plan a separate measured NVIDIA Nemotron feasibility test; "
                "this is not a compatibility or performance claim."
                if not missing_for_next_step
                else "More verified Jetson inventory data is required before planning the feasibility test."
            ),
            "missing_information": missing_for_next_step or ["None at the inventory-gate level."],
        },
    }


SENSITIVE_PATTERNS = (
    (re.compile(r"(?i)(serial(?: number)?|machine[-_ ]id)\s*[:=]\s*\S+"), r"\1: <redacted>"),
    (re.compile(r"(?im)^(user name|host name)\s*:\s*.+$"), r"\1: <redacted>"),
    (re.compile(r"(?i)\b(?:GPU-)?[0-9a-f]{8}-[0-9a-f-]{27,}\b"), "<redacted-uuid>"),
    (re.compile(r"/home/[^/\s]+"), "/home/<user>"),
    (re.compile(r"/Users/[^/\s]+"), "/Users/<user>"),
)


def sanitize(value: Any) -> Any:
    if isinstance(value, str):
        result = value.replace(str(PROJECT_ROOT), "<project_dir>")
        for pattern, replacement in SENSITIVE_PATTERNS:
            result = pattern.sub(replacement, result)
        return result
    if isinstance(value, dict):
        return {key: sanitize(item) for key, item in value.items()}
    if isinstance(value, list):
        return [sanitize(item) for item in value]
    return value


def human_bytes(value: Any) -> str:
    if not isinstance(value, int):
        return str(value)
    amount = float(value)
    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if amount < 1024 or unit == "TiB":
            return f"{amount:.1f} {unit}"
        amount /= 1024
    return str(value)


def markdown_value(value: Any) -> str:
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, (dict, list)):
        return "```json\n" + json.dumps(value, indent=2, ensure_ascii=False) + "\n```"
    text = str(value)
    return text if "\n" not in text else "```text\n" + text + "\n```"


def render_markdown(data: dict[str, Any]) -> str:
    lines = [
        "# NVIDIA Jetson inventory",
        "",
        f"Generated: {data['generated_at']}",
        "",
        "> This report intentionally omits serial numbers, user names, home directories, and full mount paths.",
        "",
        "## Summary",
        "",
        f"- Jetson execution verified: **{markdown_value(data['device']['is_jetson'])}**",
        f"- Board model: {data['device']['board_model']}",
        f"- Architecture: {data['device']['architecture']}",
        f"- Nemotron feasibility test can be planned: **{markdown_value(data['assessment']['local_nemotron_feasibility_test_can_be_planned'])}**",
        f"- Assessment: {data['assessment']['note']}",
        "",
        "## Memory summary",
        "",
    ]
    for key, value in data["memory"].items():
        lines.append(f"- {key.replace('_', ' ').title()}: {human_bytes(value)}")
    for section in ("device", "compute", "storage", "python", "audio", "monitoring", "assessment"):
        lines.extend(["", f"## {section.title()}", ""])
        for key, value in data[section].items():
            lines.extend([f"### {key.replace('_', ' ').title()}", "", markdown_value(value), ""])
    return "\n".join(lines).rstrip() + "\n"


def write_reports(data: dict[str, Any]) -> tuple[Path, Path]:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    stamp = dt.datetime.now().astimezone().strftime("%Y%m%d_%H%M%S")
    suffix = ""
    counter = 0
    while True:
        json_path = REPORTS_DIR / f"jetson_inventory_{stamp}{suffix}.json"
        markdown_path = REPORTS_DIR / f"jetson_inventory_{stamp}{suffix}.md"
        if not json_path.exists() and not markdown_path.exists():
            break
        counter += 1
        suffix = f"_{counter:02d}"
    safe_data = sanitize(data)
    json_path.write_text(json.dumps(safe_data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    markdown_path.write_text(render_markdown(safe_data), encoding="utf-8")
    return markdown_path, json_path


def main() -> int:
    try:
        markdown_path, json_path = write_reports(collect_inventory())
    except Exception as exc:
        print(f"Inventory failed safely: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    print("Inventory complete. No system configuration was changed.")
    print(f"Markdown report: {markdown_path.relative_to(PROJECT_ROOT)}")
    print(f"JSON report: {json_path.relative_to(PROJECT_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
