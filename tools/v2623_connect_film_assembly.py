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
# Older source bundles can already contain the confirmation at the top of the
# scene method, before the health check. Relocate that block so the backend is
# verified before the user is asked to approve billable generation.
if confirm_marker in source:
    existing_start = source.find(confirm_marker)
    health_position = source.find("final healthPath =")
    if health_position >= 0 and existing_start < health_position:
        block_start = source.rfind("\\n", 0, existing_start) + 1
        block_end_marker = "if (approvedPaidGeneration != true) return;"
        block_end = source.find(block_end_marker, existing_start)
        if block_end < 0:
            raise SystemExit("Found an existing paid-generation confirmation but could not locate its end")
        block_end = source.find("\\n", block_end)
        if block_end < 0:
            block_end = len(source)
        else:
            block_end += 1
        source = source[:block_start] + source[block_end:]
if confirm_marker not in source:
    health_marker = "    // Check the backend before queueing any provider generation jobs. This"
    if health_marker not in source:
        # v2605 already has the same readiness guard with different wording.
        health_marker = "    // Check readiness before any billable scene submission."
    if health_marker not in source:
        # Last-resort anchor for equivalent readiness blocks without that comment.
        health_marker = "    final healthPath ="
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
    # Readiness should be checked before asking the user to approve a billable
    # request. Insert the confirmation after the health preflight, immediately
    # before the generation method starts its saving/submission state.
    health_start = source.find(health_marker)
    # Match the current v2605 method's mounted-aware state change first.
    # Falling back preserves compatibility with older source archives.
    insert_at = source.find("if (mounted) setState(() => saving = true);", health_start)
    if insert_at < 0:
        insert_at = source.find("    setState(() => saving = true);", health_start)
    if insert_at < 0:
        raise SystemExit("Could not find generation start after backend readiness preflight")
    insert_at = source.rfind("\\n", 0, insert_at) + 1
    source = source[:insert_at] + confirmation + source[insert_at:]

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
