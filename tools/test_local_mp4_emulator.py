#!/usr/bin/env python3
"""Smoke-test Mark's AI's local MP4 storyboard on an Android emulator."""
import subprocess, time, xml.etree.ElementTree as ET, sys, os, glob

def adb(*args, check=True, timeout=35):
    try:
        return subprocess.run(["adb", *args], text=True, stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT, check=check, timeout=timeout).stdout
    except subprocess.TimeoutExpired as exc:
        output = exc.stdout or ""
        if isinstance(output, bytes):
            output = output.decode("utf-8", errors="replace")
        message = "ADB command timed out after " + str(timeout) + "s: " + " ".join(args)
        print(message, flush=True)
        if check:
            raise RuntimeError(message) from exc
        return output

def ui_dump():
    adb("shell", "uiautomator", "dump", "/sdcard/window.xml", check=False)
    raw = adb("exec-out", "cat", "/sdcard/window.xml", check=False)
    try:
        return ET.fromstring(raw)
    except ET.ParseError:
        return ET.Element("hierarchy")

def recover_system_dialog():
    # Recover from Android's slow-emulator system-not-responding prompt.
    root = ui_dump()
    for node in root.iter("node"):
        label = (node.attrib.get("text", "") + " " + node.attrib.get("content-desc", "")).strip()
        if label.lower() == "wait":
            bounds = node.attrib.get("bounds", "")
            nums = [int(x) for x in __import__("re").findall(r"-?\d+", bounds)]
            if len(nums) == 4:
                x, y = (nums[0]+nums[2])//2, (nums[1]+nums[3])//2
                adb("shell", "input", "tap", str(x), str(y), check=False)
                print("Tapped Android system recovery: Wait", flush=True)
                time.sleep(10)
                return True
    return False

def tap_text(needles, exact=False):
    root = ui_dump()
    for node in root.iter("node"):
        label = (node.attrib.get("text", "") + " " + node.attrib.get("content-desc", "")).strip()
        ok = any(label.lower() == n.lower() if exact else n.lower() in label.lower() for n in needles)
        if ok:
            bounds = node.attrib.get("bounds", "")
            nums = [int(x) for x in __import__("re").findall(r"-?\d+", bounds)]
            if len(nums) == 4:
                x, y = (nums[0]+nums[2])//2, (nums[1]+nums[3])//2
                adb("shell", "input", "tap", str(x), str(y))
                print("Tapped:", label, bounds, flush=True)
                return True
    print("Visible labels:", [n.attrib.get("text","") for n in root.iter("node") if n.attrib.get("text")][:80], flush=True)
    return False

print("Waiting for Android framework and package manager to finish booting...", flush=True)
adb("start-server", check=False)
ready = False
for attempt in range(120):
    state = adb("get-state", check=False).strip()
    boot = adb("shell", "getprop", "sys.boot_completed", check=False).strip() if state == "device" else ""
    package_service = adb("shell", "service", "check", "package", check=False).strip() if state == "device" and boot == "1" else ""
    if state == "device" and boot == "1" and "found" in package_service.lower():
        ready = True
        print("Android framework ready after", (attempt + 1) * 5, "seconds.", flush=True)
        break
    if attempt % 6 == 0:
        print("Boot check", attempt + 1, "ADB:", state or "(no response)", "boot_completed:", boot or "(not yet)", "package service:", package_service or "(not ready)", flush=True)
    time.sleep(5)
if not ready:
    print("Devices:", adb("devices", "-l", check=False), flush=True)
    print("Boot completed:", adb("shell", "getprop", "sys.boot_completed", check=False), flush=True)
    print("Package service:", adb("shell", "service", "check", "package", check=False), flush=True)
    raise SystemExit("Android framework/package manager did not become ready.")
print("Android version:", adb("shell", "getprop", "ro.build.version.release", check=False).strip(), flush=True)
installed = False
for attempt in range(4):
    try:
        apk_path = "app/build/app/outputs/flutter-apk/app-x86_64-debug.apk"
        if not os.path.isfile(apk_path):
            raise SystemExit("Expected x86_64 split APK missing: " + apk_path)
        print("Installing emulator-specific split APK:", apk_path, "size:", os.path.getsize(apk_path), "bytes", flush=True)
        # CI's emulator can report boot_completed before PackageManager is truly
        # responsive. Re-check the service immediately before each large install.
        service_ready = False
        for service_attempt in range(24):
            state = adb("get-state", check=False).strip()
            boot = adb("shell", "getprop", "sys.boot_completed", check=False).strip() if state == "device" else ""
            package_service = adb("shell", "service", "check", "package", check=False) if state == "device" and boot == "1" else ""
            if state == "device" and boot == "1" and "found" in package_service.lower():
                # PackageManager needs a short settle period after service registration.
                time.sleep(10)
                service_ready = True
                break
            time.sleep(5)
        if not service_ready:
            print("PackageManager not ready before install:", package_service if 'package_service' in locals() else "(unavailable)", flush=True)
            raise RuntimeError("Android PackageManager is not ready for APK installation")
        result = subprocess.run(["adb", "install", "--no-streaming", "-r", apk_path],
                                text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=240)
        print("APK install attempt", attempt + 1, "exit", result.returncode, "output:", result.stdout, flush=True)
        if result.returncode == 0 and "Success" in result.stdout:
            installed = True
            break
    except subprocess.TimeoutExpired as exc:
        output = exc.stdout or ""
        if isinstance(output, bytes):
            output = output.decode("utf-8", errors="replace")
        print("APK install attempt", attempt + 1, "timed out after 180 seconds. Output:", output, flush=True)
        print("ADB devices:", adb("devices", "-l", check=False), flush=True)
        print("Package manager:", adb("shell", "service", "check", "package", check=False), flush=True)
        print("--- install-stall diagnostics ---", flush=True)
        print("Data partition:", adb("shell", "df", "-h", "/data", check=False), flush=True)
        print("Memory:", adb("shell", "cat", "/proc/meminfo", check=False), flush=True)
        processes = adb("shell", "ps", "-A", check=False)
        print("Install-related processes:", "\\n".join(line for line in processes.splitlines() if any(k in line.lower() for k in ("system_server", "installd", "dex2oat", "artd", "lmkd", "package")))[-10000:], flush=True)
        logs = adb("logcat", "-d", "-t", "1800", check=False, timeout=60)
        needles = ("PackageManager", "PackageInstaller", "installd", "dex2oat", "artd", "lowmemory", "lmkd", "OutOfMemory", "ANR", "FATAL EXCEPTION", "ziparchive", "INSTALL_FAILED")
        relevant = [line for line in logs.splitlines() if any(k.lower() in line.lower() for k in needles)]
        print("Install-related logcat (last 250 lines):", "\\n".join(relevant[-250:])[-30000:], flush=True)
    # Let system_server/PackageManager recover before retrying after transient failures.\n    time.sleep(20)\nif not installed:
    print(adb("devices", "-l", check=False), flush=True)
    raise SystemExit("APK installation failed after retries.")
# Android 9 requires the declared legacy external-storage permission to publish into Movies.
grant = subprocess.run(
    ["adb", "shell", "pm", "grant", "com.marksai.app", "android.permission.WRITE_EXTERNAL_STORAGE"],
    text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=35
)
print("Legacy media permission grant exit:", grant.returncode, grant.stdout, flush=True)
if grant.returncode != 0:
    raise SystemExit("Could not grant WRITE_EXTERNAL_STORAGE to the test app; verify the manifest permission.")
# Start the app's Android activity directly instead of using the launcher;
# this avoids a known launcher/System UI ANR on resource-constrained CI emulators.
launch = adb("shell", "am", "start", "-W", "-n", "com.marksai.app/com.marksai.app.MainActivity", check=False)
print("Direct app launch:", launch, flush=True)
if "Error" in launch or "Exception" in launch:
    print("Falling back to package launcher.", flush=True)
    adb("shell", "monkey", "-p", "com.marksai.app", "1", check=False)
# Give Flutter time to build its first frame before inspecting the UI.
time.sleep(25)
for recovery in range(4):
    if not recover_system_dialog():
        break
    time.sleep(25)
# Dashboard tile labels vary slightly between archive revisions.
dashboard_found = False
for attempt in range(6):
    if tap_text(["Film Creator", "Create Film", "Film Studio", "Create a Film"]):
        dashboard_found = True
        break
    if recover_system_dialog():
        time.sleep(30)
    else:
        time.sleep(10)
if not dashboard_found:
    print("Recent app process:", adb("shell", "dumpsys", "activity", "activities", check=False)[-5000:], flush=True)
    print("Recent app logcat:", adb("logcat", "-d", "-t", "500", check=False)[-12000:], flush=True)
    raise SystemExit("Could not find a Film Creator entry on the dashboard after recovery retries.")
time.sleep(5)
found = False
for _ in range(8):
    if tap_text(["GENERATE LOCAL MP4 PREVIEW"], exact=True):
        found = True
        break
    adb("shell", "input", "swipe", "500", "800", "500", "300", "450")
    time.sleep(1)
if not found:
    print("--- UI hierarchy diagnostics ---", flush=True)
    print(adb("exec-out", "cat", "/sdcard/window.xml", check=False)[-12000:], flush=True)
    print("--- activity diagnostics ---", flush=True)
    print(adb("shell", "dumpsys", "activity", "activities", check=False)[-12000:], flush=True)
    print("--- Flutter / Android crash diagnostics ---", flush=True)
    logs = adb("logcat", "-d", "-t", "1200", check=False)
    keywords = ("flutter", "fatal exception", "androidruntime", "exception", "anr", "marksai", "render")
    print("\\n".join(line for line in logs.splitlines() if any(k in line.lower() for k in keywords))[-30000:], flush=True)
    try:
        adb("shell", "screencap", "-p", "/sdcard/marksai_failure.png", check=False)
        adb("pull", "/sdcard/marksai_failure.png", "/tmp/marksai-failure.png", check=False)
    except Exception as exc:
        print("Screenshot capture failed:", exc, flush=True)
    raise SystemExit("Local MP4 preview button was not found on the Film Creator screen; diagnostic logcat captured above.")
# Validate the actual saved MP4, not only a Flutter dialog that UIAutomator may not expose.
# The renderer inserts the MediaStore row only after encoding finishes and copying the file.
print("Polling Movies/MarksAI for the real rendered MP4...", flush=True)
deadline = time.time() + 180
device_path = None
last_listing = ""
output_dirs = [
    "/sdcard/Movies/MarksAI",
    # Android 9 fallback used only when public Movies storage cannot be created.
    "/sdcard/Android/data/com.marksai.app/files/Movies/MarksAI",
]
while time.time() < deadline:
    candidates = []
    listings = []
    for output_dir in output_dirs:
        listing = adb("shell", "find", output_dir, "-maxdepth", "1", "-type", "f", "-name", "*.mp4", check=False)
        listings.append(listing)
        candidates.extend(line.strip() for line in listing.splitlines()
                          if line.strip().startswith(output_dir + "/") and line.strip().endswith(".mp4"))
    last_listing = "\\n".join(listings)
    if candidates:
        candidate = candidates[-1]
        size = adb("shell", "stat", "-c", "%s", candidate, check=False).strip()
        if size.isdigit() and int(size) > 10000:
            device_path = candidate
            print("Found saved MP4:", device_path, "size:", size, "bytes", flush=True)
            break
    root = ui_dump()
    labels = [n.attrib.get("text", "") for n in root.iter("node")]
    visible = [x for x in labels if x]
    if any("LOCAL_RENDER_FAILED" in x or "Local video render failed" in x for x in visible):
        raise SystemExit("The app reported a local MP4 rendering error: " + repr(visible[:60]))
    elapsed = int(180 - (deadline - time.time()))
    if elapsed and elapsed % 30 < 5:
        print("Still waiting for output; visible UI labels:", visible[:30], flush=True)
    time.sleep(5)

if not device_path:
    print("No MP4 appeared. Public Movies/MarksAI listing:", adb("shell", "ls", "-l", "/sdcard/Movies/MarksAI", check=False), flush=True)
    print("No MP4 appeared. App-specific Movies/MarksAI listing:", adb("shell", "ls", "-l", "/sdcard/Android/data/com.marksai.app/files/Movies/MarksAI", check=False), flush=True)
    print("App process:", adb("shell", "pidof", "com.marksai.app", check=False), flush=True)
    print("Activity state:", adb("shell", "dumpsys", "activity", "activities", check=False)[-8000:], flush=True)
    os.makedirs("app/build/marksai-runtime-diagnostics", exist_ok=True)
    logs = adb("logcat", "-d", "-t", "2000", check=False, timeout=60)
    keywords = ("MarksAI", "LOCAL_RENDER_FAILED", "MediaCodec", "MediaMuxer", "MediaProvider", "FATAL EXCEPTION", "AndroidRuntime", "flutter", "Exception", "denied", "Permission", "ANR")
    relevant = [line for line in logs.splitlines() if any(k.lower() in line.lower() for k in keywords)]
    diag_text = "\n".join(relevant[-500:])
    with open("app/build/marksai-runtime-diagnostics/logcat-filtered.txt", "w", encoding="utf-8") as out:
        out.write(diag_text)
    print("Renderer/runtime logcat (last 500 matching lines):", diag_text[-35000:], flush=True)
    hierarchy = adb("exec-out", "cat", "/sdcard/window.xml", check=False)
    with open("app/build/marksai-runtime-diagnostics/window.xml", "w", encoding="utf-8") as out:
        out.write(hierarchy)
    try:
        adb("shell", "screencap", "-p", "/sdcard/marksai_failure.png", check=False)
        subprocess.run(["adb", "pull", "/sdcard/marksai_failure.png", "app/build/marksai-runtime-diagnostics/marksai-failure.png"],
                       text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=35, check=False)
    except Exception as exc:
        print("Screenshot capture failed:", exc, flush=True)
    raise SystemExit("No saved MP4 appeared in Movies/MarksAI within 180 seconds; runtime diagnostics captured.")

os.makedirs("/tmp/marksai-mp4-test", exist_ok=True)
local_path = "/tmp/marksai-mp4-test/preview.mp4"
adb("pull", device_path, local_path)
probe = subprocess.run(
    ["ffprobe", "-v", "error", "-select_streams", "v:0",
     "-show_entries", "stream=codec_name,width,height",
     "-show_entries", "format=duration,size",
     "-of", "default=noprint_wrappers=1", local_path],
    text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT
)
print("ffprobe:", probe.stdout, flush=True)
if probe.returncode != 0:
    raise SystemExit("Generated file is not a valid MP4 container.")
data = dict(line.split("=", 1) for line in probe.stdout.splitlines() if "=" in line)
if not data.get("codec_name") or int(data.get("width", "0")) < 1 or int(data.get("height", "0")) < 1:
    raise SystemExit("Generated MP4 has no valid video stream.")
if float(data.get("duration", "0")) < 25 or int(data.get("size", "0")) < 10000:
    raise SystemExit("Generated MP4 is too short or too small to be a valid 30-second preview.")
# Probe metadata alone does not prove the encoded stream can be decoded. Decode the
# complete saved file with FFmpeg and require at least one decoded video frame.
decode = subprocess.run(
    ["ffmpeg", "-v", "error", "-i", local_path, "-map", "0:v:0",
     "-f", "null", "-"],
    text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=180
)
print("FFmpeg full-stream decode exit:", decode.returncode, flush=True)
if decode.stdout.strip():
    print("FFmpeg decode output:", decode.stdout[-12000:], flush=True)
if decode.returncode != 0:
    raise SystemExit("Generated MP4 metadata exists, but full video-stream decoding failed.")
frame_probe = subprocess.run(
    ["ffprobe", "-v", "error", "-select_streams", "v:0",
     "-count_frames", "-show_entries", "stream=nb_read_frames",
     "-of", "default=noprint_wrappers=1:nokey=1", local_path],
    text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=60
)
print("Decoded frame count:", frame_probe.stdout.strip(), flush=True)
if frame_probe.returncode != 0 or not frame_probe.stdout.strip().isdigit() or int(frame_probe.stdout.strip()) < 1:
    raise SystemExit("Generated MP4 did not yield any decodable video frames.")
print("PASS: emulator saved an MP4 of " + data["duration"] + " seconds with codec " + data["codec_name"] + "; full-stream decode succeeded with " + frame_probe.stdout.strip() + " frames.", flush=True)
