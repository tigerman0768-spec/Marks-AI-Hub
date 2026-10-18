#!/usr/bin/env python3
"""Verify the patched Film Creator checks backend readiness before scene generation."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
screen = ROOT / "app" / "lib" / "scene_prompt_screen.dart"
if not screen.is_file():
    raise SystemExit("Film Creator scene screen is missing after repair patches")

source = screen.read_text(encoding="utf-8")
required = [
    "final healthPath =",
    "final healthUri =",
    "health['generationReady'] != true",
    "Cannot reach the video backend health endpoint",
    "RUNWAYML_API_SECRET",
    "preflightClient.close(force: true)",
    "preflightClient.getUrl(healthUri)",
    "client.postUrl(uri)",
    "Uri.encodeComponent(activeTask)",
]
missing = [marker for marker in required if marker not in source]
if missing:
    raise SystemExit("Patched Film Creator is missing readiness/generation markers: " + ", ".join(missing))

health_index = source.index("final healthPath =")
saving_index = source.index("setState(() => saving = true);", health_index)
submit_index = source.index("client.postUrl(uri)")
loop_index = source.index("for (var i = 0; i < scenes.length; i++)", submit_index)
guard_index = source.index("health['generationReady'] != true")
if not health_index < guard_index < saving_index < loop_index:
    raise SystemExit("Backend readiness guard is not before the generation queue starts")
if guard_index > submit_index:
    raise SystemExit("Paid scene submission appears before the backend readiness guard")

print("PASS: patched Film Creator checks backend health/readiness before queueing generation.")
print("PASS: patched Film Creator retains generation, task polling, and task-ID encoding.")
