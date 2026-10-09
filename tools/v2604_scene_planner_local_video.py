from pathlib import Path

path = Path("lib/scene_prompt_screen.dart")
if not path.exists():
    raise SystemExit("Scene planner source is missing")
s = path.read_text(encoding="utf-8")
if "local_video_studio_screen.dart" not in s:
    s = s.replace(
        "import 'film_creator_project.dart';",
        "import 'film_creator_project.dart';\nimport 'local_video_studio_screen.dart';",
    )
needle = "label: const Text('GENERATE VIDEO CLIPS'),\n          ),"
if needle not in s:
    raise SystemExit("Could not locate Generate Video Clips button; refusing unsafe patch")
replacement = needle + """
          const SizedBox(height: 10),
          OutlinedButton.icon(
            onPressed: saving ? null : () => Navigator.push(
              context,
              MaterialPageRoute(builder: (_) => LocalVideoStudioScreen(projectId: widget.projectId)),
            ),
            icon: const Icon(Icons.movie_creation_outlined),
            label: const Text('MAKE A LOCAL TEST VIDEO'),
          ),"""
if "MAKE A LOCAL TEST VIDEO" not in s:
    s = s.replace(needle, replacement, 1)
path.write_text(s, encoding="utf-8")
print("v2604 added an offline local-render route from the scene planner.")
