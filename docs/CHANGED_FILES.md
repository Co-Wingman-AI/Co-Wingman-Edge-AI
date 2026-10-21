# Initial product change inventory

This inventory describes the initial local product implementation from the prior checkout; later organization work is summarized in the root WORK_LOG.md.

All changes from the original `4cc1636` checkout through the integrated product.
The two historical generated reports were removed from tracking and left as
ignored local files; Git history was not rewritten. Renamed research documents
are archived and no longer provide operating instructions.

| Change | File |
| --- | --- |
| Updated | [.env.example](../.env.example) |
| Added | [.github/workflows/ci.yml](../.github/workflows/ci.yml) |
| Updated | [.gitignore](../.gitignore) |
| Updated | [README.md](../README.md) |
| Updated | [RUN_ON_JETSON.md](../RUN_ON_JETSON.md) |
| Added | [archive/README.md](../archive/README.md) |
| Moved | `docs/milestones/milestone1_step1.md` → [archive/docs/milestone1_step1.md](../archive/docs/milestone1_step1.md) |
| Moved | `docs/milestones/milestone1_step2.md` → [archive/docs/milestone1_step2.md](../archive/docs/milestone1_step2.md) |
| Moved | `docs/milestones/milestone1_step3.md` → [archive/docs/milestone1_step3.md](../archive/docs/milestone1_step3.md) |
| Moved | `scripts/nemotron_benchmark.py` → [archive/scripts/nemotron_benchmark.py](../archive/scripts/nemotron_benchmark.py) |
| Added | [cowingman/__main__.py](../cowingman/__main__.py) |
| Added | [cowingman/app.py](../cowingman/app.py) |
| Added | [cowingman/asr.py](../cowingman/asr.py) |
| Added | [cowingman/audio.py](../cowingman/audio.py) |
| Added | [cowingman/config.py](../cowingman/config.py) |
| Added | [cowingman/context.py](../cowingman/context.py) |
| Added | [cowingman/cue.py](../cowingman/cue.py) |
| Added | [cowingman/errors.py](../cowingman/errors.py) |
| Removed from current tree | `cowingman/hybrid_nemotron.py` |
| Added | [cowingman/pause.py](../cowingman/pause.py) |
| Added | [cowingman/provider.py](../cowingman/provider.py) |
| Added | [cowingman/speech.py](../cowingman/speech.py) |
| Added | [cowingman/tts.py](../cowingman/tts.py) |
| Added | [cowingman/ui.py](../cowingman/ui.py) |
| Added | [docs/HANDOFF.md](../docs/HANDOFF.md) |
| Added | [docs/PRESENTATION.md](../docs/PRESENTATION.md) |
| Added | [docs/PRIVACY.md](../docs/PRIVACY.md) |
| Added | [docs/SPEECH.md](../docs/SPEECH.md) |
| Added | [pyproject.toml](../pyproject.toml) |
| Removed from current tree | `reports/nemotron_benchmark_20261014_213647.json` |
| Removed from current tree | `reports/nemotron_benchmark_20261014_213647.md` |
| Added | [scripts/check_repository.py](../scripts/check_repository.py) |
| Removed from current tree | `scripts/hybrid_nemotron_benchmark.py` |
| Added | [scripts/navigator_benchmark.py](../scripts/navigator_benchmark.py) |
| Added | [scripts/prepare_speech_models.py](../scripts/prepare_speech_models.py) |
| Added | [tests/test_application.py](../tests/test_application.py) |
| Removed from current tree | `tests/test_hybrid_nemotron.py` |
| Updated | [tests/test_nemotron_benchmark.py](../tests/test_nemotron_benchmark.py) |
| Added | [tests/test_provider.py](../tests/test_provider.py) |
| Added | [tests/test_speech.py](../tests/test_speech.py) |
| Added | [tests/test_terminal.py](../tests/test_terminal.py) |
| Added | [docs/CHANGED_FILES.md](CHANGED_FILES.md) |
