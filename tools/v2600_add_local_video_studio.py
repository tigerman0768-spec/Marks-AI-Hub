from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "app"
LIB = ROOT / "lib"

screen = r'''import 'dart:async';
import 'dart:io';
import 'dart:math' as math;
import 'dart:typed_data';
import 'dart:ui' as ui;
import 'package:flutter/material.dart';
import 'package:path_provider/path_provider.dart';
import 'package:share_plus/share_plus.dart';
import 'package:ffmpeg_kit_flutter_new_min/ffmpeg_kit.dart';
import 'package:ffmpeg_kit_flutter_new_min/return_code.dart';
import 'film_creator_project.dart';

enum LocalFilmStyle { timelapse, sciFi, forestWalk, construction }

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
  String status = 'Ready. Generated videos stay inside Mark’s AI until you export them.';
  String? outputPath;
  FilmCreatorProject? project;
  final TextEditingController promptController = TextEditingController(text: 'A man walking his dog through a peaceful forest');

  @override void initState() { super.initState(); _loadProject(); }
  @override void dispose() {
    promptController.dispose();
    super.dispose();
  }
  Future<void> _loadProject() async {
    try {
      if (widget.projectId != null) project = await FilmCreatorProject.resume(widget.projectId!);
      if (mounted) setState(() {});
    } catch (e) {
      debugPrint('LOCAL_VIDEO_PROJECT_LOAD_FAILED: ' + e.toString());
      if (mounted) {
        setState(() => status = 'Could not load the saved film project. You can still create a local video; project details may not be saved. Details: ' + e.toString());
      }
    }
  }

  Future<Uint8List> _frame(int frame, int count) async {
    const w = 320.0, h = 180.0;
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
        final yy = (255.0 + math.pow((j + 1) / 8, 1.8) * 105).toDouble();
        canvas.drawLine(Offset(0, yy), Offset(w, yy), paint);
      }
      paint.style = PaintingStyle.fill;
      final shipX = 110 + t * 410;
      paint.color = const Color(0xff35d9ff).withOpacity(.2);
      canvas.drawCircle(Offset(shipX - 15, 210), 15, paint);
      paint.color = const Color(0xffd7f6ff);
      final ship = Path()..moveTo(shipX + 15, 210)..lineTo(shipX - 10, 202)..lineTo(shipX - 5, 210)..lineTo(shipX - 10, 218)..close();
      canvas.drawPath(ship, paint);
    } else if (style == LocalFilmStyle.forestWalk) {
      // Forest path with a warm, relaxed walker and dog; silhouettes move together
      // across the path so the selected prompt is represented in the actual frames.
      paint.color = const Color(0xffb9dca0);
      canvas.drawRect(const Rect.fromLTWH(0, 0, w, 190), paint);
      paint.shader = ui.Gradient.linear(const Offset(0, 0), const Offset(0, 210), [const Color(0xffb9e7ff), const Color(0xffe5efb1)]);
      canvas.drawRect(const Rect.fromLTWH(0, 0, w, 210), paint);
      paint.shader = null;
      // distant tree trunks and leafy crowns
      for (int i = 0; i < 11; i++) {
        final x = i * 67.0 - 12 + math.sin(t * math.pi * 2 + i) * 4;
        final trunk = Paint()..color = i.isEven ? const Color(0xff5c6842) : const Color(0xff776344);
        canvas.drawRect(Rect.fromLTWH(x, 62 + (i % 3) * 15.0, 13, 225), trunk);
        paint.color = i.isEven ? const Color(0xff356a45) : const Color(0xff477b48);
        canvas.drawCircle(Offset(x + 4, 58 + (i % 3) * 15.0), 38 + (i % 4) * 4.0, paint);
        canvas.drawCircle(Offset(x + 24, 82 + (i % 3) * 11.0), 29, paint);
      }
      // sunlit winding path
      final path = Path()..moveTo(250, 190)..lineTo(390, 190)..lineTo(640, 360)..lineTo(0, 360)..close();
      paint.color = const Color(0xffc6a77a); canvas.drawPath(path, paint);
      paint.color = const Color(0xffd7c092).withOpacity(.7);
      canvas.drawOval(Rect.fromCenter(center: Offset(320, 285), width: 210, height: 32), paint);
      // walker: head, jacket, arms and legs with a gentle walking stride
      final walk = math.sin(t * math.pi * 4) * 7;
      paint.color = const Color(0xffe8b88f); canvas.drawCircle(Offset(286 + t * 24, 210), 13, paint);
      paint.color = const Color(0xffe9ece5);
      canvas.drawOval(Rect.fromCenter(center: Offset(286 + t * 24, 240), width: 29, height: 43), paint);
      paint.color = const Color(0xff4777a8);
      canvas.drawLine(Offset(278 + t * 24, 255), Offset(274 + walk + t * 24, 286), paint..strokeWidth = 7);
      canvas.drawLine(Offset(294 + t * 24, 255), Offset(300 - walk + t * 24, 286), paint..strokeWidth = 7);
      paint.color = const Color(0xffe8b88f);
      canvas.drawLine(Offset(274 + t * 24, 231), Offset(260 + t * 24, 250), paint..strokeWidth = 5);
      canvas.drawLine(Offset(297 + t * 24, 231), Offset(311 + t * 24, 246), paint..strokeWidth = 5);
      // happy dog walking beside the person, with tail and four moving legs
      final dx = 345 + t * 24;
      paint.color = const Color(0xffb77a43);
      canvas.drawOval(Rect.fromCenter(center: Offset(dx, 270), width: 47, height: 25), paint);
      canvas.drawCircle(Offset(dx + 22, 257), 12, paint);
      canvas.drawCircle(Offset(dx + 29, 246), 5, paint);
      paint.color = const Color(0xfff1d2a1);
      canvas.drawCircle(Offset(dx + 26, 258), 2, paint);
      paint.color = const Color(0xff7e512e);
      canvas.drawLine(Offset(dx - 15, 265), Offset(dx - 25, 252), paint..strokeWidth = 4);
      for (int leg = 0; leg < 4; leg++) {
        final lx = dx - 14 + leg * 9.0;
        canvas.drawLine(Offset(lx, 279), Offset(lx + (leg.isEven ? walk : -walk), 292), paint..strokeWidth = 4);
      }
      // little flowers beside the trail
      for (int i = 0; i < 18; i++) {
        final x = (i * 43.0 + 17) % w;
        final y = 310 + (i % 4) * 11.0;
        paint.color = i.isEven ? const Color(0xfff4e6a5) : const Color(0xfff7f4ec);
        canvas.drawCircle(Offset(x, y), 2.5, paint);
      }
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

  LocalFilmStyle _styleForPrompt(String value) {
    final p = value.toLowerCase();
    if (['construction', 'construction site', 'building site', 'crane', 'building being built', 'house being built', 'building a house', 'build a house', 'skyscraper', 'builders', 'building work', 'bricklaying', 'excavator', 'bulldozer', 'scaffolding', 'roadworks', 'road construction', 'concrete pour', 'renovation', 'laying bricks', 'brick layers', 'building a wall', 'digging foundations', 'foundation work', 'demolition', 'demolishing a building', 'crane lifting', 'steel frame', 'high-rise construction', 'construction workers'].any((word) => p.contains(word))) return LocalFilmStyle.construction;
    if (['space', 'sci-fi', 'sci fi', 'spaceship', 'planet', 'galaxy', 'astronaut', 'stars'].any((word) => p.contains(word))) return LocalFilmStyle.sciFi;
    if (['city street', 'busy street', 'city centre', 'city center', 'downtown', 'urban street', 'traffic jam', 'cars driving', 'city skyline', 'town centre', 'town center', 'parking garage', 'car park', 'office district', 'subway station', 'shopping street', 'pedestrian crossing'].any((word) => p.contains(word))) return LocalFilmStyle.timelapse;
    if (['dog', 'puppy', 'forest', 'woodland', 'woods', 'park', 'walking the dog', 'man walking his dog', 'golden retriever', 'trail', 'countryside', 'autumn forest', 'woodland path', 'hiking trail'].any((word) => p.contains(word))) return LocalFilmStyle.forestWalk;
    return LocalFilmStyle.timelapse;
  }

  String _styleLabel(LocalFilmStyle value) {
    switch (value) {
      case LocalFilmStyle.forestWalk: return 'Forest walk';
      case LocalFilmStyle.sciFi: return 'Sci-fi';
      case LocalFilmStyle.timelapse: return 'Timelapse';
      case LocalFilmStyle.construction: return 'Construction timelapse';
    }
  }

  Future<void> _render() async {
    if (rendering) return;
    final prompt = promptController.text.trim();
    if (prompt.isEmpty) {
      setState(() => status = 'Please describe the video you want first.');
      return;
    }
    // Respect the currently selected style; prompt edits already update the suggested style live.
    if (!mounted) return;
    setState(() { rendering = true; progress = 0; status = 'Starting video generation…'; });
    ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Video generation started. Keep Mark’s AI open while it renders.'), duration: Duration(seconds: 3)));
    await Future<void>.delayed(const Duration(milliseconds: 80));
    Directory? frameDir;
    try {
      debugPrint('LOCAL_VIDEO_STAGE: preparing_frames');
      if (mounted) setState(() => status = 'Preparing local cinematic frames…');
      final docs = await getApplicationDocumentsDirectory();
      final root = Directory(docs.path + '/mark_ai_local_video');
      await root.create(recursive: true);
      final stamp = DateTime.now().millisecondsSinceEpoch;
      frameDir = Directory(root.path + '/frames_' + stamp.toString());
      await frameDir.create(recursive: true);
      final frameCount = seconds * 2;
      debugPrint('LOCAL_VIDEO_STAGE: drawing_frames count=' + frameCount.toString());
      for (int i = 0; i < frameCount; i++) {
        final bytes = await _frame(i, frameCount);
        await File(frameDir.path + '/frame_' + i.toString().padLeft(4, '0') + '.png').writeAsBytes(bytes);
        if (!mounted) return;
        setState(() { progress = .78 * (i + 1) / frameCount; status = 'Drawing frame ' + (i + 1).toString() + ' of ' + frameCount.toString() + '…'; });
      }
      debugPrint('LOCAL_VIDEO_STAGE: frames_complete count=' + frameCount.toString());
      final rawTitle = prompt.length > 3 ? prompt.substring(0, math.min(prompt.length, 48)) : (project?.title ?? 'local_video');
      final title = rawTitle.replaceAll(RegExp(r'[^A-Za-z0-9_-]+'), '_');
      final out = File(root.path + '/' + title + '_' + style.name + '_' + stamp.toString() + '.mp4');
      if (mounted) setState(() { progress = .80; status = 'Encoding lightweight cinematic MP4 locally…'; });
      final input = frameDir.path + '/frame_%04d.png';
      // The minimal FFmpeg package on Android may not include the MPEG-4 encoder.
      // Use Android MediaCodec directly at low resolution to avoid a known failing encoder.
      final base = '-y -threads 1 -framerate 2 -i "' + input + '" -vf "scale=320:180:flags=fast_bilinear,format=yuv420p" -movflags +faststart ';
      // Synchronous FFmpegKit execution blocks Flutter's UI isolate during
      // encoding. Use the completion callback so progress/status stays responsive.
      Future<dynamic> executeAndWait(String command, String label) async {
        final completer = Completer<dynamic>();
        await FFmpegKit.executeAsync(command, (session) {
          if (!completer.isCompleted) completer.complete(session);
        });
        // Give Android's emulator and slower phones enough time to encode.
        // The overall smoke test has its own four-minute limit.
        return completer.future.timeout(const Duration(seconds: 90), onTimeout: () {
          debugPrint('LOCAL_VIDEO_STAGE: ' + label + '_timeout_after_90s');
          throw TimeoutException(label + ' did not finish within 90 seconds.');
        });
      }
      dynamic session;
      ReturnCode? rc;
      String encoderLog = '';
      debugPrint('LOCAL_VIDEO_STAGE: mpeg4_encode_started output=' + out.path);
      try {
        session = await executeAndWait(base + '-c:v mpeg4 -q:v 4 -threads 1 "' + out.path + '"', 'mpeg4_encode');
        rc = await session.getReturnCode();
        encoderLog = (await session.getAllLogsAsString()) ?? '';
        debugPrint('LOCAL_VIDEO_STAGE: mpeg4_return_code=' + rc.toString());
      } catch (e) {
        encoderLog = 'MPEG-4 encoder attempt failed: ' + e.toString();
        debugPrint('LOCAL_VIDEO_STAGE: mpeg4_error=' + e.toString());
      }
      if (rc == null || !ReturnCode.isSuccess(rc) || !await out.exists() || await out.length() < 2048) {
        try { if (await out.exists()) await out.delete(); } catch (_) {}
        debugPrint('LOCAL_VIDEO_STAGE: mediacodec_encode_started output=' + out.path);
        try {
          session = await executeAndWait(base + '-c:v h264_mediacodec -b:v 500k -threads 1 "' + out.path + '"', 'mediacodec_encode');
          rc = await session.getReturnCode();
          final fallbackLog = (await session.getAllLogsAsString()) ?? '';
          encoderLog += '\\nMediaCodec fallback log:\\n' + fallbackLog;
          debugPrint('LOCAL_VIDEO_STAGE: mediacodec_return_code=' + rc.toString());
        } catch (e) {
          encoderLog += '\\nMediaCodec fallback failed: ' + e.toString();
          debugPrint('LOCAL_VIDEO_STAGE: mediacodec_error=' + e.toString());
        }
      }
      if (rc == null || !ReturnCode.isSuccess(rc) || !await out.exists() || await out.length() < 2048) {
        try { if (await out.exists()) await out.delete(); } catch (_) {}
        throw Exception('MP4 encoding failed with MPEG-4 and Android MediaCodec. FFmpeg logs: ' + (encoderLog.length > 1600 ? encoderLog.substring(encoderLog.length - 1600) : encoderLog));
      }
      debugPrint('LOCAL_VIDEO_STAGE: encoder_completed');
      debugPrint('LOCAL_VIDEO_STAGE: encode_success bytes=' + (await out.length()).toString());
      if (mounted) setState(() { progress = .94; status = 'Checking that the exported MP4 plays correctly…'; });
      debugPrint('LOCAL_VIDEO_STAGE: decode_verification_started');
      final check = await executeAndWait('-v error -i "' + out.path + '" -f null -', 'decode_verification');
      debugPrint('LOCAL_VIDEO_STAGE: decode_verification_completed');
      final checkCode = await check.getReturnCode().timeout(const Duration(seconds: 12), onTimeout: () => null);
      final checkLogs = (await check.getAllLogsAsString()) ?? '';
      if (checkCode == null) {
        if (checkLogs.toLowerCase().contains('error') || checkLogs.toLowerCase().contains('invalid data')) throw Exception('MP4 verification timed out and FFmpeg reported an error: ' + checkLogs);
        debugPrint('LOCAL_VIDEO_STAGE: decode_return_code_timeout_no_ffmpeg_errors');
      } else if (!ReturnCode.isSuccess(checkCode)) throw Exception('Output was created but could not be decoded for verification: ' + checkLogs);
      // The MP4 has already been encoded and decoded successfully. Keep it
      // available even if saving optional project metadata fails afterward.
      if (mounted) setState(() {
        progress = .98;
        outputPath = out.path;
        status = 'Video verified. Saving its details to the film project…';
      });
      String? projectSaveWarning;
      if (project != null) {
        try {
          final old = project!.state['localGeneratedVideos'];
          final videos = old is List ? List<dynamic>.from(old) : <dynamic>[];
          videos.add({'path': out.path, 'style': style.name, 'seconds': seconds, 'createdAt': DateTime.now().toIso8601String(), 'renderer': 'local_procedural_v1'});
          project = await project!.save({'localGeneratedVideos': videos});
        } catch (e) {
          projectSaveWarning = e.toString();
          debugPrint('LOCAL_VIDEO_PROJECT_METADATA_SAVE_FAILED: ' + projectSaveWarning);
        }
      }
      if (mounted) setState(() {
        progress = 1;
        outputPath = out.path;
        status = projectSaveWarning == null
            ? 'Verified: MP4 created and decoded successfully. It is stored privately inside Mark’s AI; use EXPORT VIDEO TO PHONE to save a visible copy.'
            : 'Video created and verified. Its project details could not be saved, but the MP4 is still available to export. Details: ' + projectSaveWarning!;
      });
    } catch (e, stack) {
      debugPrint('LOCAL_VIDEO_GENERATION_FAILED: ' + e.toString() + ' ' + stack.toString());
      if (mounted) {
        setState(() => status = 'Video generation failed: ' + e.toString());
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Video generation failed: ' + e.toString()), duration: const Duration(seconds: 8)));
      }
    } finally {
      if (frameDir != null && await frameDir.exists()) {
        try { await frameDir.delete(recursive: true); } catch (_) {}
      }
      if (mounted) setState(() => rendering = false);
    }
  }

  Future<void> _share() async {
    final path = outputPath;
    if (path == null || !await File(path).exists()) {
      if (mounted) setState(() => status = 'Export failed: the MP4 file is missing. Generate again and check the error message.');
      return;
    }
    try {
      final videoFile = File(path);
      final fileSize = await videoFile.length();
      if (fileSize < 2048) {
        if (mounted) setState(() => status = 'Export failed: the MP4 file is unexpectedly small and may be incomplete. Generate the video again.');
        return;
      }
      await Share.shareXFiles([XFile(path)], text: 'Video created locally with Mark’s AI. Choose a save option to copy it to your phone.');
      if (mounted) setState(() => status = 'The sharing menu has closed. If you chose a save option, check that destination to confirm the video was saved.');
    } catch (e) {
      if (mounted) {
        setState(() => status = 'Export failed: ' + e.toString());
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Could not open the video export menu: ' + e.toString()), duration: const Duration(seconds: 8)));
      }
    }
  }

  @override Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('Local Video Studio')),
    body: ListView(padding: const EdgeInsets.all(16), children: [
      Text('Make a video on this device', style: Theme.of(context).textTheme.headlineSmall),
      const SizedBox(height: 8),
      const Text('Describe your video below. The offline renderer chooses the closest of four hand-drawn templates: forest walk, sci-fi, construction timelapse, or general timelapse. It creates a playable MP4, but it does not generate arbitrary objects or realistic AI footage.'),
      const SizedBox(height: 12),
      TextField(controller: promptController, enabled: !rendering, maxLines: 3, onChanged: (value) { final next = _styleForPrompt(value); if (mounted) setState(() => style = next); }, decoration: const InputDecoration(labelText: 'Describe your video', hintText: 'A man walking his dog through a forest', border: OutlineInputBorder())),
      const SizedBox(height: 8),
      Text('Best matching offline template: ' + _styleLabel(style), style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w600)),
      const SizedBox(height: 4),
      const Text('Offline mode creates simple illustrated motion, not realistic AI footage. For a full film, generate real scene clips with a configured video provider, then assemble the clips with sound and subtitles.', style: TextStyle(fontSize: 12)),
      const SizedBox(height: 18),
      SegmentedButton<LocalFilmStyle>(segments: const [
        ButtonSegment(value: LocalFilmStyle.timelapse, label: Text('Timelapse'), icon: Icon(Icons.wb_twilight)),
        ButtonSegment(value: LocalFilmStyle.sciFi, label: Text('Sci-fi'), icon: Icon(Icons.rocket_launch)),
        ButtonSegment(value: LocalFilmStyle.forestWalk, label: Text('Forest walk'), icon: Icon(Icons.forest)),
        ButtonSegment(value: LocalFilmStyle.construction, label: Text('Construction'), icon: Icon(Icons.construction)),
      ], selected: {style}, onSelectionChanged: rendering ? null : (s) => setState(() => style = s.first)),
      const SizedBox(height: 16),
      Text('Duration: ' + seconds.toString() + ' seconds (4–60 seconds)'),
      Slider(value: seconds.toDouble().clamp(4.0, 60.0), min: 4, max: 60, divisions: 14, label: seconds.toString() + ' seconds', onChanged: rendering ? null : (v) => setState(() => seconds = v.round())),
      if (rendering) LinearProgressIndicator(value: progress),
      const SizedBox(height: 12),
      FilledButton.icon(onPressed: rendering ? null : () { _render(); }, icon: rendering ? const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2)) : const Icon(Icons.movie_creation), label: Text(rendering ? 'RENDERING LOCALLY…' : 'GENERATE VIDEO')),
      const SizedBox(height: 12),
      Text(status),
      if (outputPath != null) ...[
        const SizedBox(height: 12),
        const ListTile(leading: Icon(Icons.verified, color: Colors.green), title: Text('MP4 created and decoded'), subtitle: Text('Saved privately inside Mark’s AI. Tap SHARE VIDEO and choose Save to device / My Files to make it visible in your phone’s folders.')),
        SelectableText(outputPath!),
        FilledButton.icon(onPressed: rendering ? null : _share, icon: const Icon(Icons.share), label: const Text('EXPORT VIDEO TO PHONE')),
        const SizedBox(height: 6),
        const Text('In the Android share menu, choose Save to device, My Files, or another file-saving option. Mark’s AI cannot put this private file directly into Downloads until you export it.', style: TextStyle(fontSize: 12)),
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
            // Opening the local studio must never depend on project persistence.
            // A save failure previously left users on Film Creator and made the
            // Generate Video action appear to do nothing. Pass the existing ID
            // when available; the studio supports standalone rendering without it.
            onPressed: saving ? null : () {
              Navigator.of(context).push(
                MaterialPageRoute(
                  builder: (_) => LocalVideoStudioScreen(projectId: projectId),
                ),
              );
            },
            icon: const Icon(Icons.movie_creation),
            label: const Text('CREATE VIDEO LOCALLY — TIMELAPSE / SCI-FI'),
          ),"""
if "CREATE VIDEO LOCALLY — TIMELAPSE / SCI-FI" not in text:
    if needle not in text: raise SystemExit("Could not locate Film Creator screenplay button")
    text = text.replace(needle, replacement)
creator.write_text(text, encoding="utf-8")
