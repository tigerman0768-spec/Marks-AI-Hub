from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "app"
LIB = ROOT / "lib"

screen = r'''import 'dart:convert';
import 'dart:io';
import 'package:flutter/material.dart';
import 'package:path_provider/path_provider.dart';
import 'film_creator_project.dart';

class ClipLibraryScreen extends StatefulWidget {
  final String projectId;
  const ClipLibraryScreen({super.key, required this.projectId});
  @override State<ClipLibraryScreen> createState() => _ClipLibraryScreenState();
}

class _ClipLibraryScreenState extends State<ClipLibraryScreen> {
  FilmCreatorProject? project;
  List<Map<String,dynamic>> scenes = [];
  bool loading = true;
  final Set<int> downloading = {};

  String _outputUrl(Map<String,dynamic> scene) {
    final output = scene['output'];
    if (output is List && output.isNotEmpty) return output.first.toString();
    if (output is Map) {
      for (final key in ['url', 'videoUrl', 'uri']) {
        if (output[key] != null) return output[key].toString();
      }
    }
    final raw = output?.toString() ?? '';
    if (raw.startsWith('http://') || raw.startsWith('https://')) return raw;
    return '';
  }

  Future<void> _load() async {
    project = await FilmCreatorProject.resume(widget.projectId);
    final raw = project?.state['videoScenes'];
    if (raw is List) scenes = raw.whereType<Map>().map((e) => Map<String,dynamic>.from(e)).toList();
    if (mounted) setState(() => loading = false);
  }

  Future<void> _download(int index) async {
    final p = project;
    if (p == null || downloading.contains(index)) return;
    final scene = scenes[index];
    final url = _outputUrl(scene);
    if (url.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('No completed clip URL is available yet.')));
      return;
    }
    setState(() => downloading.add(index));
    try {
      final dir = await getApplicationDocumentsDirectory();
      final clips = Directory('${dir.path}/clips');
      await clips.create(recursive: true);
      final file = File('${clips.path}/scene_${scene['number'] ?? index + 1}.mp4');
      final client = HttpClient();
      final request = await client.getUrl(Uri.parse(url));
      final response = await request.close();
      if (response.statusCode < 200 || response.statusCode >= 300) {
        throw HttpException('HTTP ${response.statusCode}');
      }
      await response.pipe(file.openWrite());
      client.close(force: true);
      scene['localClipPath'] = file.path;
      scene['localClipSavedAt'] = DateTime.now().toIso8601String();
      project = await p.save({'videoScenes': scenes});
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Scene ${scene['number'] ?? index + 1} saved locally.')));
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Download failed: $e')));
    } finally {
      if (mounted) setState(() => downloading.remove(index));
    }
  }

  @override Widget build(BuildContext context) {
    if (loading) return const Scaffold(body: Center(child: CircularProgressIndicator()));
    final saved = scenes.where((s) => (s['localClipPath'] ?? '').toString().isNotEmpty).length;
    return Scaffold(
      appBar: AppBar(title: const Text('Clip Library')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Text('Saved clips: $saved of ${scenes.length}', style: Theme.of(context).textTheme.titleLarge),
          const SizedBox(height: 12),
          ...scenes.asMap().entries.map((entry) {
            final i = entry.key;
            final s = entry.value;
            final url = _outputUrl(s);
            final local = s['localClipPath']?.toString() ?? '';
            final busy = downloading.contains(i);
            return Card(child: ListTile(
              title: Text('Scene ${s['number'] ?? i + 1}'),
              subtitle: Text(local.isNotEmpty ? local : (url.isNotEmpty ? 'Generated clip ready' : 'Waiting for generated output')),
              trailing: busy
                ? const SizedBox(width: 28, height: 28, child: CircularProgressIndicator(strokeWidth: 2))
                : (url.isNotEmpty && local.isEmpty
                    ? IconButton(onPressed: () => _download(i), icon: const Icon(Icons.download))
                    : Icon(local.isNotEmpty ? Icons.check_circle : Icons.hourglass_empty)),
            ));
          }),
        ],
      ),
    );
  }
}
'''

(LIB / "clip_library_screen.dart").write_text(screen, encoding="utf-8")

status = LIB / "video_generation_status_screen.dart"
if status.exists():
    text = status.read_text(encoding="utf-8")
    if "clip_library_screen.dart" not in text:
        text = text.replace("import 'film_creator_project.dart';", "import 'film_creator_project.dart';\nimport 'clip_library_screen.dart';")
    needle = "actions: [IconButton(onPressed: polling ? null : _poll, icon: const Icon(Icons.refresh))]"
    repl = "actions: [IconButton(onPressed: polling ? null : _poll, icon: const Icon(Icons.refresh)), IconButton(onPressed: () => Navigator.push(context, MaterialPageRoute(builder: (_) => ClipLibraryScreen(projectId: widget.projectId))), icon: const Icon(Icons.video_library))]"
    if "Icons.video_library" not in text:
        text = text.replace(needle, repl)
    status.write_text(text, encoding="utf-8")
else:
    raise SystemExit("video_generation_status_screen.dart is not present; run v2594 patch first")

