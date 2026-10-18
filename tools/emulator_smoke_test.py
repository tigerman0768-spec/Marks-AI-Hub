#!/usr/bin/env python3
"""Install and smoke-test Mark's AI on the already-booted Android emulator."""
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path.cwd()
OUT = ROOT / "app" / "build" / "install"
APK = OUT / "Mark_s_AI_v2604.apk"
SMOKE = OUT / "EMULATOR_SMOKE.txt"
LOG = OUT / "emulator-logcat.txt"

def run(args, *, check=True, capture=False):
    result = subprocess.run(args, text=True, stdout=subprocess.PIPE if capture else None,
                            stderr=subprocess.STDOUT if capture else None)
    if check and result.returncode:
        detail = result.stdout[-5000:] if capture and result.stdout else ""
        raise RuntimeError(f"Command failed ({result.returncode}): {' '.join(args)}\n{detail}")
    return result.stdout if capture else ""

def save_failure(message):
    SMOKE.write_text("status=failed; reason=" + message.replace("\n", " ") + "\n", encoding="utf-8")
    try:
        LOG.write_text(run(["adb", "logcat", "-d", "-t", "8000"], check=False, capture=True), encoding="utf-8")
    except Exception:
        pass

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    SMOKE.write_text("status=running\n", encoding="utf-8")
    if not APK.is_file() or APK.stat().st_size < 1_000_000:
        raise RuntimeError("Release APK is missing or implausibly small")
    run(["adb", "install", "-r", str(APK)])
    # A Flutter cold start can take longer than ActivityManager's default wait.
    run(["adb", "shell", "am", "start", "-n", "com.marksai.app/.MainActivity"])
    time.sleep(18)
    LOG.write_text(run(["adb", "logcat", "-d", "-t", "8000"], check=False, capture=True), encoding="utf-8")
    if not run(["adb", "shell", "pidof", "com.marksai.app"], check=False, capture=True).strip():
        raise RuntimeError("App process is not running after launch")
    log = LOG.read_text(encoding="utf-8", errors="replace")
    if "FATAL EXCEPTION" in log or "Process: com.marksai.app" in log:
        raise RuntimeError("Android crash signature detected after launch")
    run(["adb", "shell", "uiautomator", "dump", "/sdcard/marks-ai-ui.xml"])
    run(["adb", "pull", "/sdcard/marks-ai-ui.xml", str(OUT / "emulator-ui.xml")])
    run(["adb", "shell", "screencap", "-p", "/sdcard/marks-ai-home.png"])
    run(["adb", "pull", "/sdcard/marks-ai-home.png", str(OUT / "emulator-home-screen.png")])
    ui_path = OUT / "emulator-ui.xml"
    ui = ui_path.read_text(encoding="utf-8", errors="replace").lower()
    if not any(p in ui for p in ("create film", "film creator", "ai filmmaking studio", "filmmaking studio", "generate screenplay")):
        raise RuntimeError("Film-creation entry not found in accessible home UI")
    run([sys.executable, "tools/emulator_find_film_entry.py", str(ui_path), str(OUT / "create-film-tap.txt")])
    coords = {}
    for line in (OUT / "create-film-tap.txt").read_text().splitlines():
        key, value = line.split("=", 1)
        coords[key] = value
    before = OUT / "emulator-ui-before-film-tap.xml"
    before.write_text(ui_path.read_text(encoding="utf-8"), encoding="utf-8")
    run(["adb", "shell", "input", "tap", coords["x"], coords["y"]])
    time.sleep(10)
    run(["adb", "shell", "uiautomator", "dump", "/sdcard/marks-ai-film-ui.xml"])
    film_ui = OUT / "emulator-film-creator-ui.xml"
    run(["adb", "pull", "/sdcard/marks-ai-film-ui.xml", str(film_ui)])
    run(["adb", "shell", "screencap", "-p", "/sdcard/marks-ai-film-screen.png"])
    run(["adb", "pull", "/sdcard/marks-ai-film-screen.png", str(OUT / "emulator-film-creator-screen.png")])
    LOG.write_text(run(["adb", "logcat", "-d", "-t", "8000"], check=False, capture=True), encoding="utf-8")
    if not run(["adb", "shell", "pidof", "com.marksai.app"], check=False, capture=True).strip():
        raise RuntimeError("App process died after tapping film creation")
    log = LOG.read_text(encoding="utf-8", errors="replace")
    if "FATAL EXCEPTION" in log or "Process: com.marksai.app" in log:
        raise RuntimeError("Android crash signature detected after tapping film creation")
    if before.read_bytes() == film_ui.read_bytes():
        raise RuntimeError("Film-creation tap did not change accessible UI")
    SMOKE.write_text("status=passed; api=30; installed=true; launched=true; film_entry_visible=true; film_entry_tapped=true; screen_changed=true; process_alive=true; crash_signature=none\n", encoding="utf-8")
    print("PASS: APK installed, app launched, film entry tapped, UI changed, process stayed alive.")
    return 0

if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        save_failure(str(error))
        print("EMULATOR SMOKE TEST FAILED:", error, file=sys.stderr)
        raise SystemExit(1)
