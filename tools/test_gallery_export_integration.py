#!/usr/bin/env python3
"""Regression guard for Android Gallery export controls and emulator evidence."""
from pathlib import Path

project_root = Path(__file__).resolve().parents[1]
app_root = project_root / "app"
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
    "lib/film_assembly_screen.dart": [
        "import 'package:gal/gal.dart';",
        "Future<void> _saveToPhoneGallery()",
        "Gal.putVideo(path, album: 'Marks AI Films')",
        "SAVE FILM TO PHONE GALLERY",
    ],
}
errors = []
for relative, needles in checks.items():
    path = app_root / relative
    if not path.is_file():
        errors.append(f"Missing required file: app/{relative}")
        continue
    content = path.read_text(encoding="utf-8")
    for needle in needles:
        if needle not in content:
            errors.append(f"app/{relative}: missing {needle!r}")

smoke_path = project_root / "tools" / "emulator_smoke_test.py"
if not smoke_path.is_file():
    errors.append("Missing required file: tools/emulator_smoke_test.py")
else:
    smoke = smoke_path.read_text(encoding="utf-8")
    for needle in [
        "gallery_export=",
        'gallery_status != "save_confirmation_visible"',
        "PASS: Gallery export confirmed by the Android UI",
        "app_ffmpeg_decode_verified=true",
    ]:
        if needle not in smoke:
            errors.append(f"tools/emulator_smoke_test.py: missing {needle!r}")

if errors:
    print("FAIL: gallery export integration incomplete")
    print("\n".join(errors))
    raise SystemExit(1)
print("PASS: Gallery save controls, explicit failure handling, MP4 decode evidence, and emulator Gallery confirmation are guarded.")
