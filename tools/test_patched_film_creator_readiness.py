#!/usr/bin/env python3
"""Verify the patched Film Creator checks backend readiness before scene generation."""
from pathlib import Path
import sys

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
    "final healthRequest = await preflightClient.getUrl(healthUri)",
    "final req = await client.postUrl(uri)",
    "final statusUri = uri.replace(path: statusPath, query: null, fragment: null)",
]
missing = [marker for marker in required if marker not in source]
if missing:
    raise SystemExit("Patched Film Creator is missing readiness/generation markers: " + ", ".join(missing))

health_index = source.index("final healthPath =")
submit_index = source.index("final req = await client.postUrl(uri)")
saving_index = source.index("setState(() => saving = true);", health_index)
loop_index = source.index("for (var i = 0; i < scenes.length; i++)", submit_index)
if not health_index < saving_index < loop_index:
    raise SystemExit("Backend readiness check is not before the generation queue starts")
if source.index("health['generationReady'] != true") > submit_index:
    raise SystemExit("Paid scene submission appears before the backend readiness guard")

print("PASS: patched Film Creator checks backend health/readiness before queueing generation.")
print("PASS: patched Film Creator retains generation, task polling, and status URL handling.")
