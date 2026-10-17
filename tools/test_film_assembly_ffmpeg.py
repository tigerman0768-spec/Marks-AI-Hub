#!/usr/bin/env python3
"""Exercise the exact FFmpeg concat/normalise strategy used by Film Assembly."""
from pathlib import Path
import json
import shutil
import subprocess
import tempfile

def run(args):
    result = subprocess.run(args, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    if result.returncode:
        raise SystemExit("Command failed (" + str(result.returncode) + "): " + " ".join(args) + "\n" + result.stdout[-5000:])
    return result.stdout

ffmpeg = shutil.which("ffmpeg")
ffprobe = shutil.which("ffprobe")
if not ffmpeg or not ffprobe:
    raise SystemExit("FFmpeg and ffprobe are required for the assembly media regression test")

with tempfile.TemporaryDirectory(prefix="marks-ai-assembly-") as temp:
    root = Path(temp)
    first = root / "scene_001.mp4"
    second = root / "scene_002.mp4"
    run([ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi",
         "-i", "color=c=blue:s=320x240:r=15:d=1", "-an", "-c:v", "mpeg4", "-q:v", "5", str(first)])
    run([ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi",
         "-i", "color=c=red:s=640x360:r=25:d=1", "-an", "-c:v", "mpeg4", "-q:v", "5", str(second)])
    concat = root / "concat.txt"
    concat.write_text("file '" + str(first) + "'\nfile '" + str(second) + "'\n", encoding="utf-8")
    output = root / "finished_film.mp4"
    # Match the app's normalising fallback, which handles scene dimension/fps
    # differences and produces a broadly playable H.264-like MP4 profile via MPEG-4.
    run([ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0",
         "-i", str(concat), "-vf",
         "scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2,fps=24,format=yuv420p",
         "-c:v", "mpeg4", "-q:v", "4", "-c:a", "aac", "-b:a", "128k", "-ar", "48000",
         "-ac", "2", "-movflags", "+faststart", str(output)])
    probe = json.loads(run([ffprobe, "-v", "error", "-select_streams", "v:0",
                            "-show_entries", "stream=codec_name,width,height",
                            "-show_entries", "format=duration,size", "-of", "json", str(output)]))
    streams = probe.get("streams", [])
    fmt = probe.get("format", {})
    if not streams:
        raise SystemExit("Assembly output has no decodable video stream")
    if int(streams[0].get("width", 0)) != 1280 or int(streams[0].get("height", 0)) != 720:
        raise SystemExit("Assembly output did not normalise to 1280x720")
    if float(fmt.get("duration", 0)) < 1.5:
        raise SystemExit("Assembly output duration is too short: " + str(fmt.get("duration")))
    run([ffmpeg, "-hide_banner", "-loglevel", "error", "-i", str(output), "-frames:v", "1", "-f", "null", "-"])
    print("PASS: mixed-resolution scene clips assembled into a decodable 1280x720 MP4.")
    print("PASS: duration=" + str(fmt["duration"]) + "s; codec=" + str(streams[0].get("codec_name")))
