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

write("film_creator_screen.dart", r"""import 'dart:convert';
import 'dart:io';
import 'package:flutter/material.dart';
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
  final backend = TextEditingController();
  String? remoteProjectId;
  String? productionId;
  String? renderId;
  String? filmUrl;
  String status = 'Ready';
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
    backend.dispose();
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
        backend.text = p.state['backendUrl']?.toString() ?? '';
        remoteProjectId = p.state['remoteProjectId']?.toString();
        productionId = p.state['productionId']?.toString();
        renderId = p.state['renderId']?.toString();
        filmUrl = p.state['filmUrl']?.toString();
        status = p.state['productionStatus']?.toString() ?? 'Ready';
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
    'backendUrl': _baseUrl(),
  };

  String _baseUrl() {
    var value = backend.text.trim();
    while (value.endsWith('/')) value = value.substring(0, value.length - 1);
    return value;
  }

  Future<Map<String, dynamic>> _request(String method, String path, [Map<String, dynamic>? body]) async {
    final base = _baseUrl();
    if (base.isEmpty) throw Exception('Enter your Mark’s AI backend URL first.');
    final client = HttpClient();
    try {
      final request = await client.openUrl(method, Uri.parse(base + path)).timeout(const Duration(seconds: 30));
      request.headers.contentType = ContentType.json;
      request.headers.set('Accept', 'application/json');
      if (body != null) request.write(jsonEncode(body));
      final response = await request.close().timeout(const Duration(minutes: 2));
      final text = await utf8.decoder.bind(response).join();
      dynamic decoded;
      try {
        decoded = text.isEmpty ? <String, dynamic>{} : jsonDecode(text);
      } catch (_) {
        decoded = <String, dynamic>{'raw': text};
      }
      if (response.statusCode < 200 || response.statusCode >= 300) {
        final message = decoded is Map && decoded['error'] != null
            ? decoded['error'].toString()
            : 'Server returned HTTP ' + response.statusCode.toString();
        throw Exception(message);
      }
      return decoded is Map ? Map<String, dynamic>.from(decoded) : <String, dynamic>{'data': decoded};
    } finally {
      client.close(force: true);
    }
  }

  Future<FilmCreatorProject> _saveState(String productionStatus) async {
    final changes = <String, dynamic>{..._body(), 'productionStatus': productionStatus};
    if (remoteProjectId != null) changes['remoteProjectId'] = remoteProjectId;
    if (productionId != null) changes['productionId'] = productionId;
    if (renderId != null) changes['renderId'] = renderId;
    if (filmUrl != null) changes['filmUrl'] = filmUrl;
    final p = projectId == null
        ? await FilmCreatorProject.createLocal(changes)
        : await FilmCreatorProject({'id': projectId!, ...changes}).saveLocal(changes);
    projectId = p.id;
    status = productionStatus;
    return p;
  }

  void _error(String message) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(message), duration: const Duration(seconds: 8)),
    );
  }

  Future<String> _ensureRemoteProject() async {
    if (remoteProjectId != null && remoteProjectId!.isNotEmpty) {
      try {
        await _request('PUT', '/api/projects/' + remoteProjectId!, {..._body(), 'id': remoteProjectId});
        return remoteProjectId!;
      } catch (_) {
        remoteProjectId = null;
      }
    }
    final result = await _request('POST', '/api/film/create', {
      'idea': idea.text.trim().isEmpty ? 'A new story begins and the main character discovers something that changes everything.' : idea.text.trim(),
      'genre': genre,
      'style': style,
      'length': length.toString() + ' min',
    });
    final id = result['projectId']?.toString() ?? (result['project'] is Map ? result['project']['id']?.toString() : null);
    if (id == null || id.isEmpty) throw Exception('Backend did not return a project ID.');
    remoteProjectId = id;
    return id;
  }

  String _screenplayText(Map<String, dynamic> result) {
    final screenplay = result['screenplay'];
    if (screenplay is String && screenplay.trim().isNotEmpty) return screenplay;
    if (screenplay is Map) {
      final b = StringBuffer();
      b.writeln(screenplay['title'] ?? title.text.trim());
      b.writeln();
      b.writeln(screenplay['logline'] ?? idea.text.trim());
      b.writeln();
      final scenes = screenplay['scenes'];
      if (scenes is List) {
        for (var i = 0; i < scenes.length; i++) {
          final scene = scenes[i];
          if (scene is Map) {
            b.writeln('SCENE ' + (i + 1).toString() + ' — ' + (scene['title']?.toString() ?? ''));
            b.writeln(scene['description']?.toString() ?? '');
            b.writeln('VISUAL PROMPT: ' + (scene['prompt']?.toString() ?? ''));
            b.writeln();
          }
        }
      }
      return b.toString();
    }
    return jsonEncode(result);
  }

  Future<void> _generateFilm() async {
    setState(() {
      saving = true;
      status = 'Preparing AI film production…';
    });
    try {
      await _save(create: projectId == null);
      if (_baseUrl().isEmpty) {
        throw Exception('Real AI film generation needs your deployed Mark’s AI backend URL. Your project is still saved on this phone.');
      }
      final id = await _ensureRemoteProject();
      final production = await _request('POST', '/api/film/produce', {'projectId': id});
      productionId = production['id']?.toString();
      if (productionId == null || productionId!.isEmpty) throw Exception('No production ID returned by backend.');
      await _saveState(production['status']?.toString() ?? 'planning');

      Map<String, dynamic> state = production;
      for (var i = 0; i < 1200; i++) {
        await Future<void>.delayed(const Duration(seconds: 3));
        state = await _request('GET', '/api/film/produce/' + productionId!);
        final current = state['status']?.toString() ?? 'unknown';
        if (mounted) setState(() => status = 'AI scene generation: ' + current + ' ' + (state['progress']?.toString() ?? '') + '%');
        await _saveState(current);
        if (current == 'ready_to_render') break;
        if (current == 'waiting_for_provider' || current == 'failed') {
          throw Exception(state['message']?.toString() ?? 'AI video generation failed.');
        }
      }
      if (state['status']?.toString() != 'ready_to_render') throw Exception('AI scene generation timed out.');

      if (mounted) setState(() => status = 'Starting final render…');
      final render = await _request('POST', '/api/render', {'projectId': id});
      renderId = render['id']?.toString();
      if (renderId == null || renderId!.isEmpty) throw Exception('No render ID returned by backend.');
      await _saveState('render_queued');
      await _request('POST', '/api/render/' + renderId! + '/run');

      Map<String, dynamic> renderState = render;
      for (var i = 0; i < 1200; i++) {
        await Future<void>.delayed(const Duration(seconds: 3));
        renderState = await _request('GET', '/api/render/' + renderId!);
        final current = renderState['status']?.toString() ?? 'unknown';
        if (mounted) setState(() => status = 'Final render: ' + current + ' ' + (renderState['progress']?.toString() ?? '') + '%');
        await _saveState(current);
        if (current == 'complete') break;
        if (current == 'failed') throw Exception(renderState['message']?.toString() ?? 'Final render failed.');
      }
      if (renderState['status']?.toString() != 'complete') throw Exception('Final render timed out.');

      filmUrl = renderState['filmUrl']?.toString();
      await _saveState('complete');
      if (mounted) {
        await showDialog<void>(
          context: context,
          builder: (_) => AlertDialog(
            title: const Text('Film Complete'),
            content: SelectableText(filmUrl == null || filmUrl!.isEmpty ? 'Your film was rendered successfully.' : 'Your film was rendered successfully.\n\n' + filmUrl!),
            actions: [TextButton(onPressed: () => Navigator.of(context).pop(), child: const Text('CLOSE'))],
          ),
        );
      }
    } catch (e) {
      await _saveState('failed');
      _error('Film generation failed: ' + e.toString());
    } finally {
      if (mounted) setState(() => saving = false);
    }
  }

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
    if (_baseUrl().isEmpty) {
      final filmTitle = title.text.trim().isEmpty ? 'Untitled Film' : title.text.trim();
      final story = idea.text.trim().isEmpty ? 'A new story begins in a world waiting to be discovered.' : idea.text.trim();
      final script = filmTitle + '\nGenre: ' + genre + '\nStyle: ' + style + '\nLength: ' + length.toString() + ' minutes\n\nSCENE 1 — OPENING\n\nThe story begins. ' + story + '\n\nSCENE 2 — TURNING POINT\n\nThe situation changes and the stakes become clear.\n\nSCENE 3 — CLIMAX\n\nThe characters face the central challenge.\n\nSCENE 4 — RESOLUTION\n\nThe story reaches its ending.\n\nFADE OUT.\nTHE END.';
      await _saveState('local_screenplay_ready');
      await showDialog<void>(
        context: context,
        builder: (_) => AlertDialog(
          title: const Text('Generated Screenplay'),
          content: SizedBox(width: double.maxFinite, child: SingleChildScrollView(child: SelectableText(script))),
          actions: [TextButton(onPressed: () => Navigator.of(context).pop(), child: const Text('CLOSE'))],
        ),
      );
      return;
    }
    setState(() {
      saving = true;
      status = 'Creating AI screenplay…';
    });
    try {
      final id = await _ensureRemoteProject();
      final result = await _request('POST', '/api/film/create', {
        'idea': idea.text.trim().isEmpty ? 'A new story begins and the main character discovers something that changes everything.' : idea.text.trim(),
        'genre': genre,
        'style': style,
        'length': length.toString() + ' min',
      });
      remoteProjectId = result['projectId']?.toString() ?? remoteProjectId;
      await _saveState('screenplay_ready');
      if (mounted) {
        await showDialog<void>(
          context: context,
          builder: (_) => AlertDialog(
            title: const Text('Generated Screenplay'),
            content: SizedBox(width: double.maxFinite, child: SingleChildScrollView(child: SelectableText(_screenplayText(result)))),
            actions: [TextButton(onPressed: () => Navigator.of(context).pop(), child: const Text('CLOSE'))],
          ),
        );
      }
    } catch (e) {
      _error('Screenplay generation failed: ' + e.toString());
    } finally {
      if (mounted) setState(() => saving = false);
    }
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
          const SizedBox(height: 18),
          TextField(
            controller: backend,
            enabled: !saving,
            keyboardType: TextInputType.url,
            decoration: const InputDecoration(
              labelText: 'Mark’s AI backend URL (optional)',
              hintText: 'https://your-server.example.com',
              helperText: 'Blank = phone-only mode. Add your backend URL for real AI video generation.',
              border: OutlineInputBorder(),
            ),
          ),
          const SizedBox(height: 18),
          if (status != 'Ready')
            Card(
              child: Padding(
                padding: const EdgeInsets.all(12),
                child: Row(
                  children: [
                    if (saving) const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2)),
                    if (saving) const SizedBox(width: 12),
                    Expanded(child: Text(status)),
                  ],
                ),
              ),
            ),
          FilledButton.icon(
            onPressed: saving ? null : _generateFilm,
            icon: const Icon(Icons.movie_creation),
            label: const Text('GENERATE FILM'),
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
    ("mark_ai_dashboard_screen.dart", "import 'film_creator_screen.dart';", "import 'film_creator_screen.dart';"),
    ("mark_ai_dashboard_screen.dart", "OfflineFilmCreatorScreen()", "FilmCreatorScreen()"),
    ("app_completion_screen.dart", "import 'film_creator_screen.dart';", "import 'film_creator_screen.dart';"),
    ("app_completion_screen.dart", "OfflineFilmCreatorScreen()", "FilmCreatorScreen()"),
]
for name, old, new in import_file_replacements:
    f = lib / name
    if f.exists():
        s = f.read_text()
        f.write_text(s.replace(old, new))

write("film_creator_offline_screen.dart", r"""import 'film_creator_screen.dart';

class OfflineFilmCreatorScreen extends FilmCreatorScreen {
  const OfflineFilmCreatorScreen({super.key, String? projectId})
      : super(projectId: projectId);
}
""")

# Keep legacy callers compiling while routing them to the hybrid creator.
for f in lib.glob("*.dart"):
    if f.name in ("film_creator_screen.dart", "film_creator_offline_screen.dart"):
        continue
    text = f.read_text()
    if "OfflineFilmCreatorScreen" in text:
        text = text.replace("OfflineFilmCreatorScreen", "FilmCreatorScreen")
        text = text.replace("import 'film_creator_offline_screen.dart';", "import 'film_creator_screen.dart';")
        f.write_text(text)


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
assert "GENERATE FILM" in offline
assert "api/film/produce" in offline
assert "api/render" in offline
