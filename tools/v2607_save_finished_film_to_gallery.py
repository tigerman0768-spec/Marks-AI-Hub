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

# v2607.1: generated scene clips were only stored under app-private Documents,
# which ordinary Android file managers and Gallery apps cannot browse. Save a
# second copy to a named public gallery album after the MP4 passes validation.
scene = ROOT / "lib" / "scene_prompt_screen.dart"
if not scene.exists():
    raise SystemExit("scene_prompt_screen.dart not found")
ss = scene.read_text(encoding="utf-8")
if "import 'package:gal/gal.dart';" not in ss:
    ss = ss.replace("import 'package:flutter/material.dart';", "import 'package:flutter/material.dart';\nimport 'package:gal/gal.dart';", 1)
needle = "    return file.path;\n  }"
if "Marks AI Clips" not in ss:
    if needle not in ss:
        # The scene-download implementation varies across the base archive.
        # Keep film-assembly and local-studio gallery support even if this
        # optional scene-copy integration cannot be safely located.
        print("WARNING: scene clip gallery integration skipped: validated download return was not found")
    else:
        gallery = r"""
    // Keep the private project copy, but also publish a discoverable copy in
    // Android Gallery/Photos. Do not report a gallery copy if permission/save fails.
    final galleryAllowed = await Gal.hasAccess();
    if (!galleryAllowed) {
      final granted = await Gal.requestAccess();
      if (!granted) {
        throw Exception('Clip downloaded to app storage but Gallery permission was denied. Open the app storage/project or grant photo/video access and retry.');
      }
    }
    await Gal.putVideo(file.path, album: 'Marks AI Clips');
"""
        ss = ss.replace(needle, gallery + needle, 1)
scene.write_text(ss, encoding="utf-8")

# Add a direct Gallery save to Local Video Studio as well as the scene/film
# assembly paths. This is the screen the user can open without configuring a
# backend, so the generated local MP4 must also be easy to find in Gallery.
local = ROOT / "lib" / "local_video_studio_screen.dart"
if not local.exists():
    raise SystemExit("local_video_studio_screen.dart not found after local renderer patch")
ls = local.read_text(encoding="utf-8")
if "import 'package:gal/gal.dart';" not in ls:
    ls = ls.replace("import 'package:flutter/material.dart';", "import 'package:flutter/material.dart';\nimport 'package:gal/gal.dart';", 1)
method_local = r"""
  Future<void> _saveLocalVideoToGallery() async {
    final path = outputPath;
    if (path == null || !await File(path).exists()) {
      if (mounted) setState(() => status = 'Cannot save: the generated MP4 file is missing. Generate the video again.');
      return;
    }
    try {
      final allowed = await Gal.hasAccess();
      if (!allowed) {
        final granted = await Gal.requestAccess();
        if (!granted) throw Exception('Gallery permission was not granted.');
      }
      await Gal.putVideo(path, album: 'Marks AI Films');
      if (mounted) setState(() => status = 'Saved to phone Gallery in the Marks AI Films album. Open Gallery or Photos to play it.');
    } catch (e) {
      if (mounted) {
        setState(() => status = 'Could not save to phone Gallery: ' + e.toString());
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Gallery export failed: ' + e.toString()), duration: const Duration(seconds: 8)));
      }
    }
  }
"""
if "Future<void> _saveLocalVideoToGallery()" not in ls:
    needle = "  Future<void> _share() async {"
    if needle not in ls: raise SystemExit("Could not locate Local Video Studio share method")
    ls = ls.replace(needle, method_local + "\n" + needle, 1)
button = """        FilledButton.icon(onPressed: rendering ? null : _share, icon: const Icon(Icons.share), label: const Text('EXPORT VIDEO TO PHONE')),"""
button2 = button + """
        const SizedBox(height: 8),
        FilledButton.icon(onPressed: _saveLocalVideoToGallery, icon: const Icon(Icons.video_library), label: const Text('SAVE DIRECTLY TO PHONE GALLERY')),"""
if "SAVE DIRECTLY TO PHONE GALLERY" not in ls:
    if button not in ls: raise SystemExit("Could not locate Local Video Studio export button")
    ls = ls.replace(button, button2, 1)
# Keep the Gallery action fixed at the bottom after a video is rendered.
fixed_gallery = """    bottomNavigationBar: outputPath == null ? null : SafeArea(
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: FilledButton.icon(
          onPressed: rendering ? null : _saveLocalVideoToGallery,
          icon: const Icon(Icons.video_library),
          label: const Text('SAVE DIRECTLY TO PHONE GALLERY'),
        ),
      ),
    ),
"""
if "bottomNavigationBar: outputPath == null ? null" not in ls:
    scaffold_marker = "    body: ListView(padding: const EdgeInsets.all(16), children: ["
    if scaffold_marker not in ls: raise SystemExit("Could not locate Local Video Studio Scaffold body")
    ls = ls.replace(scaffold_marker, fixed_gallery + scaffold_marker, 1)
local.write_text(ls, encoding="utf-8")

print("v2607.2 added explicit Gallery export for finished films, generated scene clips and local studio MP4s.")
