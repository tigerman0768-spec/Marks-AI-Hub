from pathlib import Path
import re

lib = Path("lib")
creator = lib / "film_creator_screen.dart"
screenplay = lib / "screenplay_screen.dart"

if not creator.exists() or not screenplay.exists():
    raise SystemExit("Required Film Creator screens are missing; refusing to build a misleading APK.")

s = creator.read_text(encoding="utf-8")
s = re.sub(
    r"  Future<FilmCreatorProject> _save\(\) async \{.*?\n  Future<void> _generateScreenplay\(\) async \{.*?\n  \}",
    """  Future<FilmCreatorProject> _save() async {
    if (mounted) setState(() => saving = true);
    try {
      final values = <String, dynamic>{
        'title': title.text.trim().isEmpty ? 'Untitled Film' : title.text.trim(),
        'idea': idea.text.trim(),
        'genre': genre,
        'length': length,
        'style': style,
        'aspectRatio': aspect,
        'status': 'draft',
      };
      FilmCreatorProject? existing;
      if (projectId != null) existing = await FilmCreatorProject.resume(projectId!);
      final p = existing == null
          ? await FilmCreatorProject.create(values)
          : await existing.save(values);
      projectId = p.id;
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Project saved on this device')),
        );
      }
      return p;
    } finally {
      if (mounted) setState(() => saving = false);
    }
  }

  Future<void> _generateScreenplay() async {
    try {
      final p = await _save();
      if (!mounted) return;
      await Navigator.push(
        context,
        MaterialPageRoute(builder: (_) => ScreenplayScreen(projectId: p.id)),
      );
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Could not open screenplay: $e')),
      );
    }
  }""",
    s,
    count=1,
    flags=re.S,
)
if "Could not open screenplay:" not in s:
    raise SystemExit("Could not safely patch Film Creator save/screenplay handlers.")
# The toolbar save action must also surface errors instead of silently failing.
s = s.replace(
    "actions: [IconButton(onPressed: saving ? null : _save, icon: const Icon(Icons.save))],",
    """actions: [IconButton(
          onPressed: saving ? null : () async { try { await _save(); } catch (e) {
            if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Save failed: $e')));
          }},
          icon: const Icon(Icons.save),
        )],"""
)
s = s.replace(
    "onPressed: saving ? null : _save,\n            icon: saving ?",
    """onPressed: saving ? null : () async { try { await _save(); } catch (e) {
              if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Save failed: $e')));
            }},
            icon: saving ?"""
)
creator.write_text(s, encoding="utf-8")

s = screenplay.read_text(encoding="utf-8")
s = re.sub(
    r"  Future<void> _generate\(\) async \{.*?\n  \}\n\n  @override\n  Widget build",
    """  Future<void> _generate() async {
    if (generating) return;
    if (mounted) setState(() => generating = true);
    try {
      final p = project ?? await FilmCreatorProject.resume(widget.projectId);
      if (p == null) throw StateError('Saved film project could not be found on this device.');
      final seed = p.idea.trim().isEmpty
          ? 'An unexpected event changes everything for the main character.'
          : p.idea.trim();
      final text = 'TITLE: ${p.title}\\n'
          'GENRE: ${p.genre}\\n'
          'STYLE: ${p.style}\\n'
          'TARGET LENGTH: ${p.length} MINUTES\\n\\n'
          'FADE IN:\\n\\n'
          'SCENE 1 — THE BEGINNING\\nEXT. ESTABLISHING LOCATION — DAY\\n\\n'
          'The world is introduced through a strong cinematic image. The main character enters with a clear goal.\\n\\n'
          'STORY IDEA\\n$seed\\n\\n'
          'SCENE 2 — THE TURNING POINT\\nINT. INTERIOR — DAY\\n\\n'
          'A new obstacle forces the protagonist to make a difficult choice. The stakes rise and the story moves into its central conflict.\\n\\n'
          'SCENE 3 — THE CLIMAX\\nEXT. KEY LOCATION — NIGHT\\n\\n'
          'The conflict reaches its highest point. The protagonist acts and accepts the consequences of the choice.\\n\\n'
          'SCENE 4 — THE RESOLUTION\\nEXT. FINAL IMAGE — DAWN\\n\\n'
          'The immediate conflict is resolved and the final image shows how the character and world have changed.\\n\\n'
          'FADE OUT.';
      project = await p.save({
        'screenplay': text,
        'hasScreenplay': true,
        'screenplayGeneratedAt': DateTime.now().toIso8601String(),
      });
      screenplay = text;
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Screenplay generated and saved locally')),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Screenplay generation failed: $e')),
        );
      }
    } finally {
      if (mounted) setState(() => generating = false);
    }
  }

  @override
  Widget build""",
    s,
    count=1,
    flags=re.S,
)
if "Screenplay generation failed:" not in s:
    raise SystemExit("Could not safely patch screenplay generation handler.")
screenplay.write_text(s, encoding="utf-8")
print("v2601 patched save errors, missing-project recovery, and screenplay feedback.")
