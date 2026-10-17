#!/usr/bin/env python3
"""Add a safe backend readiness preflight before any paid video generation request."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
screen = ROOT / "app" / "lib" / "scene_prompt_screen.dart"
if not screen.is_file():
    raise SystemExit("scene_prompt_screen.dart not found")

source = screen.read_text(encoding="utf-8")
marker = "Video backend is online but not ready"
if marker in source:
    print("v2622 backend readiness preflight already applied")
    raise SystemExit(0)

validation = "    if (uri == null || uri.host.isEmpty ||"
start = source.find(validation)
if start < 0:
    raise SystemExit("Could not find video backend URL validation block")
insert_at = source.find("    setState(() => saving = true);", start)
if insert_at < 0:
    raise SystemExit("Could not find generation start after backend URL validation")
block = r"""    // Check the backend before queueing any provider generation jobs. This
    // gives a clear setup error when Hostinger is online but Runway is not
    // configured, and avoids wasting time submitting scenes to an unready API.
    final healthPath = uri.path.endsWith('/api/video/generate')
        ? uri.path.substring(0, uri.path.length - '/generate'.length) + '/health'
        : (uri.path == '/' ? '' : uri.path.replaceFirst(RegExp(r'/$'), '')) +
            '/api/video/health';
    final healthUri = uri.replace(path: healthPath, query: null, fragment: null);
    final preflightClient = HttpClient();
    try {
      final healthRequest = await preflightClient.getUrl(healthUri)
          .timeout(const Duration(seconds: 15));
      final healthResponse = await healthRequest.close()
          .timeout(const Duration(seconds: 20));
      final healthBody = await utf8.decoder.bind(healthResponse).join()
          .timeout(const Duration(seconds: 15));
      if (healthResponse.statusCode < 200 || healthResponse.statusCode >= 300) {
        if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(
          content: Text('Video backend health check failed (HTTP ' +
              healthResponse.statusCode.toString() + '). Check the backend URL and deployment.'),
          duration: const Duration(seconds: 6),
        ));
        return;
      }
      dynamic health;
      try {
        health = jsonDecode(healthBody);
      } catch (_) {
        health = null;
      }
      if (health is! Map || health['generationReady'] != true) {
        final detail = health is Map
            ? (health['error'] ?? health['message'] ?? 'Runway generation is not configured').toString()
            : 'The health endpoint returned an invalid response';
        if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(
          content: Text('Video backend is online but not ready: ' + detail +
              '. Configure RUNWAYML_API_SECRET on the backend before generating.'),
          duration: const Duration(seconds: 8),
        ));
        return;
      }
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(
        content: Text('Cannot reach the video backend health endpoint: ' + e.toString()),
        duration: const Duration(seconds: 8),
      ));
      return;
    } finally {
      preflightClient.close(force: true);
    }
"""
source = source[:insert_at] + block + source[insert_at:]
screen.write_text(source, encoding="utf-8")
print("PASS: added video backend health/readiness preflight before generation")
