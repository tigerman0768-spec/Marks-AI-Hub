from pathlib import Path

path = Path("lib/screenplay_screen.dart")
if not path.exists():
    raise SystemExit("screenplay_screen.dart is missing")

source = path.read_text(encoding="utf-8")
start = source.find("  Future<void> _generate() async {")
end = source.find("  @override\n  Widget build", start)
if start < 0 or end < 0:
    raise SystemExit("Could not locate screenplay generation method boundaries")

method = r'''  Future<void> _generate() async {
    if (generating) return;
    if (mounted) setState(() => generating = true);
    try {
      final p = project ?? await FilmCreatorProject.resume(widget.projectId);
      if (p == null) {
        throw StateError('Saved film project could not be found on this device.');
      }
      final seed = p.idea.trim().isEmpty
          ? 'An unexpected event changes everything for the main character.'
          : p.idea.trim();
      final text = <String>[
        'TITLE: ' + p.title,
        'GENRE: ' + p.genre,
        'STYLE: ' + p.style,
        'TARGET LENGTH: ' + p.length.toString() + ' MINUTES',
        '',
        'FADE IN:',
        '',
        'SCENE 1 — THE BEGINNING',
        'EXT. ESTABLISHING LOCATION — DAY',
        '',
        'The world is introduced through a strong cinematic image. The main character enters with a clear goal.',
        '',
        'STORY IDEA',
        seed,
        '',
        'SCENE 2 — THE TURNING POINT',
        'INT. INTERIOR — DAY',
        '',
        'A new obstacle forces the protagonist to make a difficult choice. The stakes rise and the story moves into its central conflict.',
        '',
        'SCENE 3 — THE CLIMAX',
        'EXT. KEY LOCATION — NIGHT',
        '',
        'The conflict reaches its highest point. The protagonist acts and accepts the consequences of the choice.',
        '',
        'SCENE 4 — THE RESOLUTION',
        'EXT. FINAL IMAGE — DAWN',
        '',
        'The immediate conflict is resolved and the final image shows how the character and world have changed.',
        '',
        'FADE OUT.',
      ].join('\n');
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

'''
source = source[:start] + method + source[end:]
path.write_text(source, encoding="utf-8")
print("v2602 repaired malformed Dart screenplay string literals and retained error feedback.")
