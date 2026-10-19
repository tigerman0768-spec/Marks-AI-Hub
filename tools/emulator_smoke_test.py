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

def run(args, *, check=True, capture=False, timeout=45):
    try:
        result = subprocess.run(args, text=True, stdout=subprocess.PIPE if capture else None,
                                stderr=subprocess.STDOUT if capture else None, timeout=timeout)
    except subprocess.TimeoutExpired as error:
        detail = error.stdout or ""
        if isinstance(detail, bytes):
            detail = detail.decode("utf-8", errors="replace")
        if check:
            raise RuntimeError(f"Command timed out after {timeout}s: {' '.join(args)}\n{detail[-5000:]}")
        return detail
    if check and result.returncode:
        detail = result.stdout[-5000:] if capture and result.stdout else ""
        raise RuntimeError(f"Command failed ({result.returncode}): {' '.join(args)}\n{detail}")
    return result.stdout if capture else ""

def mark_phase(phase):
    """Persist the last smoke-test phase so runner timeouts are diagnosable."""
    SMOKE.write_text("status=running; phase=" + phase + "\n", encoding="utf-8")
    try:
        snapshot = run(["adb", "logcat", "-d", "-t", "2000"], check=False, capture=True, timeout=8)
        LOG.write_text(snapshot, encoding="utf-8")
    except Exception as error:
        (OUT / "emulator-phase-debug.txt").write_text(phase + ": logcat snapshot failed: " + str(error), encoding="utf-8")

def save_failure(message):
    SMOKE.write_text("status=failed; reason=" + message.replace("\n", " ") + "\n", encoding="utf-8")
    try:
        LOG.write_text(run(["adb", "logcat", "-d", "-t", "8000"], check=False, capture=True), encoding="utf-8")
    except Exception:
        pass

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    mark_phase("script_started")
    if not APK.is_file() or APK.stat().st_size < 1_000_000:
        raise RuntimeError("Release APK is missing or implausibly small")
    # Wait until the emulator is genuinely online, not merely listed by adb.
    # The previous smoke test began install while adb reported "device offline";
    # retrying adb install repeatedly consumed the entire runner timeout.
    serial = "emulator-5554"
    deadline = time.monotonic() + 120
    online = False
    last_state = "unknown"
    while time.monotonic() < deadline:
        state = run(["adb", "devices"], check=False, capture=True, timeout=10)
        last_state = next((line.split()[-1] for line in state.splitlines()
                           if line.startswith(serial + "\\t")), "missing")
        if last_state == "device":
            boot = run(["adb", "-s", serial, "shell", "getprop", "sys.boot_completed"],
                       check=False, capture=True, timeout=15).strip()
            if boot == "1":
                online = True
                break
        time.sleep(3)
    if not online:
        raise RuntimeError("Emulator did not become online and boot-complete within 120s; adb state=" + last_state)
    # The APK is over 100 MB. Disable adb streaming install, which stalled in
    # the previous run, and bound the package transfer to 150 seconds.
    run(["adb", "-s", serial, "install", "--no-streaming", "-r", str(APK)], timeout=150)
    mark_phase("starting_activity")
    # A Flutter cold start can take longer than ActivityManager's default wait.
    run(["adb", "shell", "am", "start", "-n", "com.marksai.app/.MainActivity"], timeout=25)
    mark_phase("activity_started; waiting_for_flutter")
    time.sleep(10)
    mark_phase("checking_process")
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
    mark_phase("process_alive; starting_ui_dump")
    ui_path = OUT / "emulator-ui.xml"
    film_phrases = ("create film", "film creator", "ai filmmaking studio", "filmmaking studio", "generate screenplay")
    ui = ""
    last_labels = []
    # Bound each UI dump: Android 16 CI images have occasionally hung
    # uiautomator behind a system ANR dialog. A smoke test should collect
    # evidence and fail with a useful reason, not consume the entire job.
    for attempt in range(1, 3):
        mark_phase("ui_dump_attempt_" + str(attempt))
        run(["adb", "shell", "uiautomator", "dump", "/sdcard/marks-ai-ui.xml"],
            check=False, timeout=12)
        run(["adb", "pull", "/sdcard/marks-ai-ui.xml", str(ui_path)],
            check=False, timeout=12)
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
                if ("process system isn't responding" in ui or "system ui isn't responding" in ui or "system ui is not responding" in ui):
                    wait_node = next(
                        (node for node in root.iter() if node.attrib.get("text", "").strip().lower() == "wait"),
                        None,
                    )
                    if wait_node is not None:
                        import re
                        bounds = re.fullmatch(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", wait_node.attrib.get("bounds", ""))
                        if bounds:
                            x1, y1, x2, y2 = map(int, bounds.groups())
                            run(["adb", "shell", "input", "tap", str((x1+x2)//2), str((y1+y2)//2)], check=False, timeout=15)
                    time.sleep(3)
                    continue
                if any(p in ui for p in film_phrases):
                    break
            except ET.ParseError:
                pass
        time.sleep(3)
    mark_phase("ui_dump_finished; capturing_home_screen")
    run(["adb", "shell", "screencap", "-p", "/sdcard/marks-ai-home.png"], timeout=15)
    run(["adb", "pull", "/sdcard/marks-ai-home.png", str(OUT / "emulator-home-screen.png")], timeout=20)
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
    mark_phase("film_entry_found; tapping")
    run(["adb", "shell", "input", "tap", coords["x"], coords["y"]], timeout=15)
    time.sleep(5)
    mark_phase("film_entry_tapped; verifying_screen")
    run(["adb", "shell", "uiautomator", "dump", "/sdcard/marks-ai-film-ui.xml"], timeout=15)
    film_ui = OUT / "emulator-film-creator-ui.xml"
    run(["adb", "pull", "/sdcard/marks-ai-film-ui.xml", str(film_ui)], timeout=20)
    run(["adb", "shell", "screencap", "-p", "/sdcard/marks-ai-film-screen.png"], timeout=20)
    run(["adb", "pull", "/sdcard/marks-ai-film-screen.png", str(OUT / "emulator-film-creator-screen.png")], timeout=20)
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
