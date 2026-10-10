#!/usr/bin/env python3
"""Fail the Android build early if the film-generation repair patches did not land."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1] / "app"
checks = {
    "scene generation/download recovery": (
        ROOT / "lib" / "scene_prompt_screen.dart",
        ["_pollAndDownload", "_downloadGeneratedClip", "localClipPath", "waiting_for_status", "jobId"],
    ),
    "scene/final-film playable MP4 validation": (
        ROOT / "lib" / "film_assembly_screen.dart",
        ["_isPlayableMp4", "FFmpegKit.execute", "finalFilmPath"],
    ),
    "film project local persistence": (
        ROOT / "lib" / "film_projects_screen.dart",
        ["offline://projects"],
    ),
    "gallery export dependency": (
        ROOT / "pubspec.yaml",
        ["gal:", "ffmpeg_kit_flutter_new_min:"],
    ),
}
failures = []
for label, (path, markers) in checks.items():
    if not path.is_file():
        failures.append(f"{label}: missing file {path.relative_to(ROOT)}")
        continue
    source = path.read_text(encoding="utf-8")
    missing = [marker for marker in markers if marker not in source]
    if missing:
        failures.append(f"{label}: missing expected markers: {', '.join(missing)}")
    else:
        print(f"PASS: {label}")

# The renderer must refuse to assemble scenes before checking local file content,
# and must validate the finished output rather than just trusting FFmpeg's return.
renderer = ROOT / "lib" / "film_assembly_screen.dart"
if renderer.is_file():
    source = renderer.read_text(encoding="utf-8")
    if "await _isPlayableMp4(File(path))" not in source:
        failures.append("renderer: per-scene decode validation is not wired into assembly")
    if "await _isPlayableMp4(out)" not in source:
        failures.append("renderer: final-film decode validation is not wired into export")
    if "Normalising clip formats and retrying assembly" not in source:
        failures.append("renderer: normalised assembly fallback is missing")

if failures:
    print("FILM PIPELINE VALIDATION FAILED:", file=sys.stderr)
    for failure in failures:
        print(" - " + failure, file=sys.stderr)
    raise SystemExit(1)
print("Film pipeline source validation passed.")
