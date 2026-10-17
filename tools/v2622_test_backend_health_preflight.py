#!/usr/bin/env python3
"""Protect the Film Creator from billable submissions to an unready backend."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
patch = (ROOT / "tools" / "v2605_download_generated_clips.py").read_text(encoding="utf-8")
routes = (ROOT / "tools" / "video_generation_routes.js").read_text(encoding="utf-8")

checks = [
    ("app requires the configured generation endpoint", "uri.path.endsWith('/api/video/generate')"),
    ("app derives health URL from the same backend origin", "'/api/video/health'"),
    ("app checks readiness before starting the generation queue", "health['generationReady'] != true"),
    ("app surfaces backend readiness errors", "Video backend is not configured for generation."),
    ("health client has bounded request timeouts", "Duration(seconds: 15)" ),
    ("backend health reports generation readiness", "generationReady: configured"),
]
failures = []
for label, marker in checks[:5]:
    if marker not in patch:
        failures.append(label)
    else:
        print("PASS:", label)
if checks[5][1] not in routes:
    failures.append(checks[5][0])
else:
    print("PASS:", checks[5][0])

health_at = patch.find("health['generationReady'] != true")
submit_at = patch.find("final req = await client.postUrl(uri)")
if health_at < 0 or submit_at < 0 or health_at > submit_at:
    failures.append("readiness check must run before any billable POST /generate request")
else:
    print("PASS: readiness check precedes billable scene submission")

if failures:
    print("BACKEND HEALTH PREFLIGHT FAILED:", file=sys.stderr)
    for item in failures:
        print(" -", item, file=sys.stderr)
    raise SystemExit(1)
print("PASS: backend readiness preflight regression checks passed.")
