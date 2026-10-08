from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "app"
LIB = ROOT / "lib"

def write(name, text):
    (LIB / name).write_text(text, encoding="utf-8")

write("film_creator_project.dart", r'''import 'dart:convert';
import 'dart:io';
import 'package:path_provider/path_provider.dart';

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

  static Future<File> _file() async {
    final dir = await getApplicationDocumentsDirectory();
    return File(dir.path + '/mark_ai_film_projects.json');
  }

  static Future<List<Map<String, dynamic>>> _all() async {
    try {
      final file = await _file();
      if (!await file.exists()) return <Map<String, dynamic>>[];
      final value = jsonDecode(await file.readAsString());
      if (value is! List) return <Map<String, dynamic>>[];
      return value.map((e) => Map<String, dynamic>.from(e as Map)).toList();
    } catch (_) {
      return <Map<String, dynamic>>[];
    }
  }

  static Future<void> _write(List<Map<String, dynamic>> items) async {
    final file = await _file();
    await file.writeAsString(const JsonEncoder.withIndent('  ').convert(items), flush: true);
  }

  static Future<FilmCreatorProject> create(Map<String, dynamic> values) async {
    final now = DateTime.now();
    final state = <String, dynamic>{
      'id': 'film_' + now.microsecondsSinceEpoch.toString(),
      'createdAt': now.toIso8601String(),
      'updatedAt': now.toIso8601String(),
      'status': 'draft',
      ...values,
    };
    final items = await _all();
    items.add(state);
    await _write(items);
    return FilmCreatorProject(state);
  }

  static Future<FilmCreatorProject?> resume(String id) async {
    final items = await _all();
    for (final item in items) {
      if (item['id']?.toString() == id) return FilmCreatorProject(item);
    }
    return null;
  }

  static Future<List<FilmCreatorProject>> all() async {
    final items = await _all();
    items.sort((a, b) => (b['updatedAt'] ?? '').toString().compareTo((a['updatedAt'] ?? '').toString()));
    return items.map(FilmCreatorProject.new).toList();
  }

  Future<FilmCreatorProject> save(Map<String, dynamic> changes) async {
    final merged = <String, dynamic>{
      ...state,
      ...changes,
      'updatedAt': DateTime.now().toIso8601String(),
    };
    final items = await _all();
    final index = items.indexWhere((e) => e['id']?.toString() == id);
    if (index >= 0) {
      items[index] = merged;
    } else {
      items.add(merged);
    }
    await _write(items);
    return FilmCreatorProject(merged);
  }
}
''')

write("film_creator_screen.dart", r'''import 'package:flutter/material.dart';
import 'film_creator_project.dart';
import 'screenplay_screen.dart';

class FilmCreatorScreen extends StatefulWidget {
  final String? projectId;
  const FilmCreatorScreen({super.key, this.projectId});
  @override State<FilmCreatorScreen> createState() => _FilmCreatorScreenState();
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

  final genres = const ['Action','Comedy','Drama','Horror','Romance','Sci-Fi','Fantasy','Thriller'];
  final styles = const ['Cinematic','Realistic','Animation','Anime','Fantasy','Vintage'];
  final aspects = const ['16:9','9:16','1:1'];

  @override
  void initState() {
    super.initState();
    projectId = widget.projectId;
    _load();
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

  Future<FilmCreatorProject> _save() async {
    setState(() => saving = true);
    final values = {
      'title': title.text.trim().isEmpty ? 'Untitled Film' : title.text.trim(),
      'idea': idea.text.trim(),
      'genre': genre,
      'length': length,
      'style': style,
      'aspectRatio': aspect,
      'status': 'draft',
    };
    final p = projectId == null
        ? await FilmCreatorProject.create(values)
        : await (await FilmCreatorProject.resume(projectId!))!.save(values);
    projectId = p.id;
    if (mounted) {
      setState(() => saving = false);
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Project saved on this device')));
    }
    return p;
  }

  Future<void> _generateScreenplay() async {
    final p = await _save();
    if (!mounted) return;
    await Navigator.push(context, MaterialPageRoute(builder: (_) => ScreenplayScreen(projectId: p.id)));
  }

  @override
  void dispose() {
    title.dispose();
    idea.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    if (loading) return const Scaffold(body: Center(child: CircularProgressIndicator()));
    return Scaffold(
      appBar: AppBar(
        title: const Text('Film Creator'),
        actions: [IconButton(onPressed: saving ? null : _save, icon: const Icon(Icons.save))],
      ),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Text('Create your film', style: Theme.of(context).textTheme.headlineMedium),
          const SizedBox(height: 8),
          const Text('Your Film Creator project is saved locally, so you can continue without the server.'),
          const SizedBox(height: 20),
          TextField(controller: title, decoration: const InputDecoration(labelText: 'Film title', border: OutlineInputBorder())),
          const SizedBox(height: 12),
          TextField(controller: idea, minLines: 5, maxLines: 9, decoration: const InputDecoration(labelText: 'What is your film about?', hintText: 'Describe the story, characters, setting and what you want to happen…', border: OutlineInputBorder())),
          const SizedBox(height: 16),
          DropdownButtonFormField<String>(
            value: genre,
            decoration: const InputDecoration(labelText: 'Genre', border: OutlineInputBorder()),
            items: genres.map((x) => DropdownMenuItem(value: x, child: Text(x))).toList(),
            onChanged: (v) { if (v != null) setState(() => genre = v); },
          ),
          const SizedBox(height: 12),
          DropdownButtonFormField<String>(
            value: style,
            decoration: const InputDecoration(labelText: 'Visual style', border: OutlineInputBorder()),
            items: styles.map((x) => DropdownMenuItem(value: x, child: Text(x))).toList(),
            onChanged: (v) { if (v != null) setState(() => style = v); },
          ),
          const SizedBox(height: 12),
          DropdownButtonFormField<int>(
            value: length,
            decoration: const InputDecoration(labelText: 'Film length (minutes)', border: OutlineInputBorder()),
            items: [1, 5, 10, 30, 60].map((x) => DropdownMenuItem(value: x, child: Text(x.toString() + ' minutes'))).toList(),
            onChanged: (v) { if (v != null) setState(() => length = v); },
          ),
          const SizedBox(height: 12),
          DropdownButtonFormField<String>(
            value: aspect,
            decoration: const InputDecoration(labelText: 'Aspect ratio', border: OutlineInputBorder()),
            items: aspects.map((x) => DropdownMenuItem(value: x, child: Text(x))).toList(),
            onChanged: (v) { if (v != null) setState(() => aspect = v); },
          ),
          const SizedBox(height: 24),
          FilledButton.icon(
            onPressed: saving ? null : _save,
            icon: saving ? const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2)) : const Icon(Icons.save),
            label: Text(saving ? 'SAVING…' : 'SAVE PROJECT'),
          ),
          const SizedBox(height: 10),
          FilledButton.icon(
            onPressed: saving ? null : _generateScreenplay,
            icon: const Icon(Icons.auto_awesome),
            label: const Text('GENERATE SCREENPLAY'),
          ),
        ],
      ),
    );
  }
}
''')

write("screenplay_screen.dart", r'''import 'package:flutter/material.dart';
import 'film_creator_project.dart';

class ScreenplayScreen extends StatefulWidget {
  final String projectId;
  const ScreenplayScreen({super.key, required this.projectId});
  @override State<ScreenplayScreen> createState() => _ScreenplayScreenState();
}

class _ScreenplayScreenState extends State<ScreenplayScreen> {
  FilmCreatorProject? project;
  String screenplay = '';
  bool loading = true;
  bool generating = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    project = await FilmCreatorProject.resume(widget.projectId);
    screenplay = project?.state['screenplay']?.toString() ?? '';
    if (mounted) setState(() => loading = false);
  }

  Future<void> _generate() async {
    final p = project ?? await FilmCreatorProject.resume(widget.projectId);
    if (p == null) return;
    setState(() => generating = true);
    final seed = p.idea.trim().isEmpty ? 'An unexpected event changes everything for the main character.' : p.idea.trim();
    final text = 'TITLE: ' + p.title + '\n'
        + 'GENRE: ' + p.genre + '\n'
        + 'STYLE: ' + p.style + '\n'
        + 'TARGET LENGTH: ' + p.length.toString() + ' MINUTES\n\n'
        + 'FADE IN:\n\n'
        + 'SCENE 1 — THE BEGINNING\nEXT. ESTABLISHING LOCATION — DAY\n\n'
        + 'The world is introduced through a strong cinematic image. The main character enters with a clear goal.\n\n'
        + 'STORY IDEA\n' + seed + '\n\n'
        + 'SCENE 2 — THE TURNING POINT\nINT. INTERIOR — DAY\n\n'
        + 'A new obstacle forces the protagonist to make a difficult choice. The stakes rise and the story moves into its central conflict.\n\n'
        + 'SCENE 3 — THE CLIMAX\nEXT. KEY LOCATION — NIGHT\n\n'
        + 'The conflict reaches its highest point. The protagonist acts and accepts the consequences of the choice.\n\n'
        + 'SCENE 4 — THE RESOLUTION\nEXT. FINAL IMAGE — DAWN\n\n'
        + 'The immediate conflict is resolved and the final image shows how the character and world have changed.\n\n'
        + 'FADE OUT.';
    project = await p.save({'screenplay': text, 'hasScreenplay': true, 'screenplayGeneratedAt': DateTime.now().toIso8601String()});
    screenplay = text;
    if (mounted) {
      setState(() => generating = false);
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Screenplay generated and saved locally')));
    }
  }

  @override
  Widget build(BuildContext context) {
    if (loading) return const Scaffold(body: Center(child: CircularProgressIndicator()));
    return Scaffold(
      appBar: AppBar(title: Text(project?.title ?? 'Screenplay')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Text('AI Screenplay', style: Theme.of(context).textTheme.headlineMedium),
          const SizedBox(height: 8),
          Text((project?.genre ?? 'Drama') + ' • ' + (project?.length.toString() ?? '5') + ' minutes • ' + (project?.style ?? 'Cinematic')),
          const SizedBox(height: 20),
          FilledButton.icon(
            onPressed: generating ? null : _generate,
            icon: generating ? const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2)) : const Icon(Icons.auto_awesome),
            label: Text(generating ? 'GENERATING…' : 'GENERATE SCREENPLAY'),
          ),
          const SizedBox(height: 16),
          screenplay.isEmpty
              ? const Card(child: Padding(padding: EdgeInsets.all(16), child: Text('Press Generate Screenplay to create the first draft.')))
              : SelectableText(screenplay, style: const TextStyle(fontSize: 16, height: 1.45)),
        ],
      ),
    );
  }
}
''')

write("film_projects_screen.dart", r'''import 'package:flutter/material.dart';
import 'film_creator_project.dart';
import 'film_creator_screen.dart';

class FilmProjectsScreen extends StatefulWidget {
  final void Function(FilmCreatorProject project)? onResume;
  const FilmProjectsScreen({super.key, this.onResume});
  @override State<FilmProjectsScreen> createState() => _FilmProjectsScreenState();
}

class _FilmProjectsScreenState extends State<FilmProjectsScreen> {
  List<FilmCreatorProject> projects = [];
  bool loading = true;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    final p = await FilmCreatorProject.all();
    if (mounted) setState(() { projects = p; loading = false; });
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('Film Projects')),
    floatingActionButton: FloatingActionButton.extended(
      onPressed: () => Navigator.push(context, MaterialPageRoute(builder: (_) => const FilmCreatorScreen())).then((_) => _load()),
      icon: const Icon(Icons.add),
      label: const Text('NEW FILM'),
    ),
    body: loading
        ? const Center(child: CircularProgressIndicator())
        : projects.isEmpty
            ? const Center(child: Text('No saved projects yet.'))
            : RefreshIndicator(
                onRefresh: _load,
                child: ListView.builder(
                  padding: const EdgeInsets.all(12),
                  itemCount: projects.length,
                  itemBuilder: (_, i) {
                    final p = projects[i];
                    final ready = p.state['hasScreenplay'] == true;
                    return Card(
                      child: ListTile(
                        leading: const Icon(Icons.movie_creation),
                        title: Text(p.title),
                        subtitle: Text(p.genre + ' • ' + (ready ? 'Screenplay ready' : 'Screenplay not generated')),
                        trailing: const Icon(Icons.chevron_right),
                        onTap: () {
                          if (widget.onResume != null) {
                            widget.onResume!(p);
                          } else {
                            Navigator.push(context, MaterialPageRoute(builder: (_) => FilmCreatorScreen(projectId: p.id))).then((_) => _load());
                          }
                        },
                      ),
                    );
                  },
                ),
              ),
  );
}
''')
print("v2592 Film Creator patch prepared")
