#!/usr/bin/env python3
"""Fail the hybrid APK build if core film screens are replaced by placeholders."""
from pathlib import Path
import re
import sys

root = Path(__file__).resolve().parents[1]
workflow_path = root / ".github" / "workflows" / "build-apk-v2591-hybrid-repair.yml"
workflow = workflow_path.read_text(encoding="utf-8")

match = re.search(r"broken\s*=\s*\[(.*?)\n\s*\]", workflow, re.S)
if not match:
    raise SystemExit("FAIL: could not inspect the repair workflow's placeholder replacement list")

replaced = set(re.findall(r"""["']([a-z0-9_]+\.dart)["']""", match.group(1)))
core_screens = {
    "film_library_screen.dart": "Film Library",
    "ai_film_assembler_screen.dart": "Film Assembly",
    "recent_films_screen.dart": "Recent Films",
    "generated_clip_review_summary_screen.dart": "Generated Clip Review",
    "shot_cards_screen.dart": "Shot Cards",
}
lost = [(filename, label) for filename, label in core_screens.items() if filename in replaced]
if lost:
    print("FAIL: the APK workflow replaces core app screens with generic placeholders:")
    for filename, label in lost:
        print(f" - {label}: app/lib/{filename}")
    print("Do not publish this APK as feature-complete. Restore the real screens and rerun the build.")
    sys.exit(1)

print("PASS: no core film-library, assembly, clip-review or shot-card screen is in the placeholder replacement list.")
