#!/usr/bin/env python3
"""Regression checks for end-to-end scene-to-film navigation and billing confirmation."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
patch = (ROOT / "tools" / "v2623_connect_film_assembly.py").read_text(encoding="utf-8")
workflow = (ROOT / ".github" / "workflows" / "build-apk-v2591-hybrid-repair.yml").read_text(encoding="utf-8")
preflight = (ROOT / "tools" / "v2613_preflight_repair_scripts.py").read_text(encoding="utf-8")
required = [
    "import 'film_assembly_screen.dart';",
    "Generate AI video clips?",
    "separate video-generation requests",
    "approvedPaidGeneration != true",
    "ASSEMBLE & PLAY FINISHED FILM",
    "FilmAssemblyScreen(projectId: widget.projectId)",
    "scene['localClipPath']",
]
missing = [item for item in required if item not in patch]
if missing:
    raise SystemExit("Missing end-to-end film safeguards: " + ", ".join(missing))
if "Run repair v2623_connect_film_assembly.py" not in workflow:
    raise SystemExit("APK workflow does not apply the assembly navigation patch")
if "Test scene-to-film assembly navigation" not in workflow:
    raise SystemExit("APK workflow does not run the assembly navigation regression test")
if '"v2623_connect_film_assembly.py", "test_v2623_connect_film_assembly.py"' not in preflight:
    raise SystemExit("Patch preflight does not validate the assembly patch and test")
print("PASS: scene-to-film navigation and billable-generation confirmation are wired into CI")
