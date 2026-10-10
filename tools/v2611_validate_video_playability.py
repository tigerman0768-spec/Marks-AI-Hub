from pathlib import Path

p = Path(__file__).resolve().parents[1] / "app" / "lib" / "film_assembly_screen.dart"
if not p.exists():
    raise SystemExit("film_assembly_screen.dart not found")
s = p.read_text(encoding="utf-8")
if "Future<bool> _isPlayableMp4" not in s:
    marker = "  Future<void> _render() async {"
    if marker not in s:
        raise SystemExit("Could not find render method; refusing unsafe patch")
    method = r"""
  Future<bool> _isPlayableMp4(File file) async {
    if (!await _looksLikeMp4(file)) return false;
    // Decode a short sample. A valid ftyp header alone cannot prove the
    // container contains a usable video stream.
    final command = '-v error -i ' + _shellQuote(file.path) +
        ' -t 1 -f null -';
    final session = await FFmpegKit.execute(command);
    return ReturnCode.isSuccess(await session.getReturnCode());
  }

"""
    s = s.replace(marker, method + marker, 1)
s = s.replace("if (!await _looksLikeMp4(File(path))) {", "if (!await _isPlayableMp4(File(path))) {")
s = s.replace("if (!ReturnCode.isSuccess(rc) || !await _looksLikeMp4(out)) {", "if (!ReturnCode.isSuccess(rc) || !await _isPlayableMp4(out)) {")
if "await _isPlayableMp4(File(path))" not in s:
    raise SystemExit("Scene playability check was not inserted")
if "await _isPlayableMp4(out)" not in s:
    raise SystemExit("Final film playability check was not inserted")
p.write_text(s, encoding="utf-8")
print("v2611 added FFmpeg decode-sample validation for scene clips and final film.")
