from pathlib import Path

p = Path(__file__).resolve().parents[1] / "app" / "lib" / "scene_prompt_screen.dart"
if not p.exists():
    raise SystemExit("scene_prompt_screen.dart not found")
s = p.read_text(encoding="utf-8")
needle = """        final scene = scenes[i];
        scene['status'] = 'submitting';"""
replacement = """        final scene = scenes[i];
        // Resume safely: never spend another generation on a clip already on disk.
        final existingPath = scene['localClipPath']?.toString() ?? '';
        if (existingPath.isNotEmpty) {
          final existingFile = File(existingPath);
          if (await existingFile.exists() && await existingFile.length() >= 1024) {
            scene['status'] = 'downloaded';
            downloaded++;
            continue;
          }
        }
        scene['status'] = 'submitting';"""
if "Resume safely: never spend another generation" in s:
    print("v2606 resume-safe clip generation already applied")
elif needle not in s:
    raise SystemExit("Could not find scene submission point; refusing unsafe patch")
else:
    s = s.replace(needle, replacement, 1)
    if "import 'dart:io';" not in s:
        s = s.replace("import 'package:flutter/material.dart';", "import 'dart:io';\nimport 'package:flutter/material.dart';")
    p.write_text(s, encoding="utf-8")
    print("v2606 resume-safe clip generation applied")
