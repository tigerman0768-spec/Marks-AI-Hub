#!/usr/bin/env python3
"""Regression guard for the Film Creator -> Local Video Studio navigation fix."""
from pathlib import Path
import re
import sys

generator = Path(__file__).resolve().parents[1] / "tools" / "v2600_add_local_video_studio.py"
source = generator.read_text(encoding="utf-8")
match = re.search(
    r"FilledButton\.icon\(\s*onPressed: saving \? null : \(\) \{(?P<body>.*?)\n\s*\},\s*icon: const Icon\(Icons\.movie_creation\)",
    source,
    flags=re.S,
)
if not match:
    raise SystemExit("FAIL: Local Video Studio button callback was not found or is not directly callable")
body = match.group("body")
if "Navigator.of(context).push(" not in body:
    raise SystemExit("FAIL: callback does not navigate to Local Video Studio")
if "await _save()" in body or "await Navigator.push" in body:
    raise SystemExit("FAIL: navigation is still blocked on asynchronous project saving")
if "LocalVideoStudioScreen(projectId: projectId)" not in body:
    raise SystemExit("FAIL: callback does not pass the existing project ID safely")
print("PASS: Local Video Studio navigation is direct and does not wait for project save")
