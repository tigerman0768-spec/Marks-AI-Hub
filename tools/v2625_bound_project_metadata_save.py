from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "app"
screen = ROOT / "lib" / "local_video_studio_screen.dart"
if not screen.exists():
    raise SystemExit("Local Video Studio screen missing")
s = screen.read_text(encoding="utf-8")
old = "project = await project!.save({'localGeneratedVideos': videos});"
new = "project = await project!.save({'localGeneratedVideos': videos}).timeout(const Duration(seconds: 8));"
if old in s:
    s = s.replace(old, new, 1)
elif new not in s:
    raise SystemExit("Could not locate optional project metadata save")
# Keep success feedback independent of optional metadata persistence.
if new not in s:
    raise SystemExit("Metadata save timeout patch was not applied")
screen.write_text(s, encoding="utf-8")
print("v2625: bounded optional project metadata saving so verified MP4 feedback cannot hang indefinitely.")
