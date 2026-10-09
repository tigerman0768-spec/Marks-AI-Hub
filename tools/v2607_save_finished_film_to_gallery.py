from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "app"
pubspec = ROOT / "pubspec.yaml"
if not pubspec.exists():
    raise SystemExit("app/pubspec.yaml not found")
s = pubspec.read_text(encoding="utf-8")
if "  gal:" not in s:
    marker = "  share_plus:"
    if marker not in s:
        raise SystemExit("share_plus dependency marker not found")
    s = s.replace(marker, "  gal: ^2.3.0\n" + marker, 1)
    pubspec.write_text(s, encoding="utf-8")

screen = ROOT / "lib" / "film_assembly_screen.dart"
if not screen.exists():
    raise SystemExit("film_assembly_screen.dart not found after renderer patch")
s = screen.read_text(encoding="utf-8")
if "import 'package:gal/gal.dart';" not in s:
    s = s.replace("import 'package:flutter/material.dart';", "import 'package:flutter/material.dart';\nimport 'package:gal/gal.dart';", 1)
method = r"""
  Future<void> _saveToPhoneGallery() async {
    final path = outputPath;
    if (path == null || !await File(path).exists()) {
      if (mounted) setState(() => errorText = 'Render the finished film first.');
      return;
    }
    try {
      final allowed = await Gal.hasAccess();
      if (!allowed) {
        final granted = await Gal.requestAccess();
        if (!granted) throw Exception('Video/photo permission was not granted.');
      }
      await Gal.putVideo(path, album: 'Marks AI Films');
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Finished film saved to your phone gallery. Open Gallery or Photos to find it.')),
        );
        setState(() => status = 'Saved to phone gallery: Marks AI Films');
      }
    } catch (e) {
      if (mounted) setState(() => errorText = 'Could not save to phone gallery: ' + e.toString());
    }
  }
"""
if "Future<void> _saveToPhoneGallery()" not in s:
    needle = "  Future<void> _share() async {"
    if needle not in s:
        raise SystemExit("Could not locate share method")
    s = s.replace(needle, method + "\n" + needle, 1)
button = """          OutlinedButton.icon(onPressed: _share, icon: const Icon(Icons.share), label: const Text('SHARE / EXPORT FILM')),"""
button2 = button + """
          const SizedBox(height: 8),
          FilledButton.icon(onPressed: _saveToPhoneGallery, icon: const Icon(Icons.save_alt), label: const Text('SAVE FILM TO PHONE GALLERY')),"""
if "SAVE FILM TO PHONE GALLERY" not in s:
    if button not in s:
        raise SystemExit("Could not locate share/export button")
    s = s.replace(button, button2, 1)
screen.write_text(s, encoding="utf-8")
print("v2607 added an explicit save-to-phone-gallery action for rendered MP4 films.")
