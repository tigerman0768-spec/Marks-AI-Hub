#!/usr/bin/env python3
"""Smoke-test Mark's AI's local MP4 storyboard on an Android emulator."""
import subprocess, time, xml.etree.ElementTree as ET, sys, os, glob

def adb(*args, check=True):
    return subprocess.run(["adb", *args], text=True, stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT, check=check).stdout

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
for attempt in range(5):
    result = subprocess.run(["adb", "install", "-r", "app/build/app/outputs/flutter-apk/app-debug.apk"],
                            text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    print("APK install attempt", attempt + 1, "exit", result.returncode, "output:", result.stdout, flush=True)
    if result.returncode == 0 and "Success" in result.stdout:
        installed = True
        break
    time.sleep(5)
if not installed:
    print(adb("devices", "-l", check=False), flush=True)
    raise SystemExit("APK installation failed after retries.")
adb("shell", "monkey", "-p", "com.marksai.app", "1", check=False)
time.sleep(20)
# Dashboard tile labels vary slightly between archive revisions.
if not tap_text(["Film Creator", "Create Film", "Film Studio", "Create a Film"]):
    if recover_system_dialog():
        time.sleep(15)
if not tap_text(["Film Creator", "Create Film", "Film Studio", "Create a Film"]):
    raise SystemExit("Could not find a Film Creator entry on the dashboard.")
time.sleep(5)
found = False
for _ in range(8):
    if tap_text(["GENERATE LOCAL MP4 PREVIEW"], exact=True):
        found = True
        break
    adb("shell", "input", "swipe", "500", "800", "500", "300", "450")
    time.sleep(1)
if not found:
    raise SystemExit("Local MP4 preview button was not found on the Film Creator screen.")
# Native encoder renders 300 frames; allow ample time on the emulator.
deadline = time.time() + 120
success = False
while time.time() < deadline:
    root = ui_dump()
    labels = [n.attrib.get("text", "") for n in root.iter("node")]
    print("UI:", [x for x in labels if x][:30], flush=True)
    if any("Storyboard preview created" in x for x in labels):
        success = True
        break
    if any("Local video render failed" in x or "LOCAL_RENDER_FAILED" in x for x in labels):
        raise SystemExit("The app reported a local MP4 rendering error.")
    time.sleep(4)
if not success:
    raise SystemExit("Timed out waiting for storyboard preview completion dialog.")
# Check the actual file on device, then validate its MP4 container and duration.
listing = adb("shell", "ls", "-lt", "/sdcard/Movies/MarksAI", check=False)
print(listing, flush=True)
files = [line.split()[-1] for line in listing.splitlines() if line.strip().endswith(".mp4") and not line.startswith("total")]
if not files:
    raise SystemExit("Success dialog appeared, but no MP4 exists in Movies/MarksAI.")
os.makedirs("/tmp/marksai-mp4-test", exist_ok=True)
device_path = "/sdcard/Movies/MarksAI/" + files[0]
local_path = "/tmp/marksai-mp4-test/preview.mp4"
adb("pull", device_path, local_path)
probe = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration,size", "-of", "default=noprint_wrappers=1", local_path], text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
print("ffprobe:", probe.stdout, flush=True)
if probe.returncode != 0:
    raise SystemExit("Generated file is not a valid MP4 container.")
data = dict(line.split("=",1) for line in probe.stdout.splitlines() if "=" in line)
if float(data.get("duration", "0")) < 25 or int(data.get("size", "0")) < 10000:
    raise SystemExit("Generated MP4 is too short or too small to be a valid 30-second preview.")
print("PASS: emulator generated a playable MP4 of " + data["duration"] + " seconds.", flush=True)
