#!/usr/bin/env python3
"""Prove FFmpeg can assemble a one-hour film from sixty short scene files."""
from pathlib import Path
import json
import shutil
import subprocess
import tempfile

def run(args, timeout=120):
    try:
        result = subprocess.run(
            args, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as error:
        output = error.stdout or ""
        if isinstance(output, bytes):
            output = output.decode("utf-8", errors="replace")
        raise SystemExit(
            "Long-film assembly timed out: " + " ".join(args) + "\n" + output[-4000:]
        )
    if result.returncode:
        raise SystemExit(
            "Command failed (" + str(result.returncode) + "): "
            + " ".join(args) + "\n" + result.stdout[-4000:]
        )
    return result.stdout

ffmpeg = shutil.which("ffmpeg")
ffprobe = shutil.which("ffprobe")
if not ffmpeg or not ffprobe:
    raise SystemExit("FFmpeg and ffprobe are required for the one-hour assembly test")

with tempfile.TemporaryDirectory(prefix="marks-ai-one-hour-") as temp:
    root = Path(temp)
    one_minute = root / "scene_source.mp4"
    # A small, one-frame-per-second source keeps this duration regression test
    # fast while still exercising a genuine 3,600-second MP4 timeline.
    run([
        ffmpeg, "-hide_banner", "-loglevel", "error", "-y",
        "-f", "lavfi", "-i", "color=c=blue:s=160x90:r=1:d=60",
        "-an", "-c:v", "mpeg4", "-q:v", "8", "-g", "1", str(one_minute),
    ])
    concat = root / "concat.txt"
    concat.write_text(
        "".join("file '" + str(one_minute) + "'\n" for _ in range(60)),
        encoding="utf-8",
    )
    output = root / "finished_one_hour_film.mp4"
    run([
        ffmpeg, "-hide_banner", "-loglevel", "error", "-y",
        "-f", "concat", "-safe", "0", "-i", str(concat),
        "-c", "copy", "-movflags", "+faststart", str(output),
    ])
    probe = json.loads(run([
        ffprobe, "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=codec_name,width,height",
        "-show_entries", "format=duration,size", "-of", "json", str(output),
    ]))
    streams = probe.get("streams", [])
    fmt = probe.get("format", {})
    duration = float(fmt.get("duration", 0))
    if not streams:
        raise SystemExit("One-hour output has no decodable video stream")
    if duration < 3599 or duration > 3601:
        raise SystemExit(f"Expected a 3,600-second film; got {duration:.3f}s")
    if int(fmt.get("size", 0)) <= 0:
        raise SystemExit("One-hour MP4 output is empty")
    # Decode frames from the start, middle, and end—not just the MP4 header.
    for timestamp in ("0", "1800", "3599"):
        run([
            ffmpeg, "-hide_banner", "-loglevel", "error", "-ss", timestamp,
            "-i", str(output), "-frames:v", "1", "-f", "null", "-",
        ])
    print("PASS: 60 scene clips were assembled into one MP4.")
    print(f"PASS: final duration={duration:.3f}s ({duration / 60:.1f} minutes).")
    print("PASS: video frames decode at the beginning, midpoint, and end.")
