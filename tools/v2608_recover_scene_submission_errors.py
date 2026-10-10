from pathlib import Path

p = Path(__file__).resolve().parents[1] / "app" / "lib" / "scene_prompt_screen.dart"
if not p.exists():
    raise SystemExit("scene_prompt_screen.dart not found")
s = p.read_text(encoding="utf-8")
start_marker = "        // Bound submission time so a stalled backend cannot freeze the\n"
end_marker = "        }\n        final activeTask = task!;"
if "v2608 per-scene submission recovery" in s:
    print("v2608 per-scene submission recovery already applied")
    raise SystemExit(0)
start = s.find(start_marker)
if start < 0:
    raise SystemExit("Could not locate bounded submission block")
end = s.find(end_marker, start)
if end < 0:
    raise SystemExit("Could not locate end of task-submission branch")
block = s[start:end]
# Catch submission, response decoding, and direct-URL download errors per scene.
# A bad scene is recorded and the queue continues instead of aborting the whole film.
replacement = (
    "        // v2608 per-scene submission recovery: one broken request must not stop the queue.\n"
    "        try {\n" + block +
    "        } catch (e) {\n"
    "          scene['status'] = 'failed';\n"
    "          scene['error'] = 'Submission failed: ' + e.toString();\n"
    "          failed++;\n"
    "          await _saveSceneState(p);\n"
    "          if (mounted) setState(() {});\n"
    "          continue;\n"
    "        }\n"
)
s = s[:start] + replacement + s[end:]
p.write_text(s, encoding="utf-8")
print("v2608 added per-scene exception recovery; failed submissions are saved and later scenes continue.")
