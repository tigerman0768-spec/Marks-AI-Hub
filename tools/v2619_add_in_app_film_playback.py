from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "app"
screen = ROOT / "lib" / "film_assembly_screen.dart"
if not screen.exists():
    raise SystemExit("film_assembly_screen.dart not found")

s = screen.read_text(encoding="utf-8")
if "import 'package:video_player/video_player.dart';" not in s:
    marker = "import 'package:flutter/material.dart';"
    if marker not in s:
        raise SystemExit("Flutter material import not found")
    s = s.replace(marker, marker + "\\nimport 'package:video_player/video_player.dart';", 1)

method = r"""
  Future<void> _playFinishedFilm() async {
    final path = outputPath;
    if (path == null || !await File(path).exists()) {
      if (mounted) setState(() => errorText = 'The finished MP4 is missing. Render the film again.');
      return;
    }
    if (!mounted) return;
    await showDialog<void>(
      context: context,
      builder: (_) => _FinishedFilmPlayerDialog(path: path),
    );
  }
"""
if "Future<void> _playFinishedFilm()" not in s:
    marker = "  Future<void> _share() async {"
    if marker not in s:
        raise SystemExit("Film Assembly share method not found")
    s = s.replace(marker, method + "\\n" + marker, 1)

# Insert the playback control alongside the existing share/export control.
if "PLAY FINISHED FILM" not in s:
    marker = "OutlinedButton.icon(onPressed: _share, icon: const Icon(Icons.share), label: const Text('SHARE / EXPORT FILM')),"
    if marker not in s:
        raise SystemExit("Film Assembly share/export button not found")
    s = s.replace(marker, "FilledButton.icon(onPressed: _playFinishedFilm, icon: const Icon(Icons.play_circle), label: const Text('PLAY FINISHED FILM')),\\n          const SizedBox(height: 8),\\n          " + marker, 1)

player = r"""

class _FinishedFilmPlayerDialog extends StatefulWidget {
  final String path;
  const _FinishedFilmPlayerDialog({required this.path});

  @override
  State<_FinishedFilmPlayerDialog> createState() => _FinishedFilmPlayerDialogState();
}

class _FinishedFilmPlayerDialogState extends State<_FinishedFilmPlayerDialog> {
  late final VideoPlayerController _controller;
  Object? _error;

  @override
  void initState() {
    super.initState();
    _controller = VideoPlayerController.file(File(widget.path));
    _controller.initialize().then((_) {
      if (mounted) setState(() {});
    }).catchError((Object error) {
      if (mounted) setState(() => _error = error);
    });
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  String _time(Duration value) {
    final seconds = value.inSeconds;
    return '${seconds ~/ 60}:${(seconds % 60).toString().padLeft(2, '0')}';
  }

  @override
  Widget build(BuildContext context) {
    final ready = _controller.value.isInitialized;
    return AlertDialog(
      title: const Text('Your finished film'),
      content: SizedBox(
        width: 560,
        child: _error != null
            ? Text('This MP4 could not be played: $_error')
            : !ready
                ? const SizedBox(height: 180, child: Center(child: CircularProgressIndicator()))
                : Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      AspectRatio(
                        aspectRatio: _controller.value.aspectRatio > 0 ? _controller.value.aspectRatio : 16 / 9,
                        child: VideoPlayer(_controller),
                      ),
                      VideoProgressIndicator(_controller, allowScrubbing: true, padding: const EdgeInsets.symmetric(vertical: 12)),
                      Row(
                        children: [
                          IconButton(
                            tooltip: _controller.value.isPlaying ? 'Pause' : 'Play',
                            onPressed: () async {
                              if (_controller.value.isPlaying) {
                                await _controller.pause();
                              } else {
                                await _controller.play();
                              }
                              if (mounted) setState(() {});
                            },
                            icon: Icon(_controller.value.isPlaying ? Icons.pause_circle : Icons.play_circle),
                          ),
                          Text('${_time(_controller.value.position)} / ${_time(_controller.value.duration)}'),
                        ],
                      ),
                    ],
                  ),
      ),
      actions: [
        TextButton(onPressed: () => Navigator.of(context).pop(), child: const Text('CLOSE')),
      ],
    );
  }
}
"""
if "class _FinishedFilmPlayerDialog extends StatefulWidget" not in s:
    s = s.rstrip() + "\\n" + player + "\\n"
screen.write_text(s, encoding="utf-8")
print("v2619 added an in-app MP4 player to Film Assembly.")
