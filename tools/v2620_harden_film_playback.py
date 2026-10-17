from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "app"
screen = ROOT / "lib" / "film_assembly_screen.dart"
if not screen.exists():
    raise SystemExit("film_assembly_screen.dart not found")

s = screen.read_text(encoding="utf-8")
# A previously saved path is not proof of a playable film. Validate it on
# resume so a stale/corrupt MP4 is never shown as a finished film.
old_load = """    outputPath = project?.state['finalFilmPath']?.toString();
    if (outputPath != null && !File(outputPath!).existsSync()) outputPath = null;
    if (mounted) setState(() => loading = false);"""
new_load = """    outputPath = project?.state['finalFilmPath']?.toString();
    if (outputPath != null) {
      final candidate = File(outputPath!);
      if (!await _isPlayableMp4(candidate)) outputPath = null;
    }
    if (mounted) setState(() => loading = false);"""
if new_load not in s:
    if old_load not in s:
        raise SystemExit("Could not locate saved-film restore block; refusing unsafe patch")
    s = s.replace(old_load, new_load, 1)

# The playback dialog must refresh its play/pause icon and elapsed time while
# the controller advances, and detach the listener before disposing it.
old_init = """    _controller = VideoPlayerController.file(File(widget.path));
    _controller.initialize().then((_) {
      if (mounted) setState(() {});
    }).catchError((Object error) {
      if (mounted) setState(() => _error = error);
    });"""
new_init = """    _controller = VideoPlayerController.file(File(widget.path));
    _controller.addListener(_onPlayerChanged);
    _controller.initialize().then((_) {
      if (mounted) setState(() {});
    }).catchError((Object error) {
      if (mounted) setState(() => _error = error);
    });"""
if new_init not in s:
    if old_init not in s:
        raise SystemExit("Could not locate player initialization block; refusing unsafe patch")
    s = s.replace(old_init, new_init, 1)

old_dispose = """  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }"""
new_dispose = """  void _onPlayerChanged() {
    if (mounted) setState(() {});
  }

  @override
  void dispose() {
    _controller.removeListener(_onPlayerChanged);
    _controller.dispose();
    super.dispose();
  }"""
if new_dispose not in s:
    if old_dispose not in s:
        raise SystemExit("Could not locate player dispose block; refusing unsafe patch")
    s = s.replace(old_dispose, new_dispose, 1)

screen.write_text(s, encoding="utf-8")
print("v2620 validates resumed films before displaying them and keeps playback controls in sync.")
