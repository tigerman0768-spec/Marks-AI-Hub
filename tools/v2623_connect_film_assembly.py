#!/usr/bin/env python3
"""Connect generated scene clips to final assembly and confirm billable AI requests."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
screen = ROOT / "app" / "lib" / "scene_prompt_screen.dart"
if not screen.is_file():
    raise SystemExit("scene_prompt_screen.dart not found")
source = screen.read_text(encoding="utf-8")

if "import 'film_assembly_screen.dart';" not in source:
    marker = "import 'film_creator_project.dart';"
    if marker not in source:
        raise SystemExit("Could not find Film Creator project import")
    source = source.replace(marker, marker + "\nimport 'film_assembly_screen.dart';", 1)

confirm_marker = "final approvedPaidGeneration = await showDialog<bool>("
if confirm_marker not in source:
    health_marker = "    // Check the backend before queueing any provider generation jobs. This"
    if health_marker not in source:
        raise SystemExit("Could not find backend readiness preflight insertion point")
    confirmation = r"""    final approvedPaidGeneration = await showDialog<bool>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: const Text('Generate AI video clips?'),
        content: Text(
          'This will submit ' + scenes.length.toString() +
          ' separate video-generation requests. Your provider may charge for usage. ' +
          'Continue only if you accept those possible charges.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(dialogContext, false),
            child: const Text('CANCEL'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(dialogContext, true),
            child: const Text('CONTINUE'),
          ),
        ],
      ),
    );
    if (approvedPaidGeneration != true) return;

"""
    source = source.replace(health_marker, confirmation + health_marker, 1)

if "ASSEMBLE & PLAY FINISHED FILM" not in source:
    button_marker = """label: const Text('GENERATE VIDEO CLIPS'),
          ),"""
    if button_marker not in source:
        raise SystemExit("Could not find Generate Video Clips button")
    assembly_button = button_marker + """
          const SizedBox(height: 10),
          OutlinedButton.icon(
            onPressed: saving || scenes.isEmpty ||
                    scenes.any((scene) => (scene['localClipPath'] ?? '').toString().isEmpty)
                ? null
                : () async {
                    await Navigator.push(
                      context,
                      MaterialPageRoute(
                        builder: (_) => FilmAssemblyScreen(projectId: widget.projectId),
                      ),
                    );
                    await _load();
                  },
            icon: const Icon(Icons.movie_creation_outlined),
            label: Text(
              scenes.isNotEmpty && scenes.every(
                (scene) => (scene['localClipPath'] ?? '').toString().isNotEmpty,
              )
                  ? 'ASSEMBLE & PLAY FINISHED FILM'
                  : 'ASSEMBLE FILM (' + scenes.where((scene) => (scene['localClipPath'] ?? '').toString().isNotEmpty).length.toString() + '/' + scenes.length.toString() + ' CLIPS READY)',
            ),
          ),"""
    source = source.replace(button_marker, assembly_button, 1)

screen.write_text(source, encoding="utf-8")
print("PASS: connected scene planner to final assembly and added paid-generation confirmation")
