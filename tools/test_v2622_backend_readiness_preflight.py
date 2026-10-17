#!/usr/bin/env python3
"""Regression checks for the video backend readiness preflight."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
patch = (ROOT / "tools" / "v2622_backend_readiness_preflight.py").read_text(encoding="utf-8")
workflow = (ROOT / ".github" / "workflows" / "build-apk-v2591-hybrid-repair.yml").read_text(encoding="utf-8")
required = [
    "uri.path.substring(0, uri.path.length - '/generate'.length) + '/health'",
    "'/api/video/health'",
    "health['generationReady'] != true",
    "RUNWAYML_API_SECRET",
    "preflightClient.close(force: true)",
    "Cannot reach the video backend health endpoint",
]
missing = [item for item in required if item not in patch]
if missing:
    raise SystemExit("Missing readiness preflight safeguards: " + ", ".join(missing))
if "Run repair v2622_backend_readiness_preflight.py" not in workflow:
    raise SystemExit("APK workflow does not apply the backend readiness preflight")
if "Test backend readiness preflight" not in workflow:
    raise SystemExit("APK workflow does not run the readiness preflight regression test")
print("PASS: backend readiness preflight safeguards and CI wiring are present")
