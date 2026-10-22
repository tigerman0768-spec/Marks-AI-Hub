#!/usr/bin/env python3
"""Install and smoke-test Mark's AI on the already-booted Android emulator."""
from pathlib import Path
import re
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

ROOT = Path.cwd()
OUT = ROOT / "app" / "build" / "install"
# Prefer the smaller x86_64 build for emulator smoke tests; the separately
# packaged universal APK remains the one intended for normal Android phones.
APK = OUT / "Mark_s_AI_v2604_emulator_x64.apk"
if not APK.is_file():
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
                           if line.startswith(serial + "\t")), "missing")
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
    # previous runs. Android's package service has also intermittently died with
    # a broken pipe during transfer. Retry with a fresh adb server and verify the
    # emulator is online before each attempt; do not treat a failed install as a pass.
    install_error = None
    for install_attempt in range(1, 4):
        mark_phase("install_attempt_" + str(install_attempt))
        state = run(["adb", "devices"], check=False, capture=True, timeout=10)
        current = next((line.split()[-1] for line in state.splitlines()
                        if line.startswith(serial + "\t")), "missing")
        if current != "device":
            run(["adb", "start-server"], check=False, timeout=15)
            time.sleep(5)
        try:
            run(["adb", "-s", serial, "install", "--no-streaming", "-r", str(APK)],
                timeout=360)
            install_error = None
            break
        except Exception as error:
            install_error = error
            (OUT / "emulator-install-retry.txt").write_text(
                "attempt=" + str(install_attempt) + "\nerror=" + str(error) + "\n",
                encoding="utf-8")
            if install_attempt < 3:
                # Restart adb transport, then wait for the already-booted device.
                run(["adb", "kill-server"], check=False, timeout=15)
                time.sleep(3)
                run(["adb", "start-server"], check=False, timeout=15)
                reconnect_deadline = time.monotonic() + 60
                while time.monotonic() < reconnect_deadline:
                    devices = run(["adb", "devices"], check=False, capture=True, timeout=10)
                    device_state = next((line.split()[-1] for line in devices.splitlines()
                                         if line.startswith(serial + "\t")), "missing")
                    if device_state == "device":
                        boot = run(["adb", "-s", serial, "shell", "getprop", "sys.boot_completed"],
                                   check=False, capture=True, timeout=15).strip()
                        if boot == "1":
                            break
                    time.sleep(3)
    if install_error is not None:
        raise RuntimeError("APK install failed after 3 attempts: " + str(install_error))
    mark_phase("starting_activity")
    # A Flutter cold start can take longer than ActivityManager's default wait.
    run(["adb", "shell", "am", "start", "-n", "com.marksai.app/.MainActivity"], timeout=25)
    mark_phase("activity_started; waiting_for_flutter")
    time.sleep(25)
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
    for attempt in range(1, 9):
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
                if ("isn't responding" in ui or "is not responding" in ui):
                    wait_node = next(
                        (node for node in root.iter() if node.attrib.get("text", "").strip().lower() == "wait"),
                        None,
                    )
                    if wait_node is not None:
                        bounds = re.fullmatch(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", wait_node.attrib.get("bounds", ""))
                        if bounds:
                            x1, y1, x2, y2 = map(int, bounds.groups())
                            run(["adb", "shell", "input", "tap", str((x1+x2)//2), str((y1+y2)//2)], check=False, timeout=15)
                    time.sleep(8)
                    if not run(["adb", "shell", "pidof", "com.marksai.app"], check=False, capture=True).strip():
                        raise RuntimeError("App process died while recovering from Android system ANR overlay")
                    continue
                if any(p in ui for p in film_phrases):
                    break
            except ET.ParseError:
                pass
        time.sleep(5)
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

    # Exercise the offline renderer, not just the navigation. The default
    # four-second clip is deliberately short so CI can validate a real MP4.
    mark_phase("film_creator_open; locating_local_video_button")
    film_text = film_ui.read_text(encoding="utf-8", errors="replace")
    # The Film Creator layout can extend below the first viewport on smaller
    # emulator screens. Search the current UI, then scroll down in controlled
    # increments before declaring the Local Video Studio entry missing.
    local_button = None
    for scroll_attempt in range(5):
        try:
            current_root = ET.parse(film_ui).getroot()
            # Flutter accessibility can put the label on a parent View that
            # spans the whole section. Tap the actual clickable Android Button,
            # not the first ancestor whose description happens to contain it.
            local_candidates = [
                node for node in current_root.iter()
                if node.attrib.get("class") == "android.widget.Button"
                and node.attrib.get("clickable") == "true"
                and any(phrase in (node.attrib.get("text", "") + " " + node.attrib.get("content-desc", "")).upper()
                        for phrase in ("MAKE A LOCAL TEST VIDEO", "CREATE VIDEO LOCALLY", "LOCAL VIDEO STUDIO"))
            ]
            local_button = local_candidates[0] if local_candidates else None
        except (ET.ParseError, OSError):
            local_button = None
        if local_button is not None:
            break
        if scroll_attempt < 4:
            # Derive swipe coordinates from the actual emulator resolution.
            # Fixed 540/1450 coordinates can miss the scrollable area on
            # smaller CI displays, leaving the same first viewport in XML.
            size_text = run(["adb", "shell", "wm", "size"], check=False, capture=True, timeout=10)
            match = re.search(r"(?:Physical|Override) size:\s*(\d+)x(\d+)", size_text)
            if match:
                screen_w, screen_h = map(int, match.groups())
            else:
                screen_w, screen_h = 1080, 1920
            sx = screen_w // 2
            sy1 = int(screen_h * 0.82)
            sy2 = int(screen_h * 0.30)
            run(["adb", "shell", "input", "swipe", str(sx), str(sy1), str(sx), str(sy2), "700"], check=False, timeout=15)
            time.sleep(2)
            dump_result = run(["adb", "shell", "uiautomator", "dump", "/sdcard/marks-ai-film-ui.xml"], check=False, capture=True, timeout=15)
            pull_result = run(["adb", "pull", "/sdcard/marks-ai-film-ui.xml", str(film_ui)], check=False, capture=True, timeout=15)
            (OUT / "emulator-film-scroll-debug.txt").write_text(
                f"attempt={scroll_attempt + 1}; resolution={screen_w}x{screen_h}\\n"
                f"dump={dump_result[-1000:]}\\npull={pull_result[-1000:]}\\n",
                encoding="utf-8",
            )
    if local_button is None:
        labels = []
        try:
            labels = [
                (n.attrib.get("text", "") + " " + n.attrib.get("content-desc", "")).strip()
                for n in ET.parse(film_ui).getroot().iter()
                if n.attrib.get("text", "").strip() or n.attrib.get("content-desc", "").strip()
            ]
        except (ET.ParseError, OSError):
            pass
        raise RuntimeError("Local Video Studio button was not visible after scrolling Film Creator; labels: " + " | ".join(labels[:50]))
    local_bounds = re.fullmatch(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", local_button.attrib.get("bounds", ""))
    if not local_bounds:
        raise RuntimeError("Local Video Studio button had no usable screen bounds")
    x1, y1, x2, y2 = map(int, local_bounds.groups())
    studio_xml = OUT / "emulator-local-video-studio-ui.xml"
    def capture_studio_ui():
        run(["adb", "shell", "uiautomator", "dump", "/sdcard/marks-ai-studio-ui.xml"], check=False, timeout=12)
        run(["adb", "pull", "/sdcard/marks-ai-studio-ui.xml", str(studio_xml)], check=False, timeout=12)
        return studio_xml.read_text(encoding="utf-8", errors="replace") if studio_xml.exists() else ""

    # Retry the actual navigation and retain every UI snapshot. A single
    # immediate accessibility dump can capture the old Flutter route on a cold
    # emulator, which previously made a real navigation delay look like a dead button.
    studio_text = ""
    prompt_node = None
    for nav_attempt in range(1, 5):
        mark_phase("local_video_studio_navigation_attempt_" + str(nav_attempt))
        run(["adb", "shell", "input", "tap", str((x1+x2)//2), str((y1+y2)//2)], check=False, timeout=15)
        for wait_attempt in range(1, 5):
            time.sleep(2)
            studio_text = capture_studio_ui()
            (OUT / ("emulator-studio-navigation-attempt-" + str(nav_attempt) + ".xml")).write_text(
                studio_text, encoding="utf-8")
            try:
                studio_root = ET.parse(studio_xml).getroot() if studio_xml.exists() else None
            except ET.ParseError:
                studio_root = None
            if studio_root is not None:
                prompt_node = next((node for node in studio_root.iter()
                                    if "Describe your video" in (node.attrib.get("text", "") + " " + node.attrib.get("content-desc", ""))), None)
            if prompt_node is not None:
                break
        if prompt_node is not None:
            break
        # Refresh the target's bounds from the latest screen before retrying.
        try:
            fresh_root = ET.parse(studio_xml).getroot()
            fresh_button = next((node for node in fresh_root.iter()
                                 if node.attrib.get("class") == "android.widget.Button"
                                 and node.attrib.get("clickable") == "true"
                                 and "CREATE VIDEO LOCALLY" in
                                 (node.attrib.get("text", "") + " " + node.attrib.get("content-desc", "")).upper()), None)
            fresh_bounds = re.fullmatch(r"\\[(\\d+),(\\d+)\\]\\[(\\d+),(\\d+)\\]", fresh_button.attrib.get("bounds", "")) if fresh_button is not None else None
            if fresh_bounds:
                x1, y1, x2, y2 = map(int, fresh_bounds.groups())
        except (ET.ParseError, OSError):
            pass

    mark_phase("local_video_studio_open; setting_short_test_prompt")
    if prompt_node is None:
        labels = []
        try:
            labels = [(n.attrib.get("text", "") + " " + n.attrib.get("content-desc", "")).strip()
                      for n in ET.parse(studio_xml).getroot().iter()
                      if n.attrib.get("text", "").strip() or n.attrib.get("content-desc", "").strip()]
        except (ET.ParseError, OSError):
            pass
        raise RuntimeError("Local Video Studio prompt field was not accessible after 4 navigation attempts; last labels: " + " | ".join(labels[:45]))
    prompt_bounds = re.fullmatch(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", prompt_node.attrib.get("bounds", ""))
    if not prompt_bounds:
        raise RuntimeError("Local Video Studio prompt field had no usable bounds")
    x1, y1, x2, y2 = map(int, prompt_bounds.groups())
    run(["adb", "shell", "input", "tap", str((x1+x2)//2), str((y1+y2)//2)], timeout=15)
    run(["adb", "shell", "input", "keyevent", "KEYCODE_CTRL_A"], check=False, timeout=10)
    run(["adb", "shell", "input", "text", "A%swalking%shis%sdog%sthrough%sa%speaceful%sforest"], timeout=15)
    size_text = run(["adb", "shell", "wm", "size"], check=False, capture=True, timeout=10)
    size_match = re.search(r"(?:Physical|Override) size:\s*(\d+)x(\d+)", size_text)
    screen_w, screen_h = map(int, size_match.groups()) if size_match else (1080, 1920)
    # Do not send KEYCODE_BACK here: if the keyboard failed to open, Android
    # pops Local Video Studio and the test then searches the wrong screen.
    # Tapping the safe centre of the app bar dismisses the keyboard without
    # navigating away from the studio.
    run(["adb", "shell", "input", "tap", str(screen_w // 2), str(max(40, int(screen_h * 0.045)))], check=False, timeout=10)
    time.sleep(1)
    studio_text = capture_studio_ui()
    studio_root = ET.parse(studio_xml).getroot() if studio_xml.exists() else None
    generate_node = None
    # Local Video Studio's prompt and render controls can be below the visible
    # viewport on Android 16. Scroll its own page before declaring the button missing.
    for studio_scroll in range(6):
        if studio_root is not None:
            # Flutter semantics can expose a large parent with the same label.
            # Select the actual clickable button with the smallest bounds so
            # the tap lands on the control rather than an empty parent area.
            candidates = []
            for node in studio_root.iter():
                label = (node.attrib.get("text", "") + " " + node.attrib.get("content-desc", "")).upper()
                if (node.attrib.get("clickable") == "true"
                        and node.attrib.get("class", "").lower().endswith("button")
                        and "GENERATE VIDEO" in label):
                    bounds = re.fullmatch(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", node.attrib.get("bounds", ""))
                    if bounds:
                        x1, y1, x2, y2 = map(int, bounds.groups())
                        candidates.append((max(1, x2-x1) * max(1, y2-y1), node))
            generate_node = min(candidates, key=lambda item: item[0])[1] if candidates else None
        if generate_node is not None:
            break
        if studio_scroll < 5:
            size_text = run(["adb", "shell", "wm", "size"], check=False, capture=True, timeout=10)
            match = re.search(r"(?:Physical|Override) size:\s*(\d+)x(\d+)", size_text)
            screen_w, screen_h = map(int, match.groups()) if match else (1080, 1920)
            run(["adb", "shell", "input", "swipe", str(screen_w // 2), str(int(screen_h * 0.82)),
                 str(screen_w // 2), str(int(screen_h * 0.30)), "650"], check=False, timeout=15)
            time.sleep(2)
            studio_text = capture_studio_ui()
            try:
                studio_root = ET.parse(studio_xml).getroot() if studio_xml.exists() else None
            except ET.ParseError:
                studio_root = None
    if generate_node is None:
        raise RuntimeError("GENERATE VIDEO button was not accessible in Local Video Studio after scrolling; labels: " +
                           " | ".join((n.attrib.get("text", "") + " " + n.attrib.get("content-desc", "")).strip()
                                      for n in studio_root.iter() if n.attrib.get("text", "").strip() or n.attrib.get("content-desc", "").strip())[:1200]
                           if studio_root is not None else "no accessible UI tree")
    generate_bounds = re.fullmatch(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", generate_node.attrib.get("bounds", ""))
    if not generate_bounds:
        raise RuntimeError("GENERATE VIDEO button had no usable bounds")
    x1, y1, x2, y2 = map(int, generate_bounds.groups())
    tap_x, tap_y = (x1+x2)//2, (y1+y2)//2
    mark_phase("local_video_generate_tap_attempt; x=" + str(tap_x) + "; y=" + str(tap_y))
    run(["adb", "shell", "input", "tap", str(tap_x), str(tap_y)], timeout=15)
    time.sleep(3)
    first_ui = capture_studio_ui().lower()
    # On some Android 16 emulator boots, a Flutter semantics node has stale
    # bounds after scrolling. Re-find the current visible button and retry once
    # only if the UI still clearly shows the idle GENERATE VIDEO label.
    # The Flutter semantics tree can continue to show the idle button while
    # frame rendering starts. Check logcat before retrying: blindly tapping again
    # created two simultaneous MP4 renders in CI, so never retry after renderer
    # activity has already begun.
    tap_log = run(["adb", "logcat", "-d", "-t", "3000"], check=False, capture=True)
    renderer_started = "LOCAL_VIDEO_STAGE: preparing_frames" in tap_log or "LOCAL_VIDEO_STAGE: drawing_frames" in tap_log
    if "generate video" in first_ui and "rendering locally" not in first_ui and not renderer_started:
        try:
            retry_root = ET.parse(studio_xml).getroot()
            retry_candidates = []
            for node in retry_root.iter():
                label = (node.attrib.get("text", "") + " " + node.attrib.get("content-desc", "")).upper()
                if node.attrib.get("clickable") == "true" and "GENERATE VIDEO" in label:
                    bounds = re.fullmatch(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", node.attrib.get("bounds", ""))
                    if bounds:
                        ax, ay, bx, by = map(int, bounds.groups())
                        if bx > ax and by > ay and 0 <= ax < screen_w and 0 <= ay < screen_h:
                            retry_candidates.append((max(1, bx-ax)*max(1, by-ay), (ax+bx)//2, (ay+by)//2))
            if retry_candidates:
                _, retry_x, retry_y = min(retry_candidates)
                mark_phase("generate_button_still_idle; retrying_current_bounds; x=" + str(retry_x) + "; y=" + str(retry_y))
                run(["adb", "shell", "input", "tap", str(retry_x), str(retry_y)], timeout=15)
                time.sleep(3)
                first_ui = capture_studio_ui().lower()
        except (ET.ParseError, OSError) as retry_error:
            print("Could not refresh Generate Video bounds:", retry_error, file=sys.stderr)
    mark_phase("local_video_generate_tapped; waiting_for_verified_mp4")
    (OUT / "emulator-local-video-studio-after-tap.xml").write_text(first_ui, encoding="utf-8")
    deadline = time.monotonic() + 240
    final_ui = ""
    last_diagnostic = time.monotonic()
    while time.monotonic() < deadline:
        time.sleep(6)
        final_ui = capture_studio_ui().lower()
        if "verified: mp4 created and decoded successfully" in final_ui or "video created and verified" in final_ui:
            break
        if "video generation failed:" in final_ui or "mp4 encoding failed" in final_ui:
            raise RuntimeError("Local MP4 render failed: " + final_ui[-1800:].replace("\n", " "))
        if not run(["adb", "shell", "pidof", "com.marksai.app"], check=False, capture=True).strip():
            raise RuntimeError("App process died while rendering the local MP4")
        # Leave a durable heartbeat and fresh logcat evidence during rendering,
        # so a slow or stalled emulator can be diagnosed without waiting for
        # the entire 240-second window to end.
        if time.monotonic() - last_diagnostic >= 30:
            mark_phase("rendering_mp4; waiting_for_verified_result")
            (OUT / "emulator-local-video-studio-live-ui.xml").write_text(final_ui, encoding="utf-8")
            # Preserve a visual checkpoint as well as the accessibility tree.
            # This helps distinguish a frozen progress panel from a UI that is
            # merely exposing incomplete accessibility labels in headless CI.
            try:
                run(["adb", "shell", "screencap", "-p", "/sdcard/marks-ai-local-video-live.png"],
                    check=False, timeout=12)
                run(["adb", "pull", "/sdcard/marks-ai-local-video-live.png",
                     str(OUT / "emulator-local-video-studio-live-screen.png")],
                    check=False, timeout=12)
            except Exception as diagnostic_error:
                (OUT / "emulator-phase-debug.txt").write_text(
                    "render heartbeat screenshot failed: " + str(diagnostic_error), encoding="utf-8")
            last_diagnostic = time.monotonic()
    (OUT / "emulator-local-video-studio-screen.xml").write_text(final_ui, encoding="utf-8")
    LOG.write_text(run(["adb", "logcat", "-d", "-t", "8000"], check=False, capture=True), encoding="utf-8")
    log = LOG.read_text(encoding="utf-8", errors="replace")
    # UI accessibility labels can lag behind the completed Flutter state update.
    # Accept that case only when logcat proves decode verification completed and
    # the exact generated MP4 is still present in the app's private video folder.
    ui_verified = ("verified: mp4 created and decoded successfully" in final_ui
                   or "video created and verified" in final_ui)
    if not ui_verified:
        paths = re.findall(r"LOCAL_VIDEO_STAGE: mpeg4_encode_started output=(/data/user/0/com\.marksai\.app/app_flutter/mark_ai_local_video/[^\s]+\.mp4)", log)
        paths = list(dict.fromkeys(paths))
        decode_ok = "LOCAL_VIDEO_STAGE: decode_verification_completed" in log
        existing_path = None
        for path in reversed(paths):
            # Use the exact absolute path logged by FFmpeg. Relative paths can
            # resolve differently across Android run-as shells and app versions.
            # Print a diagnostic listing on failure so the next run shows whether
            # the renderer cleaned up or saved to a different documents path.
            # Avoid nested shell quoting here: adb shell joins arguments differently
            # across Android platform-tools versions. Run ls directly through run-as,
            # then validate the exact MP4 path and retain the diagnostic output.
            filename = Path(path).name
            # run-as starts in the app's data directory. Use the app-relative
            # path because Android can deny traversal of /data/user/0 even to
            # the owning package when an absolute path is supplied.
            relative_path = "app_flutter/mark_ai_local_video/" + filename
            # Listing the containing directory is more reliable than asking
            # Android run-as to stat a single absolute path. Then stat the
            # relative file and require a plausible non-empty MP4 size.
            directory_listing = run(["adb", "shell", "run-as", "com.marksai.app",
                                     "ls", "-la", "app_flutter/mark_ai_local_video"],
                                    check=False, capture=True, timeout=12)
            file_size_text = run(["adb", "shell", "run-as", "com.marksai.app",
                                  "stat", "-c", "%s", relative_path],
                                 check=False, capture=True, timeout=12).strip()
            try:
                file_size = int(file_size_text)
            except ValueError:
                file_size = 0
            (OUT / "emulator-mp4-file-probe.txt").write_text(
                "path=" + path + "\\nrelative_path=" + relative_path +
                "\\ndirectory_listing=" + directory_listing +
                "\\nfile_size=" + file_size_text + "\\n", encoding="utf-8")
            if (filename in directory_listing and file_size > 1000
                    and "No such file" not in directory_listing
                    and "Permission denied" not in directory_listing):
                existing_path = path
                break
        encode_ok = "LOCAL_VIDEO_STAGE: encode_success bytes=" in log
        if not (decode_ok and (existing_path or (encode_ok and paths))):
            probe_path = OUT / "emulator-mp4-file-probe.txt"
            probe_detail = (probe_path.read_text(encoding="utf-8", errors="replace")
                            if probe_path.exists() else "MP4 file probe was not created")
            raise RuntimeError(
                "Local MP4 render could not be verified; decode_verified=" + str(decode_ok) +
                "; encode_success=" + str(encode_ok) + "; candidate_paths=" + repr(paths) +
                "; file_probe=" + probe_detail[-2400:] +
                "; last UI: " + final_ui[-1200:].replace("\n", " "))
        if existing_path:
            verification_detail = "MP4 exists and is non-empty at " + existing_path
        else:
            # Release APKs are intentionally non-debuggable, so Android blocks
            # run-as access to app-private files. Require both successful encode
            # with a byte count and the renderer's decode verification marker.
            # This verifies media generation, but explicitly does not claim that
            # the private file was independently stat'ed by the test harness.
            verification_detail = (
                "release APK is non-debuggable; renderer logged encoded MP4 bytes "
                "and completed decode verification; private-file stat unavailable")
        (OUT / "emulator-local-video-studio-ui-status-warning.txt").write_text(
            "Renderer verification: " + verification_detail +
            "; accessibility UI did not expose the success status within 240s.\n",
            encoding="utf-8")

    if "FATAL EXCEPTION" in log or "Process: com.marksai.app" in log:
        raise RuntimeError("Android crash signature detected after local MP4 render")

    # Exercise the in-app gallery export when the generated-video screen exposes
    # its save action. Record this separately from render success so a platform
    # permission dialog cannot hide the already-proven MP4 renderer result.
    gallery_status = "not_tested_button_not_visible"
    try:
        gallery_buttons = []
        # The export button is below the fold on some emulator sizes. Scroll the
        # Local Video Studio screen and refresh accessibility XML before giving
        # up; the previous test only inspected the first viewport.
        for gallery_scroll in range(5):
            try:
                gallery_root = ET.parse(OUT / "emulator-local-video-studio-screen.xml").getroot()
            except (ET.ParseError, OSError):
                gallery_root = None
            gallery_buttons = []
            if gallery_root is not None:
                for node in gallery_root.iter():
                    label = (node.attrib.get("text", "") + " " + node.attrib.get("content-desc", "")).lower()
                    if node.attrib.get("clickable") == "true" and (
                            "save directly to phone gallery" in label or "save to gallery" in label):
                        bounds = re.fullmatch(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", node.attrib.get("bounds", ""))
                        if bounds:
                            ax, ay, bx, by = map(int, bounds.groups())
                            if bx > ax and by > ay and 0 <= ax < screen_w and 0 <= ay < screen_h:
                                gallery_buttons.append((max(1, bx-ax)*max(1, by-ay), (ax+bx)//2, (ay+by)//2))
            if gallery_buttons:
                break
            if gallery_scroll < 4:
                run(["adb", "shell", "input", "swipe", str(screen_w // 2),
                     str(int(screen_h * 0.82)), str(screen_w // 2),
                     str(int(screen_h * 0.30)), "650"], check=False, timeout=12)
                time.sleep(1.5)
                capture_studio_ui()
        if gallery_buttons:
            _, gx, gy = min(gallery_buttons)
            mark_phase("testing_gallery_export_button")
            run(["adb", "shell", "input", "tap", str(gx), str(gy)], timeout=12)
            time.sleep(3)
            gallery_ui = capture_studio_ui().lower()
            if "allow" in gallery_ui and ("photos" in gallery_ui or "media" in gallery_ui or "music and audio" in gallery_ui):
                try:
                    perm_root = ET.parse(OUT / "emulator-local-video-studio-screen.xml").getroot()
                    for node in perm_root.iter():
                        if node.attrib.get("clickable") == "true" and node.attrib.get("text", "").strip().lower() in ("allow", "while using the app"):
                            bounds = re.fullmatch(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", node.attrib.get("bounds", ""))
                            if bounds:
                                ax, ay, bx, by = map(int, bounds.groups())
                                run(["adb", "shell", "input", "tap", str((ax+bx)//2), str((ay+by)//2)], timeout=12)
                                time.sleep(2)
                                break
                except (ET.ParseError, OSError):
                    pass
                gallery_ui = capture_studio_ui().lower()
            (OUT / "emulator-gallery-export-ui.xml").write_text(gallery_ui, encoding="utf-8")
            if "saved to phone gallery" in gallery_ui or "marks ai films" in gallery_ui:
                gallery_status = "save_confirmation_visible"
            elif "permission" in gallery_ui or "allow" in gallery_ui:
                gallery_status = "permission_flow_visible_no_confirmation"
            else:
                gallery_status = "button_tapped_no_confirmation"
    except Exception as gallery_error:
        gallery_status = "test_error:" + str(gallery_error).replace("\\n", " ")[:300]

    ui_status_value = "passed" if ui_verified else "renderer_verified_ui_status_stale"
    SMOKE.write_text("status=passed; api=30; installed=true; launched=true; film_entry_visible=true; film_entry_tapped=true; local_video_studio_opened=true; generate_video_tapped=true; local_mp4_created=true; app_ffmpeg_decode_verified=true; ui_status=" + ui_status_value + "; gallery_export=" + gallery_status + "; process_alive=true; crash_signature=none\\n", encoding="utf-8")
    print("PASS: APK installed, app launched, Film Creator opened, local video rendered and MP4 decoded by FFmpeg.")
    return 0

if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        save_failure(str(error))
        print("EMULATOR SMOKE TEST FAILED:", error, file=sys.stderr)
        # Surface the actual Flutter renderer stage in the Actions log. Previously
        # the logcat snapshot was only uploaded as an artifact, making a stall
        # indistinguishable from a tap that never reached the renderer.
        try:
            diagnostic = LOG.read_text(encoding="utf-8", errors="replace")
            patterns = ("LOCAL_VIDEO_STAGE:", "LOCAL_VIDEO_GENERATION_FAILED:",
                        "FATAL EXCEPTION", "ANR in", "com.marksai.app")
            relevant = [line for line in diagnostic.splitlines()
                        if any(pattern in line for pattern in patterns)]
            print("=== MARKS AI VIDEO RENDER DIAGNOSTICS (last 160 lines) ===", file=sys.stderr)
            for line in relevant[-160:]:
                print(line[-1200:], file=sys.stderr)
            if not relevant:
                print("No renderer-stage markers found in captured logcat.", file=sys.stderr)
        except Exception as diagnostic_error:
            print("Could not print renderer diagnostics:", diagnostic_error, file=sys.stderr)
        raise SystemExit(1)
