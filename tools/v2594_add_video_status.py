from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "app"
LIB = ROOT / "lib"

status_screen = r'''import 'dart:convert';
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
  bool polling = false;

  @override void initState() { super.initState(); _load(); }

  Future<void> _load() async {
    project = await FilmCreatorProject.resume(widget.projectId);
    final raw = project?.state['videoScenes'];
    if (raw is List) scenes = raw.whereType<Map>().map((e) => Map<String,dynamic>.from(e)).toList();
    if (mounted) setState(() => loading = false);
    if (scenes.any((s) => _status(s) == 'PENDING')) _poll();
  }

  String _status(Map<String,dynamic> s) {
    final value = (s['status'] ?? 'READY').toString().toUpperCase();
    if (value.contains('COMPLETE')) return 'COMPLETED';
    if (value.contains('FAIL')) return 'FAILED';
    if (value == 'PENDING' || value == 'SUBMITTED' || value == 'RUNNING' || value == 'IN_PROGRESS') return 'PENDING';
    return value == 'READY' ? 'READY' : value;
  }

  String _baseStatusEndpoint() {
    final raw = project?.state['videoGenerationEndpoint']?.toString() ?? '';
    if (raw.endsWith('/generate')) return raw.substring(0, raw.length - '/generate'.length);
    return raw.endsWith('/') ? raw.substring(0, raw.length - 1) : raw;
  }

  Future<void> _poll() async {
    if (polling) return;
    polling = true;
    try {
      final base = _baseStatusEndpoint();
      if (base.isEmpty) {
        if (mounted) ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Video generation service is not configured. Add a real backend URL in Film Creator settings.')));
        return;
      }
      for (final scene in scenes) {
        final job = scene['jobId']?.toString() ?? '';
        if (job.isEmpty || _status(scene) != 'PENDING') continue;
        try {
          final client = HttpClient();
          final request = await client.getUrl(Uri.parse(base + '/status/' + Uri.encodeComponent(job)));
          final response = await request.close();
          final body = await utf8.decoder.bind(response).join();
          client.close(force: true);
          if (response.statusCode >= 200 && response.statusCode < 300) {
            final data = jsonDecode(body);
            if (data is Map) {
              scene['status'] = data['status']?.toString() ?? scene['status'];
              if (data['output'] != null) scene['output'] = data['output'];
              if (data['failure'] != null) scene['failure'] = data['failure'];
            }
          }
        } catch (_) {}
      }
      final p = project;
      if (p != null) project = await p.save({'videoScenes': scenes});
      if (mounted) setState(() {});
    } finally {
      polling = false;
    }
  }

  Future<void> _retry(int index) async {
    final p = project;
    if (p == null) return;
    final endpoint = p.state['videoGenerationEndpoint']?.toString() ?? '';
    if (endpoint.isEmpty) {
      scene['status'] = 'FAILED';
      scene['failure'] = 'Video generation service is not configured. Add a real backend URL in Film Creator settings.';
      if (mounted) {
        setState(() {});
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Video generation service is not configured.')));
      }
      return;
    }
    final scene = scenes[index];
    setState(() => scene['status'] = 'PENDING');
    try {
      final client = HttpClient();
      final request = await client.postUrl(Uri.parse(endpoint));
      request.headers.contentType = ContentType.json;
      request.add(utf8.encode(jsonEncode({'project': p.state, 'scene': scene, 'provider': 'backend'})));
      final response = await request.close();
      final body = await utf8.decoder.bind(response).join();
      client.close(force: true);
      if (response.statusCode < 200 || response.statusCode >= 300) throw HttpException('HTTP ' + response.statusCode.toString());
      final data = jsonDecode(body);
      if (data is Map && data['jobId'] != null) scene['jobId'] = data['jobId'].toString();
      scene['status'] = data is Map ? (data['status']?.toString() ?? 'PENDING') : 'PENDING';
      scene.remove('failure');
      project = await p.save({'videoScenes': scenes});
      if (mounted) setState(() {});
      _poll();
    } catch (e) {
      scene['status'] = 'FAILED';
      scene['failure'] = e.toString();
      if (mounted) setState(() {});
    }
  }

  @override Widget build(BuildContext context) {
    if (loading) return const Scaffold(body: Center(child: CircularProgressIndicator()));
    final complete = scenes.where((s) => _status(s) == 'COMPLETED').length;
    final failed = scenes.where((s) => _status(s) == 'FAILED').length;
    return Scaffold(
      appBar: AppBar(title: const Text('Clip Progress'), actions: [IconButton(onPressed: polling ? null : _poll, icon: const Icon(Icons.refresh))]),
      body: ListView(padding: const EdgeInsets.all(16), children: [
        Text('AI video clips', style: Theme.of(context).textTheme.headlineMedium),
        const SizedBox(height: 8),
        Text('$complete of ${scenes.length} clips completed${failed > 0 ? ' • $failed failed' : ''}'),
        const SizedBox(height: 10),
        LinearProgressIndicator(value: scenes.isEmpty ? 0 : complete / scenes.length),
        const SizedBox(height: 18),
        ...scenes.asMap().entries.map((entry) {
          final i = entry.key; final s = entry.value; final state = _status(s);
          final output = s['output']?.toString() ?? '';
          return Card(child: Padding(padding: const EdgeInsets.all(12), child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text('Scene ${s['number'] ?? i + 1}', style: const TextStyle(fontWeight: FontWeight.bold)),
            const SizedBox(height: 6),
            Text(state),
            if (s['jobId'] != null) Text('Job: ${s['jobId']}'),
            if (output.isNotEmpty) SelectableText('Output: $output'),
            if (s['failure'] != null) Text('Error: ${s['failure']}'),
            if (state == 'FAILED') Align(alignment: Alignment.centerRight, child: TextButton.icon(onPressed: () => _retry(i), icon: const Icon(Icons.refresh), label: const Text('RETRY'))),
          ])));
        }),
      ]),
    );
  }
}
'''

(LIB / "video_generation_status_screen.dart").write_text(status_screen, encoding="utf-8")

scene = LIB / "scene_prompt_screen.dart"
text = scene.read_text(encoding="utf-8")
if "video_generation_status_screen.dart" not in text:
    text = text.replace("import 'film_creator_project.dart';", "import 'film_creator_project.dart\\nimport 'video_generation_status_screen.dart';")
needle = "label: const Text('GENERATE VIDEO CLIPS'),\\n          ),"
replacement = "label: const Text('GENERATE VIDEO CLIPS'),\\n          ),\\n          const SizedBox(height: 10),\\n          OutlinedButton.icon(onPressed: saving ? null : () => Navigator.push(context, MaterialPageRoute(builder: (_) => VideoGenerationStatusScreen(projectId: widget.projectId))), icon: const Icon(Icons.track_changes), label: const Text('VIEW CLIP PROGRESS')), "
if "VIEW CLIP PROGRESS" not in text:
    text = text.replace(needle, replacement)
# Fix accidental escaping that displayed Dart interpolation literally (for example ${scenes.length}).
text = text.replace(r"\$", "$")
scene.write_text(text, encoding="utf-8")
