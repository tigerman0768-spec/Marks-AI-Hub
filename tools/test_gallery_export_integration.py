#!/usr/bin/env python3
"""Regression guard for the explicit Android Gallery export controls."""
from pathlib import Path

root = Path(__file__).resolve().parents[1] / "app"
checks = {
    "pubspec.yaml": ["gal:"],
    "lib/local_video_studio_screen.dart": [
        "import 'package:gal/gal.dart';",
        "Future<void> _saveLocalVideoToGallery()",
        "Gal.putVideo(path, album: 'Marks AI Films')",
        "SAVE DIRECTLY TO PHONE GALLERY",
        "bottomNavigationBar: outputPath == null ? null : SafeArea(",
        "onPressed: rendering ? null : _saveLocalVideoToGallery",
        "Saved to phone Gallery in the Marks AI Films album",
        "Film saved to Gallery",
        "Could not save film",
        "Gallery export failed: ",
        "No finished film found",
        "Cannot save: the generated MP4 file is missing.",
    ],
    "tools/emulator_smoke_test.py": [
        \"gallery_export=\",
        \"gallery_status != \\\"save_confirmation_visible\\\"\",
        \"PASS: Gallery export confirmed by the Android UI\",
        \"app_ffmpeg_decode_verified=true\",
    ],
    "lib/film_assembly_screen.dart": [
        "import 'package:gal/gal.dart';",
        "Future<void> _saveToPhoneGallery()",
        "Gal.putVideo(path, album: 'Marks AI Films')",
        "SAVE FILM TO PHONE GALLERY",
    ],
}
errors = []
for relative, needles in checks.items():
    path = root / relative
    if not path.is_file():
        errors.append(f"Missing required file: {relative}")
        continue
    content = path.read_text(encoding="utf-8")
    for needle in needles:
        if needle not in content:
            errors.append(f"{relative}: missing {needle!r}")
if errors:
    print("FAIL: gallery export integration incomplete")
    print("\n".join(errors))
    raise SystemExit(1)
print("PASS: local MP4 exposes a fixed, visible Gallery export action; assembled film Gallery export and success status are wired.")
