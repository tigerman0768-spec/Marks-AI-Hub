from pathlib import Path
import re

p = Path(__file__).resolve().parents[1] / "app" / "lib" / "scene_prompt_screen.dart"
if not p.exists():
    raise SystemExit("scene_prompt_screen.dart not found")
s = p.read_text(encoding="utf-8")

if "Keep a reverse-proxy/base path when constructing the status URL." in s:
    print("v2614 status URL fix already applied")
    raise SystemExit(0)

# v2605 may already contain a newer, three-branch status URL implementation.
# Preserve that implementation rather than insisting on the older two-branch
# string. Only replace the known legacy implementation when it is present.
old = """          final statusPath = uri.path.endsWith('/api/video/generate')
              ? uri.path.substring(0, uri.path.length - '/generate'.length) + '/status/' + Uri.encodeComponent(activeTask)
              : '/api/video/status/' + Uri.encodeComponent(task);
          final statusUri = uri.replace(path: statusPath, query: null, fragment: null);"""
new = """          // Keep a reverse-proxy/base path when constructing the status URL.
          // Example: https://host.example/myapp/api/video/generate becomes
          // https://host.example/myapp/api/video/status/<taskId>.
          final endpointPath = uri.path.replaceFirst(RegExp(r'/+$'), '');
          String statusPath;
          if (endpointPath.endsWith('/api/video/generate')) {
            statusPath = endpointPath.substring(0, endpointPath.length - '/generate'.length) +
                '/status/' + Uri.encodeComponent(activeTask);
          } else if (endpointPath.endsWith('/api/video/status')) {
            statusPath = endpointPath + '/' + Uri.encodeComponent(activeTask);
          } else {
            final basePath = endpointPath == '/' ? '' : endpointPath;
            statusPath = basePath + '/api/video/status/' + Uri.encodeComponent(activeTask);
          }
          final statusUri = uri.replace(path: statusPath, query: null, fragment: null);"""
if old in s:
    s = s.replace(old, new, 1)
else:
    # Recognize the newer implementation already introduced in v2605.
    if "final statusPath = uri.path.endsWith('/api/video/generate')" in s and "Uri.encodeComponent(activeTask)" in s and "statusUri = uri.replace(path: statusPath" in s:
        print("Current status URL implementation already preserves API and base paths")
        raise SystemExit(0)
    raise SystemExit("No supported status URL construction found; refusing unsafe patch")

p.write_text(s, encoding="utf-8")
print("v2614 repaired status URL construction for API and reverse-proxy base paths")
