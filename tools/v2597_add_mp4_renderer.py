from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "app"
LIB = ROOT / "lib"

pubspec = ROOT / "pubspec.yaml"
content = pubspec.read_text(encoding="utf-8")
if "ffmpeg_kit_flutter_new_min:" not in content:
    marker = "  video_player: ^2.9.5"
    if marker not in content:
        raise SystemExit("Expected video_player dependency not found")
    content = content.replace(marker, marker + "\n  # LGPL-only FFmpeg build for local MP4 assembly.\n  ffmpeg_kit_flutter_new_min: ^3.6.7")
    pubspec.write_text(content, encoding="utf-8")

screen = r'''import 'dart:io';
import 'package:flutter/material.dart';
import 'package:path_provider/path_provider.dart';
import 'package:share_plus/share_plus.dart';
import 'package:ffmpeg_kit_flutter_new_min/ffmpeg_kit.dart';
import 'package:ffmpeg_kit_flutter_new_min/return_code.dart';
import 'film_creator_project.dart';

class FilmAssemblyScreen extends StatefulWidget {
  final String projectId;
  const FilmAssemblyScreen({super.key, required this.projectId});
  @override State<FilmAssemblyScreen> createState() => _FilmAssemblyScreenState();
}

class _FilmAssemblyScreenState extends State<FilmAssemblyScreen> {
  FilmCreatorProject? project;
  List<Map<String, dynamic>> scenes = [];
  bool loading = true, rendering = false;
  String status = '';
  String? outputPath, errorText;

  @override
  void initState() { super.initState(); _load(); }

  Future<void> _load() async {
    project = await FilmCreatorProject.resume(widget.projectId);
    final raw = project?.state['videoScenes'];
    if (raw is List) {
      scenes = raw.whereType<Map>().map((e) => Map<String, dynamic>.from(e)).toList();
      scenes.sort((a, b) => ((a['number'] ?? 0) as num).compareTo((b['number'] ?? 0) as num));
    }
    outputPath = project?.state['finalFilmPath']?.toString();
    if (outputPath != null && !File(outputPath!).existsSync()) outputPath = null;
    if (mounted) setState(() => loading = false);
  }

  String _shellQuote(String value) => "'" + value.replaceAll("'", "'\\''") + "'";

  Future<void> _render() async {
    if (rendering) return;
    final p = project;
    if (p == null) { setState(() => errorText = 'Film project could not be loaded.'); return; }
    if (scenes.isEmpty) { setState(() => errorText = 'There are no planned scenes to assemble.'); return; }

    final ordered = <Map<String, dynamic>>[];
    for (var i = 0; i < scenes.length; i++) {
      final scene = scenes[i];
      final path = scene['localClipPath']?.toString() ?? '';
      if (path.isEmpty || !await File(path).exists()) {
        setState(() => errorText = 'Scene ' + (scene['number'] ?? i + 1).toString() + ' is missing. Download every generated MP4 first.');
        return;
      }
      ordered.add(scene);
    }

    setState(() { rendering = true; errorText = null; status = 'Preparing ordered scene list…'; });
    try {
      final docs = await getApplicationDocumentsDirectory();
      final filmsDir = Directory(docs.path + '/films');
      await filmsDir.create(recursive: true);
      final stamp = DateTime.now().millisecondsSinceEpoch;
      final listFile = File(filmsDir.path + '/concat_' + stamp.toString() + '.txt');
      final lines = ordered.map((s) => "file '" + s['localClipPath'].toString().replaceAll("'", "'\\''") + "'").join('\n');
      await listFile.writeAsString(lines + '\n', flush: true);
      final title = (p.title.trim().isEmpty ? 'my_film' : p.title.trim()).replaceAll(RegExp(r'[^A-Za-z0-9_-]+'), '_');
      final out = File(filmsDir.path + '/' + title + '_' + stamp.toString() + '.mp4');

      setState(() => status = 'Joining ' + ordered.length.toString() + ' clips into one MP4…');
      final command = '-y -f concat -safe 0 -i ' + _shellQuote(listFile.path) +
          ' -c copy -movflags +faststart ' + _shellQuote(out.path);
      final session = await FFmpegKit.execute(command);
      final rc = await session.getReturnCode();
      if (!ReturnCode.isSuccess(rc) || !await out.exists() || await out.length() < 1024) {
        final logs = (await session.getOutput()) ?? '';
        if (await out.exists()) await out.delete();
        final tail = logs.length > 700 ? logs.substring(logs.length - 700) : logs;
        throw Exception('Clips could not be joined without re-encoding. Check that they have compatible formats. ' + tail);
      }

      project = await p.save({
        'finalFilmPath': out.path,
        'finalFilmRenderedAt': DateTime.now().toIso8601String(),
        'finalFilmSceneCount': ordered.length,
        'filmAssembly': {
          'status': 'RENDERED',
          'outputPath': out.path,
          'orderedScenes': ordered.map((s) => {'scene': s['number'], 'path': s['localClipPath'], 'status': 'READY'}).toList(),
          'sceneCount': ordered.length,
          'readyCount': ordered.length,
          'createdAt': DateTime.now().toIso8601String(),
        }
      });
      if (mounted) setState(() { outputPath = out.path; status = 'Finished MP4 created successfully.'; });
    } catch (e) {
      if (mounted) setState(() => errorText = e.toString());
    } finally {
      if (mounted) setState(() => rendering = false);
    }
  }

  Future<void> _share() async {
    final path = outputPath;
    if (path != null && await File(path).exists()) {
      await Share.shareXFiles([XFile(path)], text: 'Created with Mark’s AI Film Studio');
    }
  }

  @override
  Widget build(BuildContext context) {
    if (loading) return const Scaffold(body: Center(child: CircularProgressIndicator()));
    final ready = scenes.where((s) {
      final path = s['localClipPath']?.toString() ?? '';
      return path.isNotEmpty && File(path).existsSync();
    }).length;
    final hasFilm = outputPath != null && File(outputPath!).existsSync();
    return Scaffold(
      appBar: AppBar(title: const Text('Film Assembly')),
      body: ListView(padding: const EdgeInsets.all(16), children: [
        Text('Create your finished film', style: Theme.of(context).textTheme.headlineSmall),
        const SizedBox(height: 8),
        Text(ready.toString() + ' of ' + scenes.length.toString() + ' scene clips are downloaded.'),
        const SizedBox(height: 12),
        LinearProgressIndicator(value: scenes.isEmpty ? 0 : ready / scenes.length),
        const SizedBox(height: 16),
        ...scenes.asMap().entries.map((entry) {
          final i = entry.key, s = entry.value;
          final path = s['localClipPath']?.toString() ?? '';
          final exists = path.isNotEmpty && File(path).existsSync();
          return Card(child: ListTile(
            leading: CircleAvatar(child: Text((i + 1).toString())),
            title: Text('Scene ' + (s['number'] ?? i + 1).toString()),
            subtitle: Text(exists ? 'Downloaded MP4 ready' : 'Clip missing — download it first'),
            trailing: Icon(exists ? Icons.check_circle : Icons.warning_amber_rounded),
          ));
        }),
        const SizedBox(height: 12),
        FilledButton.icon(
          onPressed: rendering || scenes.isEmpty || ready != scenes.length ? null : _render,
          icon: rendering ? const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2)) : const Icon(Icons.movie_creation),
          label: Text(rendering ? 'RENDERING…' : 'RENDER FINISHED MP4'),
        ),
        if (rendering || status.isNotEmpty) ...[const SizedBox(height: 10), Text(status)],
        if (errorText != null) ...[const SizedBox(height: 10), Text(errorText!, style: TextStyle(color: Theme.of(context).colorScheme.error))],
        if (hasFilm) ...[
          const SizedBox(height: 16),
          const ListTile(leading: Icon(Icons.check_circle, color: Colors.green), title: Text('Finished film saved'), subtitle: Text('One MP4 is stored in the app films folder.')),
          SelectableText(outputPath!),
          OutlinedButton.icon(onPressed: _share, icon: const Icon(Icons.share), label: const Text('SHARE / EXPORT FILM')),
        ],
        const SizedBox(height: 8),
        const Text('This first renderer joins compatible MP4 clips without re-encoding. If the provider returns incompatible formats, an error is shown rather than claiming a film was made.'),
      ]),
    );
  }
}
'''
(LIB / "film_assembly_screen.dart").write_text(screen, encoding="utf-8")

status = LIB / "video_generation_status_screen.dart"
text = status.read_text(encoding="utf-8")
if "film_assembly_screen.dart" not in text:
    text = text.replace("import 'clip_library_screen.dart';", "import 'clip_library_screen.dart';\nimport 'film_assembly_screen.dart';")
if "FilmAssemblyScreen(projectId: widget.projectId)" not in text:
    needle = "actions: [IconButton(onPressed: polling ? null : _poll, icon: const Icon(Icons.refresh))]"
    repl = needle[:-1] + ", IconButton(onPressed: () => Navigator.push(context, MaterialPageRoute(builder: (_) => FilmAssemblyScreen(projectId: widget.projectId))), icon: const Icon(Icons.movie_creation))]"
    if needle not in text:
        raise SystemExit("Could not locate Clip Progress action bar")
    text = text.replace(needle, repl)
status.write_text(text, encoding="utf-8")
