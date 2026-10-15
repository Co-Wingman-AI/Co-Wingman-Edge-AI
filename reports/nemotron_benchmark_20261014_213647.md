# NVIDIA Nemotron isolated benchmark

Generated: 2026-10-14T21:34:31-04:00

- Jetson verified: **yes**
- Model: `nvidia/NVIDIA-Nemotron-3-Nano-4B-GGUF:Q4_K_M`
- Context size: 2048
- Server load time: 45.223 seconds
- Isolated benchmark passed: **no**
- Minimum available RAM: 293.79 MiB
- Maximum server RSS: 4.47 GiB
- Swap growth: 361.00 MiB

> An isolated pass is not proof that the complete concurrent speech pipeline is feasible.

## Measured trials

| Trial | Success | Valid JSON | First content (s) | Total (s) | Output tok/s |
|---:|:---:|:---:|---:|---:|---:|
| 1 | yes | yes | 1.065 | 24.977 | 6.691 |
| 2 | yes | yes | 1.206 | 25.544 | 6.574 |
| 3 | yes | yes | 1.508 | 18.9 | 6.497 |

## Assessment

```json
{
  "isolated_benchmark_passed": false,
  "all_requests_succeeded": true,
  "all_json_outputs_valid": true,
  "swap_growth_within_256_mib": false,
  "at_least_1_gib_ram_headroom": false,
  "next_gate": "Review failures or resource pressure before adding any concurrent model.",
  "warning": "An isolated pass does not prove that the complete Co-Wingman pipeline fits or meets latency targets."
}
```

## Resource summary

```json
{
  "system": {
    "sample_count": 264,
    "minimum_available_ram_bytes": 308060160,
    "maximum_server_rss_bytes": 4794400768,
    "initial_swap_used_bytes": 9437184,
    "maximum_swap_used_bytes": 387973120,
    "swap_growth_bytes": 378535936,
    "maximum_sysfs_temperature_c": 54.937
  },
  "tegrastats": {
    "available": true,
    "sample_count": 131,
    "max_gpu_utilization_percent": 99,
    "max_temperature_c": 54.75,
    "max_input_power_mw": 10973,
    "last_samples": [
      "10-14-2026 21:36:34 RAM 6887/7620MB (lfb 1x512kB) SWAP 369/3810MB (cached 0MB) CPU [57%@883,52%@883,56%@883,54%@883,53%@883,53%@883] GR3D_FREQ 2% cpu@53.656C soc2@51.812C soc0@53.406C gpu@53.781C tj@53.781C soc1@51.937C VDD_IN 8544mW/7268mW VDD_CPU_GPU_CV 3095mW/2367mW VDD_SOC 2066mW/1842mW",
      "10-14-2026 21:36:35 RAM 6887/7620MB (lfb 1x512kB) SWAP 369/3810MB (cached 0MB) CPU [57%@1190,52%@1190,50%@1190,50%@1190,57%@1190,57%@1190] GR3D_FREQ 5% cpu@53.937C soc2@51.843C soc0@53.437C gpu@53.843C tj@53.937C soc1@52C VDD_IN 8425mW/7277mW VDD_CPU_GPU_CV 3095mW/2372mW VDD_SOC 2026mW/1844mW",
      "10-14-2026 21:36:36 RAM 6882/7620MB (lfb 1x512kB) SWAP 369/3810MB (cached 0MB) CPU [53%@729,53%@729,46%@729,51%@729,53%@729,51%@729] GR3D_FREQ 99% cpu@53.468C soc2@51.812C soc0@53.468C gpu@54.406C tj@54.406C soc1@52.093C VDD_IN 9180mW/7292mW VDD_CPU_GPU_CV 3367mW/2380mW VDD_SOC 2301mW/1848mW",
      "10-14-2026 21:36:37 RAM 6882/7620MB (lfb 1x512kB) SWAP 369/3810MB (cached 0MB) CPU [56%@806,54%@806,57%@806,56%@806,56%@729,56%@729] GR3D_FREQ 1% cpu@53.906C soc2@51.906C soc0@53.468C gpu@53.937C tj@53.937C soc1@52.156C VDD_IN 8982mW/7306mW VDD_CPU_GPU_CV 3169mW/2387mW VDD_SOC 2301mW/1851mW",
      "10-14-2026 21:36:38 RAM 6882/7620MB (lfb 1x512kB) SWAP 369/3810MB (cached 0MB) CPU [60%@806,56%@806,58%@806,58%@806,59%@729,57%@729] GR3D_FREQ 1% cpu@54.093C soc2@52.062C soc0@53.593C gpu@54.187C tj@54.312C soc1@52.062C VDD_IN 9761mW/7325mW VDD_CPU_GPU_CV 3599mW/2396mW VDD_SOC 2539mW/1857mW",
      "10-14-2026 21:36:39 RAM 6882/7620MB (lfb 1x512kB) SWAP 369/3810MB (cached 0MB) CPU [60%@883,60%@883,57%@883,58%@883,58%@806,58%@806] GR3D_FREQ 4% cpu@54.125C soc2@51.968C soc0@53.593C gpu@54.375C tj@54.375C soc1@52.156C VDD_IN 9761mW/7345mW VDD_CPU_GPU_CV 3638mW/2406mW VDD_SOC 2539mW/1862mW",
      "10-14-2026 21:36:40 RAM 6882/7620MB (lfb 1x512kB) SWAP 369/3810MB (cached 0MB) CPU [60%@729,56%@729,60%@729,44%@729,59%@806,59%@806] GR3D_FREQ 72% cpu@53.875C soc2@52.156C soc0@53.687C gpu@54.75C tj@54.75C soc1@52.156C VDD_IN 9483mW/7361mW VDD_CPU_GPU_CV 3565mW/2415mW VDD_SOC 2420mW/1866mW",
      "10-14-2026 21:36:41 RAM 6882/7620MB (lfb 1x512kB) SWAP 369/3810MB (cached 0MB) CPU [60%@806,57%@806,58%@806,45%@806,58%@729,59%@729] GR3D_FREQ 4% cpu@54.062C soc2@52.093C soc0@53.625C gpu@54.437C tj@54.437C soc1@52.343C VDD_IN 9339mW/7377mW VDD_CPU_GPU_CV 3605mW/2424mW VDD_SOC 2261mW/1869mW",
      "10-14-2026 21:36:42 RAM 6882/7620MB (lfb 1x512kB) SWAP 369/3810MB (cached 0MB) CPU [60%@883,60%@883,59%@883,60%@883,60%@883,58%@883] GR3D_FREQ 3% cpu@54.531C soc2@52.343C soc0@53.781C gpu@54.437C tj@54.531C soc1@52.281C VDD_IN 10039mW/7397mW VDD_CPU_GPU_CV 3678mW/2434mW VDD_SOC 2733mW/1876mW",
      "10-14-2026 21:36:43 RAM 6882/7620MB (lfb 1x512kB) SWAP 369/3810MB (cached 0MB) CPU [59%@883,60%@883,58%@883,59%@883,59%@806,59%@806] GR3D_FREQ 2% cpu@54.5C soc2@52.187C soc0@53.718C gpu@54.468C tj@54.5C soc1@52.312C VDD_IN 9642mW/7414mW VDD_CPU_GPU_CV 3480mW/2442mW VDD_SOC 2579mW/1881mW"
    ]
  }
}
```

## Outputs

### Trial 1

```json
{
  "valid": true,
  "errors": [],
  "parsed": {
    "cue": "Which part of the project should we test first?",
    "intent": "resume",
    "should_offer": true
  }
}
```

### Trial 2

```json
{
  "valid": true,
  "errors": [],
  "parsed": {
    "cue": "Sure, I'll explain the local measurement requirement.",
    "intent": "respond",
    "should_offer": true
  }
}
```

### Trial 3

```json
{
  "valid": true,
  "errors": [],
  "parsed": {
    "cue": "Help me explain differences between JSON and Markdown",
    "intent": "clarify",
    "should_offer": true
  }
}
```
