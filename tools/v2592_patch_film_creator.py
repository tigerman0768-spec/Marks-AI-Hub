undefined

# v2594: persistent video generation status/retrieval screen.
write("video_generation_status_screen.dart", r'''import 'dart:convert';
import 'dart:io';
import 'package:flutter/material.dart';
import 'film_creator_project.dart';

class VideoGenerationStatusScreen extends StatefulWidget {
  final String projectId;
  const VideoGenerationStatusScreen({super.key, required this.projectId});
  @override State<VideoGenerationStatusScreen> createState() => _VideoGenerationStatusScreenState();
}

class _VideoGenerationStatusScreenState extends State<VideoGenerationStatusScreen> {
  FilmCreatorProject? project;
  List<Map<String,dynamic>> scenes = [];
  bool loading = true;
  bool busy = false;
  String endpoint = '';

  @override void initState() { super.initState(); _load(); }

  Future<void> _load() async {
    project = await FilmCreatorProject.resume(widget.projectId);
    final saved = project?.state['videoScenes'];
    if (saved is List) scenes = saved.whereType<Map>().map((e) => Map<String,dynamic>.from(e)).toList();
    endpoint = project?.state['videoGenerationEndpoint']?.toString() ?? '';
    if (mounted) setState(() => loading = false);
  }

  String _status(Map<String,dynamic> s) {
    final x = (s['status'] ?? 'READY').toString().toUpperCase();
    if (x == 'SUCCEEDED' || x == 'COMPLETED') return 'COMPLETED';
    if (x == 'FAILED' || x == 'ERROR') return 'FAILED';
    if ((s['jobId'] ?? '').toString().isNotEmpty) return x;
    return 'READY';
  }

  Future<void> _poll() async {
    if (endpoint.isEmpty) return;
    setState(() => busy = true);
    final client = HttpClient();
    try {
      for (final scene in scenes) {
        final job = scene['jobId']?.toString() ?? '';
        if (job.isEmpty || _status(scene) == 'COMPLETED') continue;
        final url = endpoint.replaceFirst(RegExp(r'/generate/?$'), '/status/') + Uri.encodeComponent(job);
        final request = await client.getUrl(Uri.parse(url));
        final response = await request.close();
        final body = await utf8.decoder.bind(response).join();
        if (response.statusCode < 200 || response.statusCode >= 300) {
          scene['status'] = 'FAILED';
          scene['error'] = 'HTTP ' + response.statusCode.toString();
          continue;
        }
        final data = jsonDecode(body);
        if (data is Map) {
          scene['status'] = data['status']?.toString() ?? scene['status'] ?? 'PENDING';
          if (data['output'] != null) scene['output'] = data['output'];
          if (data['failure'] != null) scene['error'] = data['failure'];
        }
      }
      project = await project!.save({'videoScenes': scenes, 'videoGenerationLastPolledAt': DateTime.now().toIso8601String()});
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Status check failed: ' + e.toString())));
    } finally {
      client.close(force: true);
      if (mounted) setState(() => busy = false);
    }
  }

  Future<void> _retry(Map<String,dynamic> scene) async {
    if (endpoint.isEmpty) return;
    setState(() => busy = true);
    final client = HttpClient();
    try {
      final request = await client.postUrl(Uri.parse(endpoint));
      request.headers.contentType = ContentType.json;
      request.add(utf8.encode(jsonEncode({'project': project!.state, 'scene': scene, 'provider': 'backend'})));
      final response = await request.close();
      final body = await utf8.decoder.bind(response).join();
      if (response.statusCode < 200 || response.statusCode >= 300) throw HttpException('HTTP ' + response.statusCode.toString());
      final data = jsonDecode(body);
      if (data is Map) {
        scene['status'] = data['status']?.toString() ?? 'PENDING';
        scene['jobId'] = data['jobId']?.toString() ?? '';
        scene.remove('error');
        scene.remove('output');
      }
      project = await project!.save({'videoScenes': scenes});
    } catch (e) {
      scene['status'] = 'FAILED';
      scene['error'] = e.toString();
    } finally {
      client.close(force: true);
      if (mounted) setState(() => busy = false);
    }
  }

  @override Widget build(BuildContext context) {
    if (loading) return const Scaffold(body: Center(child: CircularProgressIndicator()));
    final completed = scenes.where((s) => _status(s) == 'COMPLETED').length;
    return Scaffold(
      appBar: AppBar(title: const Text('Video Generation'), actions: [IconButton(onPressed: busy ? null : _poll, icon: const Icon(Icons.refresh))]),
      body: ListView(padding: const EdgeInsets.all(16), children: [
        Text('Clip progress', style: Theme.of(context).textTheme.headlineMedium),
        const SizedBox(height: 6),
        Text(completed.toString() + ' of ' + scenes.length.toString() + ' scenes completed'),
        const SizedBox(height: 10),
        LinearProgressIndicator(value: scenes.isEmpty ? 0 : completed / scenes.length),
        const SizedBox(height: 12),
        FilledButton.icon(onPressed: busy ? null : _poll, icon: const Icon(Icons.sync), label: Text(busy ? 'CHECKING…' : 'CHECK GENERATION STATUS')),
        const SizedBox(height: 12),
        ...scenes.map((s) => Card(child: Padding(padding: const EdgeInsets.all(12), child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text('Scene ' + (s['number']?.toString() ?? '?'), style: const TextStyle(fontWeight: FontWeight.bold)),
          Text('Status: ' + _status(s)),
          if ((s['jobId'] ?? '').toString().isNotEmpty) Text('Job: ' + s['jobId'].toString()),
          if (s['output'] != null) SelectableText('Video output: ' + s['output'].toString()),
          if (s['error'] != null) ...[
            Text('Error: ' + s['error'].toString()),
            OutlinedButton.icon(onPressed: busy ? null : () => _retry(s), icon: const Icon(Icons.refresh), label: const Text('RETRY SCENE')),
          ],
        ])))),
      ]),
    );
  }
}
''');

final sceneFile = LIB / "scene_prompt_screen.dart";
var sceneText = sceneFile.read_text(encoding="utf-8");
if ("video_generation_status_screen.dart" not in sceneText) {
  sceneText = sceneText.replace("import 'film_creator_project.dart';", "import 'film_creator_project.dart';\nimport 'video_generation_status_screen.dart';", 1);
}
const oldButton = "OutlinedButton.icon(\n            onPressed: saving ? null : _submitToBackend,\n            icon: const Icon(Icons.movie),\n            label: const Text('GENERATE VIDEO CLIPS'),\n          ),";
const newButton = oldButton + "\n          const SizedBox(height: 8),\n          OutlinedButton.icon(\n            onPressed: saving ? null : () => Navigator.push(context, MaterialPageRoute(builder: (_) => VideoGenerationStatusScreen(projectId: widget.projectId))).then((_) => _load()),\n            icon: const Icon(Icons.track_changes),\n            label: const Text('VIEW CLIP PROGRESS'),\n          ),";
if (sceneText.contains(oldButton)) sceneText = sceneText.replace(oldButton, newButton);
sceneFile.write_text(sceneText, encoding="utf-8");
print("v2594 video generation status screen added");
