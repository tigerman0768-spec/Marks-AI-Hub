from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "app"
LIB = ROOT / "lib"

screen = r'''import 'dart:io';
import 'package:flutter/material.dart';
import 'film_creator_project.dart';

class FilmAssemblyScreen extends StatefulWidget {
  final String projectId;
  const FilmAssemblyScreen({super.key, required this.projectId});
  @override State<FilmAssemblyScreen> createState() => _FilmAssemblyScreenState();
}

class _FilmAssemblyScreenState extends State<FilmAssemblyScreen> {
  FilmCreatorProject? project;
  List<Map<String,dynamic>> scenes = [];
  bool loading = true;
  bool saving = false;

  @override void initState() { super.initState(); _load(); }

  Future<void> _load() async {
    project = await FilmCreatorProject.resume(widget.projectId);
    final raw = project?.state['videoScenes'];
    if (raw is List) {
      scenes = raw.whereType<Map>().map((e) => Map<String,dynamic>.from(e)).toList();
      scenes.sort((a,b) => ((a['number'] ?? 0) as num).compareTo((b['number'] ?? 0) as num));
    }
    if (mounted) setState(() => loading = false);
  }

  Future<void> _saveAssembly() async {
    final p = project;
    if (p == null) return;
    setState(() => saving = true);
    final clips = scenes.map((s) => {
      'scene': s['number'],
      'path': s['localClipPath'],
      'status': (s['localClipPath'] ?? '').toString().isEmpty ? 'MISSING' : 'READY',
    }).toList();
    await p.save({
      'filmAssembly': {
        'status': 'READY_FOR_RENDER',
        'orderedScenes': clips,
        'sceneCount': scenes.length,
        'readyCount': clips.where((c) => c['status'] == 'READY').length,
        'createdAt': DateTime.now().toIso8601String(),
      }
    });
    if (mounted) {
      setState(() => saving = false);
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Film assembly order saved.')));
    }
  }

  @override Widget build(BuildContext context) {
    if (loading) return const Scaffold(body: Center(child: CircularProgressIndicator()));
    final ready = scenes.where((s) {
      final path = s['localClipPath']?.toString() ?? '';
      return path.isNotEmpty && File(path).existsSync();
    }).length;
    return Scaffold(
      appBar: AppBar(title: const Text('Film Assembly')),
      body: ListView(padding: const EdgeInsets.all(16), children: [
        Text('Film Assembly', style: Theme.of(context).textTheme.headlineMedium),
        const SizedBox(height: 8),
        Text('${ready} of ${scenes.length} scene clips are ready for assembly.'),
        const SizedBox(height: 14),
        LinearProgressIndicator(value: scenes.isEmpty ? 0 : ready / scenes.length),
        const SizedBox(height: 18),
        ...scenes.asMap().entries.map((entry) {
          final i=entry.key; final s=entry.value;
          final path=s['localClipPath']?.toString() ?? '';
          final exists=path.isNotEmpty && File(path).existsSync();
          return Card(child: ListTile(
            leading: CircleAvatar(child: Text('${i+1}')),
            title: Text('Scene ${s['number'] ?? i+1}'),
            subtitle: Text(exists ? 'Ready' : 'Clip not downloaded'),
            trailing: Icon(exists ? Icons.check_circle : Icons.hourglass_empty),
          ));
        }),
        const SizedBox(height: 18),
        FilledButton.icon(
          onPressed: saving || scenes.isEmpty ? null : _saveAssembly,
          icon: const Icon(Icons.movie_creation),
          label: Text(saving ? 'SAVING…' : 'SAVE ASSEMBLY ORDER'),
        ),
        const SizedBox(height: 8),
        const Text('The next render layer will concatenate the ordered MP4 clips into the finished film while preserving the selected project aspect ratio.'),
      ]),
    );
  }
}
'''
(LIB / "film_assembly_screen.dart").write_text(screen, encoding="utf-8")

status = LIB / "video_generation_status_screen.dart"
text = status.read_text(encoding="utf-8")
if "film_assembly_screen.dart" not in text:
    text=text.replace("import 'clip_library_screen.dart';","import 'clip_library_screen.dart';\nimport 'film_assembly_screen.dart';")
if "Icons.movie_creation" not in text:
    old="IconButton(onPressed: () => Navigator.push(context, MaterialPageRoute(builder: (_) => ClipLibraryScreen(projectId: widget.projectId))), icon: const Icon(Icons.video_library))"
    new=old+", IconButton(onPressed: () => Navigator.push(context, MaterialPageRoute(builder: (_) => FilmAssemblyScreen(projectId: widget.projectId))), icon: const Icon(Icons.movie_creation))"
    text=text.replace(old,new)
status.write_text(text, encoding="utf-8")
