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
    if old in s:
        s = s.replace(old, new, 1)
    elif "await _looksLikeMp4(File(path))" not in s:
        raise SystemExit("Scene input validation block is unknown and no MP4 check exists")
    # If an earlier renderer revision already validates scene MP4s, preserve it.

old_final = "      if (!ReturnCode.isSuccess(rc) || !await out.exists() || await out.length() < 1024) {"
new_final = "      if (!ReturnCode.isSuccess(rc) || !await _looksLikeMp4(out)) {"
if old_final in s:
    s = s.replace(old_final, new_final, 1)
elif "ReturnCode.isSuccess(rc) || !await _looksLikeMp4(out)" not in s:
    raise SystemExit("Final output validation block is unknown and no MP4 signature check exists")

marker = "  Future<void> _render() async {"
if marker not in s:
    raise SystemExit("Could not find render method")
if "v2610 validates every scene input" not in s:
    s = s.replace(marker, "  // v2610 validates every scene input and the final rendered MP4 signature.\n" + marker, 1)
p.write_text(s, encoding="utf-8")
print("v2610 verified MP4 signature checks for scene inputs and final output.")
