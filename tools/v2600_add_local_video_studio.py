from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "app"
LIB = ROOT / "lib"

screen = r'''import 'dart:io';
import 'dart:math' as math;
import 'dart:typed_data';
import 'dart:ui' as ui;
import 'package:flutter/material.dart';
import 'package:path_provider/path_provider.dart';
import 'package:share_plus/share_plus.dart';
import 'package:ffmpeg_kit_flutter_new_min/ffmpeg_kit.dart';
import 'package:ffmpeg_kit_flutter_new_min/return_code.dart';
import 'film_creator_project.dart';

enum LocalFilmStyle { timelapse, sciFi }

class LocalVideoStudioScreen extends StatefulWidget {
  final String? projectId;
  const LocalVideoStudioScreen({super.key, this.projectId});
  @override State<LocalVideoStudioScreen> createState() => _LocalVideoStudioScreenState();
}

class _LocalVideoStudioScreenState extends State<LocalVideoStudioScreen> {
  LocalFilmStyle style = LocalFilmStyle.sciFi;
  int seconds = 6;
  bool rendering = false;
  double progress = 0;
  String status = 'Rendered on this device. No video backend is required.';
  String? outputPath;
  FilmCreatorProject? project;

  @override void initState() { super.initState(); _loadProject(); }
  Future<void> _loadProject() async {
    if (widget.projectId != null) project = await FilmCreatorProject.resume(widget.projectId!);
    if (mounted) setState(() {});
  }

  Future<Uint8List> _frame(int frame, int count) async {
    const w = 640.0, h = 360.0;
    final recorder = ui.PictureRecorder();
    final canvas = Canvas(recorder, const Rect.fromLTWH(0, 0, w, h));
    final paint = Paint();
    final t = frame / math.max(1, count - 1);
    final sci = style == LocalFilmStyle.sciFi;
    final top = sci ? const Color(0xff020615) : Color.lerp(const Color(0xff182a63), const Color(0xfff9a65a), t)!;
    final bottom = sci ? const Color(0xff161044) : Color.lerp(const Color(0xff3865a8), const Color(0xff3a183e), t)!;
    paint.shader = ui.Gradient.linear(const Offset(0, 0), const Offset(0, h), [top, bottom]);
    canvas.drawRect(const Rect.fromLTWH(0, 0, w, h), paint);
    paint.shader = null;
    if (sci) {
      for (int i = 0; i < 105; i++) {
        final x = (i * 97.13 + frame * (1.4 + (i % 4) * .42)) % w;
        final y = (i * 47.71) % 255.0;
        paint.color = i % 7 == 0 ? const Color(0xffa9e7ff) : Colors.white.withOpacity(.45 + .5 * ((math.sin(frame * .15 + i) + 1) / 2));
        canvas.drawCircle(Offset(x, y), i % 13 == 0 ? 1.7 : 0.8, paint);
      }
      final planet = Offset(455 - t * 30, 126 + math.sin(t * math.pi * 2) * 5);
      paint.shader = ui.Gradient.radial(planet, 70, [const Color(0xffa8e6ff), const Color(0xff5b5fd5), const Color(0xff21134f)]);
      canvas.drawCircle(planet, 57, paint);
      paint.shader = null;
      paint.color = const Color(0xff5bd7ff).withOpacity(.7);
      paint.style = PaintingStyle.stroke; paint.strokeWidth = 2;
      canvas.drawOval(Rect.fromCenter(center: planet.translate(0, 6), width: 145, height: 27), paint);
      paint.style = PaintingStyle.fill;
      paint.color = const Color(0xff7b54ff).withOpacity(.4);
      for (int i = -8; i <= 8; i++) {
        final path = Path()..moveTo(w / 2 + i * 2.5, 255)..lineTo(w / 2 + i * 18.0 + t * 6, h);
        paint.style = PaintingStyle.stroke; paint.strokeWidth = .7; canvas.drawPath(path, paint);
      }
      for (int j = 0; j < 8; j++) {
        final yy = 255.0 + math.pow((j + 1) / 8, 1.8) * 105;
        canvas.drawLine(Offset(0, yy), Offset(w, yy), paint);
      }
      paint.style = PaintingStyle.fill;
      final shipX = 110 + t * 410;
      paint.color = const Color(0xff35d9ff).withOpacity(.2);
      canvas.drawCircle(Offset(shipX - 15, 210), 15, paint);
      paint.color = const Color(0xffd7f6ff);
      final ship = Path()..moveTo(shipX + 15, 210)..lineTo(shipX - 10, 202)..lineTo(shipX - 5, 210)..lineTo(shipX - 10, 218)..close();
      canvas.drawPath(ship, paint);
    } else {
      final sunX = 100 + t * 420, sunY = 92 + t * 175;
      paint.shader = ui.Gradient.radial(Offset(sunX, sunY), 70, [const Color(0xfffff2bb).withOpacity(.75), const Color(0xffffb65e).withOpacity(.08), Colors.transparent]);
      canvas.drawCircle(Offset(sunX, sunY), 70, paint);
      paint.shader = null;
      paint.color = Color.lerp(const Color(0xfffff4c7), const Color(0xffe9685b), t)!;
      canvas.drawCircle(Offset(sunX, sunY), 25, paint);
      for (int i = 0; i < 5; i++) {
        final cx = (i * 155.0 + t * (25 + i * 5)) % 760 - 60;
        final cy = 55.0 + i * 25;
        paint.color = Colors.white.withOpacity(.1);
        canvas.drawOval(Rect.fromCenter(center: Offset(cx, cy), width: 105, height: 13), paint);
        canvas.drawOval(Rect.fromCenter(center: Offset(cx + 24, cy + 3), width: 85, height: 12), paint);
      }
      final far = Path()..moveTo(0,248)..lineTo(85,200)..lineTo(150,237)..lineTo(238,189)..lineTo(322,239)..lineTo(405,205)..lineTo(500,241)..lineTo(570,211)..lineTo(640,242)..lineTo(640,360)..lineTo(0,360)..close();
      paint.color = const Color(0xff45385d); canvas.drawPath(far, paint);
      final near = Path()..moveTo(0,286)..lineTo(95,264)..lineTo(170,289)..lineTo(265,251)..lineTo(370,290)..lineTo(470,260)..lineTo(560,291)..lineTo(640,273)..lineTo(640,360)..lineTo(0,360)..close();
      paint.color = const Color(0xff1b213d); canvas.drawPath(near, paint);
    }
    paint.color = Colors.black.withOpacity(.2);
    canvas.drawRect(const Rect.fromLTWH(0, 0, w, 13), paint);
    canvas.drawRect(const Rect.fromLTWH(0, 347, w, 13), paint);
    final picture = recorder.endRecording();
    final image = await picture.toImage(w.toInt(), h.toInt());
    final bytes = await image.toByteData(format: ui.ImageByteFormat.png);
    image.dispose(); picture.dispose();
    return bytes!.buffer.asUint8List();
  }

  Future<void> _render() async {
    if (rendering) return;
    setState(() { rendering = true; progress = 0; outputPath = null; status = 'Preparing local cinematic frames…'; });
    Directory? frameDir;
    try {
      final docs = await getApplicationDocumentsDirectory();
      final root = Directory(docs.path + '/mark_ai_local_video');
      await root.create(recursive: true);
      final stamp = DateTime.now().millisecondsSinceEpoch;
      frameDir = Directory(root.path + '/frames_' + stamp.toString());
      await frameDir.create(recursive: true);
      final frameCount = seconds * 12;
      for (int i = 0; i < frameCount; i++) {
        final bytes = await _frame(i, frameCount);
        await File(frameDir.path + '/frame_' + i.toString().padLeft(4, '0') + '.png').writeAsBytes(bytes);
        if (!mounted) return;
        setState(() { progress = .78 * (i + 1) / frameCount; status = 'Drawing frame ' + (i + 1).toString() + ' of ' + frameCount.toString() + '…'; });
      }
      final rawTitle = project?.title ?? (style == LocalFilmStyle.sciFi ? 'sci_fi' : 'timelapse');
      final title = rawTitle.replaceAll(RegExp(r'[^A-Za-z0-9_-]+'), '_');
      final out = File(root.path + '/' + title + '_' + style.name + '_' + stamp.toString() + '.mp4');
      setState(() => status = 'Encoding cinematic MP4 locally…');
      final input = frameDir.path + '/frame_%04d.png';
      final command = '-y -framerate 12 -i "' + input + '" -vf "scale=1280:720:flags=lanczos,format=yuv420p" -c:v mpeg4 -q:v 2 -movflags +faststart "' + out.path + '"';
      final session = await FFmpegKit.execute(command);
      final rc = await session.getReturnCode();
      if (!ReturnCode.isSuccess(rc) || !await out.exists() || await out.length() < 2048) {
        final logs = (await session.getOutput()) ?? '';
        throw Exception('MP4 encoding failed. ' + (logs.length > 500 ? logs.substring(logs.length - 500) : logs));
      }
      final check = await FFmpegKit.execute('-v error -i "' + out.path + '" -f null -');
      if (!ReturnCode.isSuccess(await check.getReturnCode())) throw Exception('Output was created but could not be decoded for verification.');
      if (project != null) {
        final old = project!.state['localGeneratedVideos'];
        final videos = old is List ? List<dynamic>.from(old) : <dynamic>[];
        videos.add({'path': out.path, 'style': style.name, 'seconds': seconds, 'createdAt': DateTime.now().toIso8601String(), 'renderer': 'local_procedural_v1'});
        project = await project!.save({'localGeneratedVideos': videos});
      }
      if (mounted) setState(() { progress = 1; outputPath = out.path; status = 'Verified: MP4 created and decoded successfully on this device.'; });
    } catch (e) {
      if (mounted) setState(() => status = 'Could not finish the video: ' + e.toString());
    } finally {
      if (frameDir != null && await frameDir.exists()) {
        try { await frameDir.delete(recursive: true); } catch (_) {}
      }
      if (mounted) setState(() => rendering = false);
    }
  }

  Future<void> _share() async {
    final path = outputPath;
    if (path != null && await File(path).exists()) await Share.shareXFiles([XFile(path)], text: 'Created locally with Mark’s AI');
  }

  @override Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('Local Video Studio')),
    body: ListView(padding: const EdgeInsets.all(16), children: [
      Text('Make a video on this device', style: Theme.of(context).textTheme.headlineSmall),
      const SizedBox(height: 8),
      const Text('No backend URL, downloaded stock clips or cloud video service is needed. This first version draws animated scenes locally and encodes a real MP4.'),
      const SizedBox(height: 18),
      SegmentedButton<LocalFilmStyle>(segments: const [
        ButtonSegment(value: LocalFilmStyle.timelapse, label: Text('Timelapse'), icon: Icon(Icons.wb_twilight)),
        ButtonSegment(value: LocalFilmStyle.sciFi, label: Text('Sci-fi'), icon: Icon(Icons.rocket_launch)),
      ], selected: {style}, onSelectionChanged: rendering ? null : (s) => setState(() => style = s.first)),
      const SizedBox(height: 16),
      Text('Duration: ' + seconds.toString() + ' seconds'),
      Slider(value: seconds.toDouble(), min: 4, max: 12, divisions: 4, label: seconds.toString() + ' seconds', onChanged: rendering ? null : (v) => setState(() => seconds = v.round())),
      if (rendering) LinearProgressIndicator(value: progress),
      const SizedBox(height: 12),
      FilledButton.icon(onPressed: rendering ? null : _render, icon: rendering ? const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2)) : const Icon(Icons.movie_creation), label: Text(rendering ? 'RENDERING LOCALLY…' : 'GENERATE VIDEO')),
      const SizedBox(height: 12),
      Text(status),
      if (outputPath != null) ...[
        const SizedBox(height: 12),
        const ListTile(leading: Icon(Icons.verified, color: Colors.green), title: Text('MP4 created and decoded'), subtitle: Text('1280 × 720 output saved in the app documents folder.')),
        SelectableText(outputPath!),
        OutlinedButton.icon(onPressed: _share, icon: const Icon(Icons.share), label: const Text('SHARE VIDEO')),
      ],
    ]),
  );
}
'''
(LIB / "local_video_studio_screen.dart").write_text(screen, encoding="utf-8")

creator = LIB / "film_creator_screen.dart"
text = creator.read_text(encoding="utf-8")
if "local_video_studio_screen.dart" not in text:
    text = text.replace("import 'screenplay_screen.dart';", "import 'screenplay_screen.dart';\nimport 'local_video_studio_screen.dart';")
needle = """          FilledButton.icon(
            onPressed: saving ? null : _generateScreenplay,
            icon: const Icon(Icons.auto_awesome),
            label: const Text('GENERATE SCREENPLAY'),
          ),"""
replacement = needle + """
          const SizedBox(height: 10),
          FilledButton.icon(
            onPressed: saving ? null : () async {
              final p = await _save();
              if (!mounted) return;
              await Navigator.push(context, MaterialPageRoute(builder: (_) => LocalVideoStudioScreen(projectId: p.id)));
            },
            icon: const Icon(Icons.movie_creation),
            label: const Text('CREATE VIDEO LOCALLY — TIMELAPSE / SCI-FI'),
          ),"""
if "CREATE VIDEO LOCALLY — TIMELAPSE / SCI-FI" not in text:
    if needle not in text: raise SystemExit("Could not locate Film Creator screenplay button")
    text = text.replace(needle, replacement)
creator.write_text(text, encoding="utf-8")
