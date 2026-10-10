from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1] / "app" / "lib"
p = ROOT / "scene_prompt_screen.dart"
if not p.exists():
    raise SystemExit("scene_prompt_screen.dart not found")
s = p.read_text(encoding="utf-8")
if "Future<void> _pollAndDownload" in s:
    print("v2605 async download repair already applied")
    raise SystemExit(0)
if "package:path_provider/path_provider.dart" not in s:
    s = s.replace("import 'package:flutter/material.dart';", "import 'package:path_provider/path_provider.dart';\nimport 'package:flutter/material.dart';")
start = s.index("  Future<void> _submitToBackend() async {")
end = s.index("\n  Future<void> _prepare() async {", start)
method = r'''  Future<void> _submitToBackend() async {
    final p = project;
    if (p == null || scenes.isEmpty) return;
    final endpoint = await showDialog<String>(
      context: context,
      builder: (context) {
        final controller = TextEditingController(text: p.state['videoGenerationEndpoint']?.toString() ?? '');
        return AlertDialog(
          title: const Text('Video generation backend'),
          content: TextField(controller: controller, decoration: const InputDecoration(hintText: 'https://your-domain/api/video/generate')),
          actions: [
            TextButton(onPressed: () => Navigator.pop(context), child: const Text('CANCEL')),
            FilledButton(onPressed: () => Navigator.pop(context, controller.text.trim()), child: const Text('USE')),
          ],
        );
      },
    );
    if (endpoint == null || endpoint.isEmpty) return;
    final uri = Uri.tryParse(endpoint);
    if (uri == null || !uri.hasScheme || uri.host.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Enter a valid backend URL')));
      return;
    }
    setState(() => saving = true);
    final client = HttpClient();
    var downloaded = 0;
    var failed = 0;
    try {
      for (var i = 0; i < scenes.length; i++) {
        final scene = scenes[i];
        scene['status'] = 'submitting';
        if (mounted) setState(() {});
        // Reuse a saved provider task after timeout/app restart. Never submit
        // another paid generation request when this scene already has a job ID.
        var task = scene['jobId']?.toString();
        if (task == null || task.isEmpty) {
        // Bound submission time so a stalled backend cannot freeze the
        // entire scene queue indefinitely.
        final req = await client.postUrl(uri).timeout(const Duration(seconds: 30));
        req.headers.contentType = ContentType.json;
        req.add(utf8.encode(jsonEncode({
          'project': p.state, 'scene': scene, 'prompt': scene['prompt'],
          'durationSeconds': scene['durationSeconds'] ?? 8,
          'aspectRatio': p.aspectRatio, 'provider': 'backend',
        })));
        final res = await req.close().timeout(const Duration(seconds: 60));
        final body = await utf8.decoder.bind(res).join().timeout(const Duration(seconds: 45));
        if (res.statusCode < 200 || res.statusCode >= 300) {
          scene['status'] = 'failed';
          scene['error'] = 'Generate request HTTP ' + res.statusCode.toString();
          failed++;
          await _saveSceneState(p);
          continue;
        }
        final dynamic data = jsonDecode(body);
        final newTask = data is Map ? (data['taskId'] ?? data['jobId'] ?? data['id'])?.toString() : null;
        if (newTask == null || newTask.isEmpty) {
          final direct = data is Map ? (data['videoUrl'] ?? data['url'] ?? data['output']) : null;
          if (direct is String && direct.startsWith('http')) {
            scene['localClipPath'] = await _downloadGeneratedClip(client, Uri.parse(direct), i + 1);
            scene['status'] = 'downloaded';
            scene['downloadedAt'] = DateTime.now().toIso8601String();
            scene.remove('error');
            scene.remove('failureCode');
            scene.remove('failureMessage');
            scene.remove('lastStatusError');
            scene.remove('downloadFailureAt');
            scene.remove('downloadFailureType');
            downloaded++;
          } else {
            scene['status'] = 'failed';
            scene['error'] = 'No task ID or video URL returned';
            failed++;
          }
          await _saveSceneState(p);
          continue;
        }
        task = newTask;
        scene['jobId'] = task;
        scene['status'] = 'queued';
        await _saveSceneState(p);
        }
        final activeTask = task!;
        var finished = false;
        for (var attempt = 0; attempt < 180; attempt++) {
          await Future.delayed(const Duration(seconds: 5));
          final statusPath = uri.path.endsWith('/api/video/generate')
              ? uri.path.substring(0, uri.path.length - '/generate'.length) + '/status/' + Uri.encodeComponent(activeTask)
              : '/api/video/status/' + Uri.encodeComponent(activeTask);
          final statusUri = uri.replace(path: statusPath, query: null, fragment: null);
          HttpClientResponse statusRes;
          String statusBody;
          try {
            final statusRequest = await client.getUrl(statusUri).timeout(const Duration(seconds: 30));
            statusRes = await statusRequest.close().timeout(const Duration(seconds: 45));
            statusBody = await utf8.decoder.bind(statusRes).join().timeout(const Duration(seconds: 30));
          } catch (e) {
            // A temporary network hiccup must not abandon the entire film job.
            scene['status'] = 'waiting_for_status';
            scene['lastStatusError'] = e.toString();
            if (attempt % 6 == 0) await _saveSceneState(p);
            if (mounted) setState(() {});
            continue;
          }
          if (statusRes.statusCode < 200 || statusRes.statusCode >= 300) {
            final code = statusRes.statusCode;
            // Retry temporary failures against the same task instead of
            // abandoning a scene that may still be generating.
            if (code == 408 || code == 425 || code == 429 || code >= 500) {
              scene['status'] = 'waiting_for_status';
              scene['lastStatusError'] = 'Status check HTTP ' + code.toString();
              if (attempt % 6 == 0) await _saveSceneState(p);
              if (mounted) setState(() {});
              continue;
            }
            scene['status'] = 'failed';
            scene['error'] = 'Status check HTTP ' + code.toString();
            try {
              final dynamic errorData = jsonDecode(statusBody);
              if (errorData is Map) {
                scene['failureCode'] = errorData['failureCode'] ?? errorData['failure_code'] ?? errorData['code'];
                scene['failureMessage'] = errorData['failureMessage'] ?? errorData['failure_message'] ?? errorData['error'] ?? errorData['message'];
              }
            } catch (_) {
              // Keep the HTTP status as the fallback if the backend returns
              // a non-JSON error body.
            }
            failed++;
            finished = true;
            break;
          }
          final dynamic status = jsonDecode(statusBody);
          final state = status is Map ? (status['status'] ?? status['state'] ?? '').toString().toLowerCase() : '';
          if (state == 'failed' || state == 'error' || state == 'cancelled' || state == 'canceled') {
            scene['status'] = 'failed';
            scene['error'] = status is Map ? (status['failureMessage'] ?? status['failure_message'] ?? status['failure'] ?? status['error'] ?? 'Generation failed').toString() : 'Generation failed';
            scene['failureCode'] = status is Map ? (status['failureCode'] ?? status['failure_code'] ?? status['code']) : null;
            scene['failureMessage'] = status is Map ? (status['failureMessage'] ?? status['failure_message'] ?? status['failure'] ?? status['error'] ?? status['message']) : null;
            failed++;
            finished = true;
            break;
          }
          final dynamic output = status is Map ? (status['output'] ?? status['outputs'] ?? status['videoUrl'] ?? status['url']) : null;
          final videoUrl = _findVideoUrl(output);
          final isSuccessfulState = state == 'succeeded' || state == 'success' || state == 'completed' || state == 'complete';
          if (isSuccessfulState && videoUrl == null) {
            scene['status'] = 'failed';
            scene['error'] = 'Provider marked generation successful but returned no usable video URL';
            scene['failureCode'] = status is Map ? (status['failureCode'] ?? status['failure_code']) : null;
            scene['failureMessage'] = status is Map ? (status['failureMessage'] ?? status['failure_message']) : null;
            failed++;
            finished = true;
            break;
          }
          if (videoUrl != null && (isSuccessfulState || state.isEmpty)) {
            try {
              scene['localClipPath'] = await _downloadGeneratedClip(client, Uri.parse(videoUrl), i + 1);
              scene['status'] = 'downloaded';
              scene['downloadedAt'] = DateTime.now().toIso8601String();
              scene.remove('error');
              scene.remove('failureCode');
              scene.remove('failureMessage');
              scene.remove('lastStatusError');
              scene.remove('downloadFailureAt');
              scene.remove('downloadFailureType');
              downloaded++;
            } catch (e) {
              scene['status'] = 'failed';
              scene['error'] = 'Download failed: ' + e.toString();
              scene['downloadFailureAt'] = DateTime.now().toIso8601String();
              scene['downloadFailureType'] = e.runtimeType.toString();
              failed++;
            }
            finished = true;
            break;
          }
          scene['status'] = state.isEmpty ? 'processing' : state;
          if (attempt % 6 == 0) await _saveSceneState(p);
          if (mounted) setState(() {});
        }
        if (!finished) {
          scene['status'] = 'timeout';
          scene['error'] = 'Still processing after 15 minutes; retry this scene later';
          failed++;
        }
        await _saveSceneState(p);
      }
      project = await p.save({
        'videoScenes': scenes, 'videoGenerationEndpoint': endpoint,
        'videoGenerationDownloadedCount': downloaded, 'videoGenerationFailedCount': failed,
        'videoGenerationCompletedAt': DateTime.now().toIso8601String(),
      });
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(downloaded.toString() + ' clips downloaded; ' + failed.toString() + ' failed.')));
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Generation failed: ' + e.toString())));
    } finally {
      client.close(force: true);
      if (mounted) setState(() => saving = false);
    }
  }

  String? _findVideoUrl(dynamic output) {
    if (output is String && output.startsWith('http')) return output;
    if (output is List) {
      for (final item in output) {
        final found = _findVideoUrl(item);
        if (found != null) return found;
      }
    }
    if (output is Map) {
      return _findVideoUrl(output['url'] ?? output['uri'] ?? output['videoUrl'] ?? output['output']);
    }
    return null;
  }

  Future<void> _saveSceneState(FilmCreatorProject p) async {
    project = await p.save({
      'videoScenes': scenes, 'videoSceneCount': scenes.length,
      'videoScenePlanReady': true,
      'videoGenerationUpdatedAt': DateTime.now().toIso8601String(),
    });
  }

  Future<String> _downloadGeneratedClip(HttpClient client, Uri uri, int number) async {
    final request = await client.getUrl(uri).timeout(const Duration(seconds: 30));
    final response = await request.close().timeout(const Duration(seconds: 60));
    if (response.statusCode < 200 || response.statusCode >= 300) {
      final code = response.statusCode;
      await response.drain<void>();
      throw HttpException('Video download HTTP ' + code.toString());
    }
    final docs = await getApplicationDocumentsDirectory();
    final folder = Directory(docs.path + '/mark_ai_local_video/scenes');
    await folder.create(recursive: true);
    final file = File(folder.path + '/scene_' + number.toString().padLeft(3, '0') + '.mp4');
    // A timeout during streaming also closes the partial file; never leave a
    // truncated MP4 recorded as a successful download.
    final sink = file.openWrite();
    try {
      await response.timeout(const Duration(seconds: 90)).pipe(sink);
    } catch (_) {
      try { await sink.close(); } catch (_) {}
      if (await file.exists()) await file.delete();
      rethrow;
    }
    if (!await file.exists() || await file.length() < 1024) {
      if (await file.exists()) await file.delete();
      throw const FormatException('Downloaded MP4 is empty or incomplete');
    }
    final handle = await file.open();
    var validMp4 = false;
    try {
      final header = await handle.read(12);
      validMp4 = header.length >= 8 &&
          String.fromCharCodes(header.sublist(4, 8)) == 'ftyp';
    } finally {
      await handle.close();
    }
    if (!validMp4) {
      await file.delete();
      throw const FormatException('Downloaded file is not a valid MP4 container');
    }
    return file.path;
  }
'''
s = s[:start] + method + s[end:]
p.write_text(s, encoding="utf-8")
print("Patched async task polling and local MP4 downloads")
