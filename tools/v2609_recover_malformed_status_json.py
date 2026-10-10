from pathlib import Path

p = Path(__file__).resolve().parents[1] / "app" / "lib" / "scene_prompt_screen.dart"
if not p.exists():
    raise SystemExit("scene_prompt_screen.dart not found")
s = p.read_text(encoding="utf-8")
needle = "          final dynamic status = jsonDecode(statusBody);"
if "v2609 malformed status recovery" in s:
    print("v2609 malformed status recovery already applied")
    raise SystemExit(0)
if needle not in s:
    raise SystemExit("Could not find status JSON decode point; refusing unsafe patch")
replacement = """          // v2609 malformed status recovery: proxies can briefly return HTML or partial JSON.
          dynamic status;
          try {
            status = jsonDecode(statusBody);
          } catch (e) {
            scene['status'] = 'waiting_for_status';
            scene['lastStatusError'] = 'Invalid status response: ' + e.toString();
            if (attempt % 6 == 0) await _saveSceneState(p);
            if (mounted) setState(() {});
            continue;
          }"""
s = s.replace(needle, replacement, 1)
p.write_text(s, encoding="utf-8")
print("v2609 added retry handling for malformed status JSON.")
