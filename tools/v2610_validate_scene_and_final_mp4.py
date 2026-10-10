from pathlib import Path

p = Path(__file__).resolve().parents[1] / "app" / "lib" / "film_assembly_screen.dart"
if not p.exists():
    raise SystemExit("film_assembly_screen.dart not found")
s = p.read_text(encoding="utf-8")
old = """      if (path.isEmpty || !await File(path).exists()) {
        setState(() => errorText = 'Scene ' + (scene['number'] ?? i + 1).toString() + ' is missing. Download every generated MP4 first.');
        return;
      }
      ordered.add(scene);"""
new = """      if (path.isEmpty || !await File(path).exists()) {
        setState(() => errorText = 'Scene ' + (scene['number'] ?? i + 1).toString() + ' is missing. Download every generated MP4 first.');
        return;
      }
      if (!await _looksLikeMp4(File(path))) {
        setState(() => errorText = 'Scene ' + (scene['number'] ?? i + 1).toString() + ' is not a valid MP4. Regenerate or download that scene again.');
        return;
      }
      ordered.add(scene);"""
if "v2610 validates every scene input" not in s:
    if old not in s:
        raise SystemExit("Could not locate scene input validation block; refusing unsafe patch")
    s = s.replace(old, new, 1)
old_final = "      if (!ReturnCode.isSuccess(rc) || !await out.exists() || await out.length() < 1024) {"
new_final = "      if (!ReturnCode.isSuccess(rc) || !await _looksLikeMp4(out)) {"
if old_final in s:
    s = s.replace(old_final, new_final, 1)
elif new_final not in s:
    raise SystemExit("Could not locate final output validation block")
s = s.replace("  Future<void> _render() async {", "  // v2610 validates every scene input and the final rendered MP4 signature.\n  Future<void> _render() async {", 1)
p.write_text(s, encoding="utf-8")
print("v2610 added MP4 signature checks for every input clip and final output.")
