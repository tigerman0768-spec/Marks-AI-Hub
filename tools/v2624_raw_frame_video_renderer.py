from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1] / "app"
screen = ROOT / "lib" / "local_video_studio_screen.dart"
if not screen.exists():
    raise SystemExit("Local Video Studio screen missing")
s = screen.read_text(encoding="utf-8")

old = "final bytes = await image.toByteData(format: ui.ImageByteFormat.png);"
if old in s:
    s = s.replace(old, "final bytes = await image.toByteData(format: ui.ImageByteFormat.rawRgba);", 1)
elif "ui.ImageByteFormat.rawRgba" not in s:
    raise SystemExit("Could not locate frame image encoding line")

loop = re.compile(
    # Patch-generated Dart source has changed indentation across earlier repair
    # stages. Anchor on frame-count and completion markers, not exact spacing.
    r"^[ \t]*(?:final frameRate\s*=\s*seconds\s*>=\s*60\s*\?\s*1\s*:\s*12\s*;\s*)?"
    r"final frameCount\s*=\s*seconds\s*\*\s*(?:2|frameRate)\s*;.*?"
    r"^[ \t]*debugPrint\('LOCAL_VIDEO_STAGE: frames_complete count='\s*"
    r"\+\s*frameCount\.toString\(\)\);",
    re.S | re.M,
)
replacement = """      final frameRate = seconds >= 60 ? 1 : 12;
      final frameCount = seconds * frameRate;
      debugPrint('LOCAL_VIDEO_STAGE: drawing_frames count=' + frameCount.toString());
      final rawFrames = File(frameDir.path + '/frames.rgba');
      if (await rawFrames.exists()) await rawFrames.delete();
      const expectedFrameBytes = 640 * 360 * 4;
      for (int i = 0; i < frameCount; i++) {
        final bytes = await _frame(i, frameCount);
        if (bytes.lengthInBytes != expectedFrameBytes) {
          throw StateError('Frame ' + (i + 1).toString() + ' has invalid raw pixel data: ' + bytes.lengthInBytes.toString() + ' bytes.');
        }
        await rawFrames.writeAsBytes(bytes, mode: i == 0 ? FileMode.write : FileMode.append, flush: i == frameCount - 1);
        if (!mounted) return;
        setState(() { progress = .78 * (i + 1) / frameCount; status = 'Drawing frame ' + (i + 1).toString() + ' of ' + frameCount.toString() + '…'; });
      }
      final rawLength = await rawFrames.length();
      if (rawLength != expectedFrameBytes * frameCount) {
        throw StateError('Raw frame file length mismatch: expected ' + (expectedFrameBytes * frameCount).toString() + ', got ' + rawLength.toString());
      }
      debugPrint('LOCAL_VIDEO_STAGE: frames_complete count=' + frameCount.toString() + ' raw_bytes=' + rawLength.toString());"""
if "raw frame file length mismatch" not in s.lower():
    if loop.search(s):
        s = loop.sub(lambda m: replacement, s, count=1)
    else:
        raise SystemExit("Could not locate frame loop in generated Local Video Studio source")
elif "-f rawvideo -pixel_format rgba -video_size 640x360" not in s:
    raise SystemExit("Found partial raw-frame renderer patch; refusing to overwrite an inconsistent renderer")

pattern = re.compile(r"      final input = frameDir\.path \+ '/frame_%04d\.png';\n.*?      final base = .*?;", re.S)
base_replacement = """      final input = frameDir.path + '/frames.rgba';
      // Raw RGBA input must match the 640x360 canvas dimensions above.
      final base = '-y -threads 1 -f rawvideo -pixel_format rgba -video_size 640x360 -framerate ' + frameRate.toString() + ' -i "' + input + '" -vf "fps=12,scale=640:360:flags=fast_bilinear,format=yuv420p" -movflags +faststart ';"""
if pattern.search(s):
    s = pattern.sub(lambda m: base_replacement, s, count=1)
elif "-f rawvideo -pixel_format rgba -video_size 640x360" not in s:
    raise SystemExit("Could not locate FFmpeg input command in Local Video Studio source")

screen.write_text(s, encoding="utf-8")
print("v2624: switched Local Video Studio to validated raw RGBA frames, bypassing PNG decoding.")
