#!/usr/bin/env python3
"""Regression checks for end-to-end scene-to-film navigation and billing confirmation."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
patch = (ROOT / "tools" / "v2623_connect_film_assembly.py").read_text(encoding="utf-8")
workflow = (ROOT / ".github" / "workflows" / "build-apk-v2591-hybrid-repair.yml").read_text(encoding="utf-8")
preflight = (ROOT / "tools" / "v2613_preflight_repair_scripts.py").read_text(encoding="utf-8")
gallery_patch = (ROOT / "tools" / "v2607_save_finished_film_to_gallery.py").read_text(encoding="utf-8")
pipeline_validator = (ROOT / "tools" / "v2612_validate_film_pipeline.py").read_text(encoding="utf-8")
scene_source = (ROOT / "app" / "lib" / "scene_prompt_screen.dart").read_text(encoding="utf-8")
assembly_source = (ROOT / "app" / "lib" / "film_assembly_screen.dart").read_text(encoding="utf-8")
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
if "Gal.putVideo(path, album: 'Marks AI Films')" not in gallery_patch:
    raise SystemExit("Finished-film gallery export patch is missing the actual gallery save call")
if "SAVE FILM TO PHONE GALLERY" not in gallery_patch:
    raise SystemExit("Finished-film gallery export button is missing")
if '"finished film export to phone gallery"' not in pipeline_validator:
    raise SystemExit("Film pipeline validator does not verify finished-film gallery export")

for marker in [
    "health['generationReady'] != true",
    "approvedPaidGeneration != true",
    "ASSEMBLE & PLAY FINISHED FILM",
    "FilmAssemblyScreen(projectId: widget.projectId)",
]:
    if marker not in scene_source:
        raise SystemExit("Built scene planner is missing required behavior: " + marker)

for marker in [
    "FFmpegKit.execute",
    "await _isPlayableMp4(out)",
    "PLAY FINISHED FILM",
    "Gal.putVideo(path, album: 'Marks AI Films')",
    "SAVE FILM TO PHONE GALLERY",
]:
    if marker not in assembly_source:
        raise SystemExit("Built film assembly screen is missing required behavior: " + marker)

print("PASS: generated app source contains backend readiness checks, paid-generation confirmation, assembly/playback and gallery export")
