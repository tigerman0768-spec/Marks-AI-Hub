#!/usr/bin/env python3
"""Install and smoke-test Mark's AI on the already-booted Android emulator."""
from pathlib import Path
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

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
    # A cold CI emulator can report a transient package-service Broken pipe
    # even after boot_completed=1. Reconnect and retry installation instead of
    # failing the entire smoke test on the first adb/package-manager hiccup.
    install_error = None
    for attempt in range(1, 4):
        try:
            run(["adb", "wait-for-device"])
            run(["adb", "shell", "getprop", "sys.boot_completed"])
            run(["adb", "install", "-r", str(APK)])
            install_error = None
            break
        except Exception as error:
            install_error = error
            if attempt == 3:
                raise RuntimeError("APK installation failed after 3 attempts: " + str(error))
            print(f"APK install attempt {attempt} failed; restarting adb and retrying: {error}", file=sys.stderr)
            run(["adb", "kill-server"], check=False)
            time.sleep(3)
            run(["adb", "start-server"], check=False)
            time.sleep(8)
    if install_error is not None:
        raise RuntimeError("APK installation failed: " + str(install_error))
    # A Flutter cold start can take longer than ActivityManager's default wait.
    run(["adb", "shell", "am", "start", "-n", "com.marksai.app/.MainActivity"])
    time.sleep(18)
    LOG.write_text(run(["adb", "logcat", "-d", "-t", "8000"], check=False, capture=True), encoding="utf-8")
    if not run(["adb", "shell", "pidof", "com.marksai.app"], check=False, capture=True).strip():
        raise RuntimeError("App process is not running after launch")
    log = LOG.read_text(encoding="utf-8", errors="replace")
    if "FATAL EXCEPTION" in log or "Process: com.marksai.app" in log:
        raise RuntimeError("Android crash signature detected after launch")
    # The Android 16 CI emulator has intermittently displayed its own
    # "Process system isn't responding" dialog over the app during first boot.
    # That overlay hid the app from uiautomator and caused a false failure.
    # Dismiss it with Wait, then re-capture the UI while Flutter finishes loading.
    ui_path = OUT / "emulator-ui.xml"
    film_phrases = ("create film", "film creator", "ai filmmaking studio", "filmmaking studio", "generate screenplay")
    ui = ""
    last_labels = []
    for attempt in range(1, 10):
        run(["adb", "shell", "uiautomator", "dump", "/sdcard/marks-ai-ui.xml"], check=False)
        run(["adb", "pull", "/sdcard/marks-ai-ui.xml", str(ui_path)], check=False)
        if ui_path.exists():
            ui = ui_path.read_text(encoding="utf-8", errors="replace").lower()
            try:
                root = ET.parse(ui_path).getroot()
                last_labels = [
                    (node.attrib.get("text", "") + " " + node.attrib.get("content-desc", "")).strip()
                    for node in root.iter()
                    if (node.attrib.get("text", "").strip() or node.attrib.get("content-desc", "").strip())
                ]
                # If the system's ANR overlay is covering the app, choose Wait
                # instead of Close app and give the emulator time to recover.
                if "process system isn't responding" in ui:
                    wait_node = next(
                        (node for node in root.iter() if node.attrib.get("text", "").strip().lower() == "wait"),
                        None,
                    )
                    if wait_node is not None:
                        import re
                        bounds = re.fullmatch(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", wait_node.attrib.get("bounds", ""))
                        if bounds:
                            x1, y1, x2, y2 = map(int, bounds.groups())
                            run(["adb", "shell", "input", "tap", str((x1+x2)//2), str((y1+y2)//2)], check=False)
                    time.sleep(8)
                    continue
                if any(p in ui for p in film_phrases):
                    break
            except ET.ParseError:
                pass
        time.sleep(8)
    run(["adb", "shell", "screencap", "-p", "/sdcard/marks-ai-home.png"])
    run(["adb", "pull", "/sdcard/marks-ai-home.png", str(OUT / "emulator-home-screen.png")])
    ui = ui_path.read_text(encoding="utf-8", errors="replace").lower() if ui_path.exists() else ""
    if not any(p in ui for p in film_phrases):
        raise RuntimeError("Film-creation entry not found after emulator UI recovery; last accessible labels: " + " | ".join(last_labels[:35]))
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
