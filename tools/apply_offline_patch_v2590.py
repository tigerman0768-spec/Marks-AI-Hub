from pathlib import Path

lib = Path("lib")

def write(name, body):
    (lib / name).write_text(body)

write("film_creator_project.dart", r"""import 'dart:convert';
import 'dart:io';
import 'package:path_provider/path_provider.dart';
import 'package:uuid/uuid.dart';

class FilmCreatorProject {
  final Map<String, dynamic> state;
  FilmCreatorProject(this.state);

  String get id => state['id']?.toString() ?? '';
  String get title => state['title']?.toString() ?? 'Untitled Film';
  String get idea => state['idea']?.toString() ?? '';
  String get genre => state['genre']?.toString() ?? 'Drama';
  int get length => int.tryParse(state['length']?.toString() ?? '5') ?? 5;
  String get style => state['style']?.toString() ?? 'Cinematic';
  String get aspectRatio => state['aspectRatio']?.toString() ?? '16:9';

  static Future<Directory> _dir() async {
    final root = await getApplicationDocumentsDirectory();
    final dir = Directory('${root.path}/marks_ai_projects');
    if (!await dir.exists()) await dir.create(recursive: true);
    return dir;
  }

  static Future<File> _file(String id) async {
    final dir = await _dir();
    final safe = id.replaceAll(RegExp(r'[^A-Za-z0-9_-]'), '_');
    return File('${dir.path}/${safe}.json');
  }

  static Future<FilmCreatorProject?> resume(String id) async {
    try {
      final f = await _file(id);
      if (!await f.exists()) return null;
      final data = jsonDecode(await f.readAsString()) as Map;
      return FilmCreatorProject(Map<String, dynamic>.from(data));
    } catch (_) {
      return null;
    }
  }

  static Future<FilmCreatorProject> createLocal(Map<String, dynamic> state) async {
    final id = const Uuid().v4();
    final p = FilmCreatorProject({...state, 'id': id});
    await p._write();
    return p;
  }

  Future<FilmCreatorProject> saveLocal(Map<String, dynamic> changes) async {
    final p = FilmCreatorProject({...state, ...changes, 'id': id});
    await p._write();
    return p;
  }

  Future<void> _write() async {
    final f = await _file(id);
    await f.writeAsString(jsonEncode(state), flush: true);
  }

  static Future<List<FilmCreatorProject>> allLocal() async {
    final dir = await _dir();
    final result = <FilmCreatorProject>[];
    await for (final e in dir.list()) {
      if (e is! File || !e.path.endsWith('.json')) continue;
      try {
        final data = jsonDecode(await e.readAsString()) as Map;
        result.add(FilmCreatorProject(Map<String, dynamic>.from(data)));
      } catch (_) {}
    }
    result.sort((a, b) => a.title.toLowerCase().compareTo(b.title.toLowerCase()));
    return result;
  }

  Future<void> deleteLocal() async {
    try {
      final f = await _file(id);
      if (await f.exists()) await f.delete();
    } catch (_) {}
  }
}
""")

write("film_creator_screen.dart", r"""import 'package:flutter/material.dart';
import 'film_creator_project.dart';

const List<String> kMarkAiGenres = [
  'Action','Comedy','Drama','Horror','Romance','Sci-Fi','Fantasy','Thriller'
];
const List<String> kMarkAiStyles = [
  'Cinematic','Realistic','Animation','Anime','Fantasy','Vintage'
];

class FilmCreatorScreen extends StatefulWidget {
  final String? projectId;
  const FilmCreatorScreen({super.key, this.projectId});

  @override
  State<FilmCreatorScreen> createState() => _FilmCreatorScreenState();
}

class _FilmCreatorScreenState extends State<FilmCreatorScreen> {
  final title = TextEditingController();
  final idea = TextEditingController();
  String genre = 'Drama';
  String style = 'Cinematic';
  String aspect = '16:9';
  int length = 5;
  String? projectId;
  bool loading = true;
  bool saving = false;

  @override
  void initState() {
    super.initState();
    projectId = widget.projectId;
    _load();
  }

  @override
  void dispose() {
    title.dispose();
    idea.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    if (projectId != null) {
      final p = await FilmCreatorProject.resume(projectId!);
      if (p != null) {
        title.text = p.title;
        idea.text = p.idea;
        genre = p.genre;
        length = p.length;
        style = p.style;
        aspect = p.aspectRatio;
      }
    }
    if (mounted) setState(() => loading = false);
  }

  Map<String, dynamic> _body() => {
    'title': title.text.trim().isEmpty ? 'Untitled Film' : title.text.trim(),
    'idea': idea.text.trim(),
    'genre': genre,
    'length': length,
    'style': style,
    'aspectRatio': aspect,
    'status': 'draft',
  };

  Future<void> _save({bool create = false}) async {
    setState(() => saving = true);
    try {
      final body = _body();
      if (projectId == null || create) {
        final p = await FilmCreatorProject.createLocal(body);
        projectId = p.id;
      } else {
        await FilmCreatorProject({'id': projectId!, ...body}).saveLocal(body);
      }
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Project saved on this phone')),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Local save failed: $e')),
        );
      }
    } finally {
      if (mounted) setState(() => saving = false);
    }
  }

  Future<void> _generateScreenplay() async {
    await _save(create: projectId == null);
    if (!mounted) return;
    final filmTitle = title.text.trim().isEmpty ? 'Untitled Film' : title.text.trim();
    final story = idea.text.trim().isEmpty
        ? 'A new story begins in a world waiting to be discovered.'
        : idea.text.trim();
    final script = '''
$filmTitle
Genre: $genre
Style: $style
Length: $length minutes
Aspect Ratio: $aspect

SCENE 1 — OPENING
FADE IN:

EXT. OPENING LOCATION — DAY

The story begins. $story

The main character takes the first step toward the central conflict.

SCENE 2 — THE TURNING POINT
The situation changes and the stakes become clear.

DIALOGUE
CHARACTER: We have to decide what happens next.

SCENE 3 — CLIMAX
The characters face the central challenge and make their defining choice.

SCENE 4 — RESOLUTION
The consequences unfold and the story reaches its ending.

FADE OUT.
THE END.
''';
    await showDialog<void>(
      context: context,
      builder: (_) => AlertDialog(
        title: const Text('Generated Screenplay'),
        content: SizedBox(
          width: double.maxFinite,
          child: SingleChildScrollView(child: SelectableText(script)),
        ),
        actions: [
          TextButton(onPressed: () => Navigator.of(context).pop(), child: const Text('CLOSE')),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    if (loading) {
      return const Scaffold(body: Center(child: CircularProgressIndicator()));
    }

    return Scaffold(
      appBar: AppBar(
        title: const Text('Film Creator'),
        actions: [
          IconButton(
            onPressed: saving ? null : () => _save(),
            icon: const Icon(Icons.save),
          ),
          const SizedBox(width: 8),
        ],
      ),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(16, 16, 16, 96),
        children: [
          Text('Create your film', style: Theme.of(context).textTheme.headlineMedium),
          const SizedBox(height: 8),
          const Text('Your project is saved directly on this phone. No server is required.'),
          const SizedBox(height: 20),
          TextField(
            controller: title,
            decoration: const InputDecoration(
              labelText: 'Film title',
              border: OutlineInputBorder(),
            ),
          ),
          const SizedBox(height: 12),
          TextField(
            controller: idea,
            minLines: 5,
            maxLines: 9,
            decoration: const InputDecoration(
              labelText: 'What is your film about?',
              hintText: 'Describe the story, characters, setting and what you want to happen…',
              border: OutlineInputBorder(),
            ),
          ),
          const SizedBox(height: 16),
          DropdownButtonFormField<String>(
            value: genre,
            decoration: const InputDecoration(labelText: 'Genre', border: OutlineInputBorder()),
            items: kMarkAiGenres.map((x) => DropdownMenuItem(value: x, child: Text(x))).toList(),
            onChanged: (v) { if (v != null) setState(() => genre = v); },
          ),
          const SizedBox(height: 12),
          DropdownButtonFormField<String>(
            value: style,
            decoration: const InputDecoration(labelText: 'Visual style', border: OutlineInputBorder()),
            items: kMarkAiStyles.map((x) => DropdownMenuItem(value: x, child: Text(x))).toList(),
            onChanged: (v) { if (v != null) setState(() => style = v); },
          ),
          const SizedBox(height: 12),
          DropdownButtonFormField<int>(
            value: length,
            decoration: const InputDecoration(labelText: 'Film length (minutes)', border: OutlineInputBorder()),
            items: [1, 5, 10, 30, 60].map((x) => DropdownMenuItem(value: x, child: Text('$x minutes'))).toList(),
            onChanged: (v) { if (v != null) setState(() => length = v); },
          ),
          const SizedBox(height: 12),
          DropdownButtonFormField<String>(
            value: aspect,
            decoration: const InputDecoration(labelText: 'Aspect ratio', border: OutlineInputBorder()),
            items: ['16:9', '9:16', '1:1'].map((x) => DropdownMenuItem(value: x, child: Text(x))).toList(),
            onChanged: (v) { if (v != null) setState(() => aspect = v); },
          ),
          const SizedBox(height: 24),
          FilledButton.icon(
            onPressed: saving ? null : () => _save(),
            icon: saving
                ? const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2))
                : const Icon(Icons.save),
            label: Text(saving ? 'SAVING…' : 'SAVE PROJECT'),
          ),
          const SizedBox(height: 10),
          const SizedBox(height: 8),
          FilledButton.icon(
            onPressed: saving ? null : _generateScreenplay,
            icon: const Icon(Icons.auto_awesome),
            label: const Text('GENERATE SCREENPLAY'),
          ),
          const SizedBox(height: 24),
        ],
      ),
    );
  }
}
""")


# Generate Screenplay is intentionally kept inside Film Creator.\n# Force the dashboard and completion screen to use a uniquely named offline creator.
# This prevents any stale/generated copy of the old network-based FilmCreatorScreen
# from being selected by the build.
import_file_replacements = [
    ("mark_ai_dashboard_screen.dart", "import 'film_creator_screen.dart';", "import 'film_creator_offline_screen.dart';"),
    ("mark_ai_dashboard_screen.dart", "FilmCreatorScreen()", "OfflineFilmCreatorScreen()"),
    ("app_completion_screen.dart", "import 'film_creator_screen.dart';", "import 'film_creator_offline_screen.dart';"),
    ("app_completion_screen.dart", "FilmCreatorScreen()", "OfflineFilmCreatorScreen()"),
]
for name, old, new in import_file_replacements:
    f = lib / name
    if f.exists():
        s = f.read_text()
        f.write_text(s.replace(old, new))

write("film_creator_offline_screen.dart", (lib / "film_creator_screen.dart").read_text()
      .replace("class FilmCreatorScreen", "class OfflineFilmCreatorScreen")
      .replace("State<FilmCreatorScreen>", "State<OfflineFilmCreatorScreen>")
      .replace("const FilmCreatorScreen(", "const OfflineFilmCreatorScreen(")
      .replace("_FilmCreatorScreenState", "_OfflineFilmCreatorScreenState"))


# Force every Dart caller of the Film Creator onto the offline implementation.
# The original project contains several generated/duplicate entry points, so do not
# rely on a couple of exact dashboard filenames.
for f in lib.glob("*.dart"):
    if f.name in ("film_creator_screen.dart", "film_creator_offline_screen.dart"):
        continue
    s = f.read_text()
    if "FilmCreatorScreen" in s:
        s = s.replace("import 'film_creator_screen.dart';", "import 'film_creator_offline_screen.dart';")
        s = s.replace("FilmCreatorScreen", "OfflineFilmCreatorScreen")
        f.write_text(s)

# Normalize any repeated replacement from earlier generated passes.
for f in lib.glob("*.dart"):
    s = f.read_text()
    if "OfflineOfflineFilmCreatorScreen" in s:
        f.write_text(s.replace("OfflineOfflineFilmCreatorScreen", "OfflineFilmCreatorScreen"))

# Remove stale emulator URLs from every generated Dart source file.
# The archive can contain legacy services that are not reachable from Film Creator,
# but their string constants would still be compiled into the APK. Keep the offline
# build free of the old emulator endpoint so the packaged APK cannot route Film Creator
# saves back to the unavailable local backend.
for f in lib.glob("*.dart"):
    s = f.read_text()
    s = s.replace("10.0.2.2:3000/api/projects", "offline://projects")
    s = s.replace("http://10.0.2.2:3000", "offline://backend")
    s = s.replace("10.0.2.2", "offline.local")
    s = s.replace("Save failed:", "Local save failed:")
    f.write_text(s)

# Final normalization after all replacements: never allow duplicated offline class names.
for f in lib.glob("*.dart"):
    s = f.read_text()
    if "OfflineOfflineFilmCreatorScreen" in s:
        f.write_text(s.replace("OfflineOfflineFilmCreatorScreen", "OfflineFilmCreatorScreen"))

# Do not place Generate Screenplay on the Studio dashboard.
# The action belongs inside Film Creator, after the user enters the film details.
# Fail-safe: the offline creator itself must contain no emulator URL or old network
# save message. The build must stop if this invariant is violated.
offline = (lib / "film_creator_offline_screen.dart").read_text()
assert "10.0.2.2" not in offline
assert "Save failed:" not in offline
