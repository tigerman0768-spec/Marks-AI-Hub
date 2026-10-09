from pathlib import Path

path = Path("lib/local_video_studio_screen.dart")
if not path.exists():
    raise SystemExit("Local Video Studio source is missing")

s = path.read_text(encoding="utf-8")
s = s.replace("enum LocalFilmStyle { timelapse, sciFi }", "enum LocalFilmStyle { construction, timelapse, sciFi }")
s = s.replace("LocalFilmStyle style = LocalFilmStyle.sciFi;", "LocalFilmStyle style = LocalFilmStyle.construction;")
s = s.replace("    if (sci) {", """    if (style == LocalFilmStyle.construction) {
      // A procedural construction-site timelapse: the shell rises floor by floor,
      // scaffolding is erected, workers move, and a tower crane sweeps across the site.
      paint.color = const Color(0xfff5b66b).withOpacity(.75);
      canvas.drawCircle(Offset(530 - t * 28, 72 + t * 18), 24, paint);
      for (int i = 0; i < 4; i++) {
        final cx = (i * 173.0 + frame * (1.0 + i * .2)) % 760 - 55;
        final cy = 50.0 + i * 22;
        paint.color = Colors.white.withOpacity(.18);
        canvas.drawOval(Rect.fromCenter(center: Offset(cx, cy), width: 90, height: 13), paint);
        canvas.drawOval(Rect.fromCenter(center: Offset(cx + 20, cy + 3), width: 72, height: 11), paint);
      }
      paint.color = const Color(0xff6c7559);
      canvas.drawRect(const Rect.fromLTWH(0, 285, 640, 75), paint);
      paint.color = const Color(0xffb7a58a);
      canvas.drawRect(const Rect.fromLTWH(0, 282, 640, 8), paint);
      // Foundation and concrete slab.
      paint.color = const Color(0xff8b9297);
      canvas.drawRect(const Rect.fromLTWH(178, 270, 270, 18), paint);
      final floors = 1 + (t * 5).floor();
      const left = 220.0, right = 420.0, floorH = 31.0, baseY = 270.0;
      for (int floor = 0; floor < floors; floor++) {
        final topY = baseY - (floor + 1) * floorH;
        paint.color = Color.lerp(const Color(0xffc1c8ca), const Color(0xff89979d), floor / 6)!;
        canvas.drawRect(Rect.fromLTRB(left, topY, right, topY + floorH - 2), paint);
        paint.color = const Color(0xff69777d);
        canvas.drawRect(Rect.fromLTWH(left - 3, topY + floorH - 3, right - left + 6, 4), paint);
        paint.color = const Color(0xffe4d9b9);
        for (int window = 0; window < 4; window++) {
          final wx = left + 17 + window * 45;
          canvas.drawRect(Rect.fromLTWH(wx, topY + 6, 23, 17), paint);
          paint.color = const Color(0xff657e8a);
          canvas.drawRect(Rect.fromLTWH(wx + 2, topY + 8, 19, 13), paint);
          paint.color = const Color(0xffe4d9b9);
        }
      }
      // Scaffold rails grow with the building.
      paint.color = const Color(0xffd2a84f);
      paint.style = PaintingStyle.stroke;
      paint.strokeWidth = 2;
      final topScaffold = baseY - floors * floorH - 8;
      canvas.drawLine(Offset(left - 14, topScaffold), Offset(left - 14, 280), paint);
      canvas.drawLine(Offset(right + 14, topScaffold), Offset(right + 14, 280), paint);
      for (double y = topScaffold + 10; y < 281; y += 22) {
        canvas.drawLine(Offset(left - 17, y), Offset(right + 17, y), paint);
      }
      canvas.drawLine(Offset(left - 14, topScaffold), Offset(right + 14, topScaffold), paint);
      paint.style = PaintingStyle.fill;
      // Tower crane and moving hook.
      paint.color = const Color(0xffe8b33f);
      canvas.drawRect(const Rect.fromLTWH(480, 80, 7, 205), paint);
      canvas.drawRect(Rect.fromLTWH(365, 76 + t * 8, 230, 6), paint);
      paint.color = const Color(0xff4b5053);
      canvas.drawRect(Rect.fromLTWH(400 + t * 85, 82 + t * 8, 3, 37 + t * 12), paint);
      canvas.drawRect(Rect.fromLTWH(393 + t * 85, 116 + t * 20, 17, 5), paint);
      // Small hard-hatted workers move around the base.
      for (int worker = 0; worker < 4; worker++) {
        final x = 80 + ((frame * (1.2 + worker * .25) + worker * 137) % 470);
        final y = 266.0 + (worker % 2) * 4;
        paint.color = worker.isEven ? const Color(0xffff8b28) : const Color(0xffe7e7df);
        canvas.drawCircle(Offset(x, y - 16), 4, paint);
        canvas.drawLine(Offset(x, y - 12), Offset(x, y - 2), paint..strokeWidth = 3);
        canvas.drawLine(Offset(x, y - 9), Offset(x - 5, y - 5), paint);
        canvas.drawLine(Offset(x, y - 9), Offset(x + 5, y - 5), paint);
        canvas.drawLine(Offset(x, y - 2), Offset(x - 4, y + 3), paint);
        canvas.drawLine(Offset(x, y - 2), Offset(x + 4, y + 3), paint);
        paint.color = const Color(0xffffd34e);
        canvas.drawArc(Rect.fromCenter(center: Offset(x, y - 20), width: 10, height: 6), math.pi, math.pi, false, paint..style = PaintingStyle.stroke);
        paint.style = PaintingStyle.fill;
      }
      final label = TextPainter(
        text: TextSpan(text: 'CONSTRUCTION TIMELAPSE', style: TextStyle(color: Colors.white, fontSize: 16, fontWeight: FontWeight.bold, shadows: [Shadow(color: Colors.black.withOpacity(.7), blurRadius: 4)])),
        textDirection: TextDirection.ltr,
      )..layout();
      label.paint(canvas, const Offset(18, 18));
    } else if (sci) {""")
s = s.replace("final frameCount = seconds * 12;", "final frameRate = seconds >= 60 ? 1 : 12;\n      final frameCount = seconds * frameRate;")
s = s.replace("final base = '-y -framerate 12 -i \"' + input + '\" -vf \"scale=1280:720:flags=lanczos,format=yuv420p\" -movflags +faststart ';",
              "final base = '-y -framerate ' + frameRate.toString() + ' -i \"' + input + '\" -vf \"fps=12,scale=1280:720:flags=lanczos,format=yuv420p\" -movflags +faststart ';")
s = s.replace("ButtonSegment(value: LocalFilmStyle.timelapse, label: Text('Timelapse'), icon: Icon(Icons.wb_twilight)),",
              "ButtonSegment(value: LocalFilmStyle.construction, label: Text('Construction'), icon: Icon(Icons.construction)),\n        ButtonSegment(value: LocalFilmStyle.timelapse, label: Text('Sunset'), icon: Icon(Icons.wb_twilight)),")
s = s.replace("Text('Duration: ' + seconds.toString() + ' seconds'),\n      Slider(value: seconds.toDouble(), min: 4, max: 12, divisions: 4, label: seconds.toString() + ' seconds', onChanged: rendering ? null : (v) => setState(() => seconds = v.round())),",
"""DropdownButtonFormField<int>(
        value: seconds,
        decoration: const InputDecoration(labelText: 'Video duration', border: OutlineInputBorder()),
        items: const [
          DropdownMenuItem<int>(value: 6, child: Text('6 seconds')),
          DropdownMenuItem<int>(value: 30, child: Text('30 seconds')),
          DropdownMenuItem<int>(value: 60, child: Text('1 minute')),
          DropdownMenuItem<int>(value: 300, child: Text('5 minutes')),
        ],
        onChanged: rendering ? null : (v) { if (v != null) setState(() => seconds = v); },
      ),""")
# Remove accidental escaping from the Python-generated Dart strings in the replacement above.
s = s.replace(r"'\${v ~/ 60} minute'", "v == 60 ? '1 minute' : '5 minutes'")
s = s.replace(r"'\$v seconds'", "v.toString() + ' seconds'")
if "LocalFilmStyle.construction" not in s or "fps=12,scale=1280:720" not in s or "5 minutes" not in s:
    raise SystemExit("Construction timelapse patch incomplete")
path.write_text(s, encoding="utf-8")
print("v2603 added construction-site timelapse visuals, duration presets through five minutes, and memory-conscious frame sampling.")
