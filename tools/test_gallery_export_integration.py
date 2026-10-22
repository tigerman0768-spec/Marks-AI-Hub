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
        "Saved to phone Gallery in the Marks AI Films album",
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
print("PASS: local MP4 and assembled film both expose explicit Gallery export; success status is wired.")
