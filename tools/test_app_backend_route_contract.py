#!/usr/bin/env python3
"""Keep Mark's AI Android scene polling and the shipped video backend routes in sync."""
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
app_patch = ROOT / "tools" / "v2605_download_generated_clips.py"
backend_routes = ROOT / "tools" / "video_generation_routes.js"
readiness_patch = ROOT / "tools" / "v2622_backend_readiness_preflight.py"
if not app_patch.is_file() or not backend_routes.is_file() or not readiness_patch.is_file():
    raise SystemExit("Missing app scene patch, readiness preflight, or backend route source")

app = app_patch.read_text(encoding="utf-8")
routes = backend_routes.read_text(encoding="utf-8")
readiness = readiness_patch.read_text(encoding="utf-8")
checks = [
    ("Android checks backend readiness before billable generation", "final healthUri = uri.replace(path: healthPath, query: null, fragment: null)", readiness),
    ("Android refuses generation when provider is not configured", "RUNWAYML_API_SECRET", readiness),
    ("Android requires the documented generation endpoint", "Enter the full backend URL ending in /api/video/generate", app),
    ("Android checks backend health before paid generation", "final healthUri = uri.replace(path: healthPath, query: null, fragment: null)", app),
    ("Android blocks generation when backend is not ready", "health['generationReady'] != true", app),
    ("Android submits to the generation route", "uri.path.endsWith('/api/video/generate')", app),
    ("backend exposes the matching generation route", "app.post('/api/video/generate'", routes),
    ("Android derives the status route from the generation URL", "uri.path.substring(0, uri.path.length - '/generate'.length) + '/status/'", app),
    ("backend exposes the matching task-status route", "app.get('/api/video/status/:taskId'", routes),
    ("task IDs are URL-encoded by Android", "Uri.encodeComponent(activeTask)", app),
    ("backend URL-encodes task IDs before requesting Runway", "encodeURIComponent(taskId)", routes),
    ("Android polls the same saved task rather than resubmitting", "final activeTask = task!", app),
    ("backend returns a task ID to the Android client", "taskId,", routes),
    ("backend returns normalized status and output", "status: task.status", routes),
    ("Android rejects success without a usable video URL", "Provider marked generation successful but returned no usable video URL", app),
]
failures = []
for label, marker, source in checks:
    if marker not in source:
        failures.append(label)
    else:
        print("PASS:", label)

# Prevent accidental route drift from the documented Hostinger setup.
readme = (ROOT / "backend" / "README.md").read_text(encoding="utf-8")
for route in ("/api/video/generate", "/api/video/status/:taskId", "/api/video/health"):
    if route not in readme:
        failures.append("Hostinger README documents " + route)
    else:
        print("PASS: Hostinger README documents " + route)

if failures:
    print("APP/BACKEND CONTRACT FAILED:", file=sys.stderr)
    for failure in failures:
        print(" - " + failure, file=sys.stderr)
    raise SystemExit(1)
print("PASS: Android/backend route contract is consistent.")
