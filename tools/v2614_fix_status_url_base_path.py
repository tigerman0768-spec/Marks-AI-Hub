from pathlib import Path

p = Path(__file__).resolve().parents[1] / "app" / "lib" / "scene_prompt_screen.dart"
if not p.exists():
    raise SystemExit("scene_prompt_screen.dart not found")
s = p.read_text(encoding="utf-8")
old = """          final statusPath = uri.path.endsWith('/api/video/generate')
              ? uri.path.substring(0, uri.path.length - '/generate'.length) + '/status/' + Uri.encodeComponent(activeTask)
              : '/api/video/status/' + Uri.encodeComponent(task);
          final statusUri = uri.replace(path: statusPath, query: null, fragment: null);"""
new = """          // Keep a reverse-proxy/base path when constructing the status URL.
          // Example: https://host.example/myapp/api/video/generate becomes
          // https://host.example/myapp/api/video/status/<taskId>.
          final endpointPath = uri.path.replaceFirst(RegExp(r'/+$'), '');
          String statusPath;
          if (endpointPath.endsWith('/generate')) {
            statusPath = endpointPath.substring(0, endpointPath.length - '/generate'.length) +
                '/status/' + Uri.encodeComponent(activeTask);
          } else {
            final basePath = endpointPath == '/' ? '' : endpointPath;
            statusPath = basePath + '/api/video/status/' + Uri.encodeComponent(activeTask);
          }
          final statusUri = uri.replace(path: statusPath, query: null, fragment: null);"""
if new in s:
    print("v2614 status URL fix already applied")
elif old not in s:
    raise SystemExit("Could not locate status URL construction; refusing unsafe patch")
else:
    s = s.replace(old, new, 1)
    p.write_text(s, encoding="utf-8")
    print("v2614 fixed status URL construction for reverse-proxy base paths")
