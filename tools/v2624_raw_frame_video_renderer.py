from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "app"
screen = ROOT / "lib" / "local_video_studio_screen.dart"
if not screen.exists():
    raise SystemExit("Local Video Studio screen missing")
s = screen.read_text(encoding="utf-8")

old = "final bytes = await image.toByteData(format: ui.ImageByteFormat.png);"
new = "final bytes = await image.toByteData(format: ui.ImageByteFormat.rawRgba);"
if old in s:
    s = s.replace(old, new, 1)
elif "ui.ImageByteFormat.rawRgba" not in s:
    raise SystemExit("Could not locate frame image encoding line")

old = """      final frameCount = seconds * 2;
      debugPrint('LOCAL_VIDEO_STAGE: drawing_frames count=' + frameCount.toString());
      for (int i = 0; i < frameCount; i++) {
        final bytes = await _frame(i, frameCount);
        await File(frameDir.path + '/frame_' + i.toString().padLeft(4, '0') + '.png').writeAsBytes(bytes);
        if (!mounted) return;
        setState(() { progress = .78 * (i + 1) / frameCount; status = 'Drawing frame ' + (i + 1).toString() + ' of ' + frameCount.toString() + '…'; });
      }
      debugPrint('LOCAL_VIDEO_STAGE: frames_complete count=' + frameCount.toString());"""
new = """      final frameCount = seconds * 2;
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
if old in s:
    s = s.replace(old, new, 1)
elif "raw frame file length mismatch" not in s:
    raise SystemExit("Could not locate frame writing loop")

old = """      final input = frameDir.path + '/frame_%04d.png';
      // The minimal FFmpeg package on Android may not include the MPEG-4 encoder.
      // Use Android MediaCodec directly at low resolution to avoid a known failing encoder.
      final base = '-y -threads 1 -framerate 2 -i "' + input + '" -vf "scale=640:360:flags=fast_bilinear,format=yuv420p" -movflags +faststart ';"""
new = """      final input = frameDir.path + '/frames.rgba';
      // Feed raw RGBA pixels to FFmpeg instead of PNG image sequences. This avoids
      // Android FFmpegKit PNG inflate errors and makes frame boundaries explicit.
      final base = '-y -threads 1 -f rawvideo -pixel_format rgba -video_size 640x360 -framerate 2 -i "' + input + '" -vf "scale=640:360:flags=fast_bilinear,format=yuv420p" -movflags +faststart ';"""
if old in s:
    s = s.replace(old, new, 1)
elif "-f rawvideo -pixel_format rgba -video_size 640x360" not in s:
    raise SystemExit("Could not locate FFmpeg input command")

s = s.replace("status = 'Encoding lightweight cinematic MP4 locally…';", "status = 'Encoding validated raw frames into a cinematic MP4 locally…';", 1)
screen.write_text(s, encoding="utf-8")
print("v2624: switched Local Video Studio to validated raw RGBA frames, bypassing PNG decoding.")
