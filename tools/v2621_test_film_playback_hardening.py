from pathlib import Path
import sys

root = Path(__file__).resolve().parents[1]
workflow = (root / ".github/workflows/build-apk-v2591-hybrid-repair.yml").read_text(encoding="utf-8")
preflight = (root / "tools/v2613_preflight_repair_scripts.py").read_text(encoding="utf-8")
patch = (root / "tools/v2620_harden_film_playback.py").read_text(encoding="utf-8")\napp_screen = root / "app/lib/film_assembly_screen.dart"\nsource = app_screen.read_text(encoding="utf-8") if app_screen.exists() else ""

checks = {
    "workflow watches playback hardening patch": "tools/v2620_harden_film_playback.py" in workflow,
    "workflow runs playback patch after in-app player": workflow.find("python3 ../tools/v2619_add_in_app_film_playback.py") < workflow.find("python3 ../tools/v2620_harden_film_playback.py"),
    "preflight includes playback hardening patch": '"v2620_harden_film_playback.py"' in preflight,
    "restored saved films are decode-validated": "_isPlayableMp4(candidate)" in patch,
    "playback controller has a listener": "_controller.addListener(_onPlayerChanged)" in patch,
    "playback listener is removed on disposal": "_controller.removeListener(_onPlayerChanged)" in patch,
    "patch refuses unknown source blocks": "refusing unsafe patch" in patch,\n    "effective screen validates restored film bytes": "if (!await _isPlayableMp4(candidate)) outputPath = null;" in source,\n    "effective screen exposes playback action": "PLAY FINISHED FILM" in source,\n    "effective player refreshes controller state": "void _onPlayerChanged()" in source,
}
failed = [name for name, ok in checks.items() if not ok]
for name, ok in checks.items():
    print(("PASS: " if ok else "FAIL: ") + name)
if failed:
    print("Playback hardening regression failed:", *failed, sep="\n - ", file=sys.stderr)
    raise SystemExit(1)
print("Playback hardening regression passed.")
