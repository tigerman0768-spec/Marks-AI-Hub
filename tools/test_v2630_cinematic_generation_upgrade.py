#!/usr/bin/env python3
"""Regression tests for the v2630 cinematic AI generation upgrade."""
from pathlib import Path

root = Path(__file__).resolve().parents[1]
patch = (root / "tools" / "v2630_cinematic_generation_upgrade.py").read_text(encoding="utf-8")
workflow = (root / ".github" / "workflows" / "build-apk-v2591-hybrid-repair.yml").read_text(encoding="utf-8")

checks = [
    ("photorealistic live-action treatment exists", "photorealistic live-action cinema" in patch),
    ("animation requests keep an animation treatment", "premium cinematic animation" in patch),
    ("multiple camera setups are selected by scene number", "shotPlans[index % shotPlans.length]" in patch),
    ("continuity locks character and set details", "Maintain strict continuity with adjacent scenes" in patch),
    ("the AI backend receives the enhanced scene prompt", "'scene': requestScene, 'prompt': cinematicPrompt" in patch),
    ("offline preview is no longer labelled as full AI generation", "CREATE ILLUSTRATED PREVIEW (OFFLINE)" in patch),
    ("users can return directly to AI film generation", "RETURN TO REAL AI FILM GENERATION" in patch),
    ("the build workflow runs the upgrade patch", "v2630_cinematic_generation_upgrade.py" in workflow),
    ("the build workflow runs the regression test", "test_v2630_cinematic_generation_upgrade.py" in workflow),
]
failed = []
for label, passed in checks:
    print(("PASS" if passed else "FAIL") + ": " + label)
    if not passed:
        failed.append(label)
if failed:
    raise SystemExit("v2630 regression test failed: " + "; ".join(failed))
print("PASS: v2630 cinematic generation regression suite.")
