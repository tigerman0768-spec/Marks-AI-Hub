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


# v2626: Keep Gallery export discoverable beside Generate Video on small screens.
screen = ROOT / "lib" / "local_video_studio_screen.dart"
s = screen.read_text(encoding="utf-8")
button_anchor = """      FilledButton.icon(onPressed: rendering ? null : () { _render(); }, icon: rendering ? const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2)) : const Icon(Icons.movie_creation), label: Text(rendering ? 'RENDERING LOCALLY…' : 'GENERATE VIDEO')),
      const SizedBox(height: 12),
      Text(status),"""
button_replacement = """      FilledButton.icon(onPressed: rendering ? null : () { _render(); }, icon: rendering ? const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2)) : const Icon(Icons.movie_creation), label: Text(rendering ? 'RENDERING LOCALLY…' : 'GENERATE VIDEO')),
      const SizedBox(height: 8),
      FilledButton.icon(
        onPressed: rendering || outputPath == null ? null : _saveLocalVideoToGallery,
        icon: const Icon(Icons.video_library),
        label: const Text('SAVE TO GALLERY'),
      ),
      const SizedBox(height: 12),
      Text(status),"""
if button_anchor in s and "label: const Text('SAVE TO GALLERY')" not in s:
    s = s.replace(button_anchor, button_replacement, 1)
    screen.write_text(s, encoding="utf-8")
elif "label: const Text('SAVE TO GALLERY')" not in s:
    raise SystemExit("Could not locate Generate Video button to add visible Gallery action")
print("v2626: added a discoverable Gallery save action beside Generate Video.")
