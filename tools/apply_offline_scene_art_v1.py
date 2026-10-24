from pathlib import Path

root = Path(__file__).resolve().parents[1] / "app"
target = root / "android/app/src/main/kotlin/com/marksai/app/MainActivity.kt"
if not target.exists():
    raise SystemExit("Native renderer source missing")
s = target.read_text(encoding="utf-8")
anchor = "    p.color = Color.argb(210, 3, 7, 18); c.drawRect(0f, 130f, 320f, 180f, p)"
if "OFFLINE_SCENE_ART_V1" not in s:
    if anchor not in s:
        raise SystemExit("Renderer scene overlay anchor not found")
    art = r"""
    // OFFLINE_SCENE_ART_V1: prompt-keyword-driven artwork, drawn locally on-device.
    val topic = (idea + " " + genre + " " + title).lowercase(Locale.ROOT)
    val ground = 132f
    if (topic.contains("forest") || topic.contains("dog") || topic.contains("walk") || topic.contains("nature")) {
      // Layered trees with parallax, plus a moving walker and dog.
      for (i in 0..7) {
        val x = ((i * 49 - frame * (i % 3 + 1) / 3) % 370 + 370) % 370 - 25
        val tall = 45f + (i % 3) * 15f
        p.color = if (i % 2 == 0) Color.rgb(13, 48, 42) else Color.rgb(19, 69, 48)
        val path = android.graphics.Path().apply {
          moveTo(x.toFloat(), ground); lineTo(x + 22f, ground - tall); lineTo(x + 44f, ground); close()
        }
        c.drawPath(path, p)
        p.color = Color.rgb(67, 43, 28); c.drawRect(x + 19f, ground - 4f, x + 25f, 158f, p)
      }
      val walkX = 95f + (frame % 100) * 0.7f
      p.color = Color.rgb(25, 27, 32); c.drawCircle(walkX, 91f, 7f, p)
      p.strokeWidth = 5f; p.strokeCap = Paint.Cap.ROUND
      c.drawLine(walkX, 98f, walkX, 119f, p)
      val leg = (frame % 12 - 6) * 1.2f
      c.drawLine(walkX, 117f, walkX - 7f + leg, 132f, p)
      c.drawLine(walkX, 117f, walkX + 7f - leg, 132f, p)
      c.drawLine(walkX, 103f, walkX - 8f, 113f, p); c.drawLine(walkX, 103f, walkX + 9f, 110f, p)
      val dogX = walkX + 22f
      p.color = Color.rgb(157, 105, 57); c.drawOval(dogX, 116f, dogX + 18f, 126f, p)
      c.drawCircle(dogX + 17f, 116f, 5f, p)
      c.strokeWidth = 2f
      c.drawLine(dogX + 4f, 124f, dogX + 2f, 132f, p); c.drawLine(dogX + 13f, 124f, dogX + 16f, 132f, p)
      c.drawLine(walkX + 8f, 106f, dogX + 15f, 118f, p)
    } else if (topic.contains("build") || topic.contains("construct") || topic.contains("crane") || topic.contains("timelapse")) {
      // A construction site that rises through the five story beats.
      val height = 18f + scene * 17f
      p.color = Color.rgb(38, 47, 58); c.drawRect(95f, ground - height, 205f, ground, p)
      p.color = Color.rgb(239, 178, 51)
      for (row in 0..(scene + 1)) for (col in 0..3) c.drawRect(104f + col * 23f, ground - height + 7f + row * 13f, 115f + col * 23f, ground - height + 14f + row * 13f, p)
      p.strokeWidth = 3f; c.drawLine(150f, ground - height, 150f, 28f, p)
      c.drawLine(150f, 30f, 265f, 30f, p); c.drawLine(150f, 30f, 102f, 30f, p)
      c.drawLine(246f, 30f, 246f, 48f + (frame % 20), p)
      p.color = Color.rgb(238, 177, 48); c.drawCircle(246f, 50f + (frame % 20), 3f, p)
      p.strokeWidth = 2f
      for (i in 0..2) {
        val wx = 45f + i * 24f
        p.color = Color.rgb(25, 30, 35); c.drawCircle(wx, 115f, 4f, p)
        c.drawLine(wx, 119f, wx, 130f, p); c.drawLine(wx, 130f, wx - 4f, 135f, p); c.drawLine(wx, 130f, wx + 4f, 135f, p)
      }
    } else if (topic.contains("sci-fi") || topic.contains("space") || topic.contains("alien") || topic.contains("robot")) {
      // A moving spacecraft and distant planet.
      p.color = Color.rgb(94, 133, 174); c.drawCircle(255f, 48f, 23f, p)
      p.color = Color.rgb(47, 80, 126); c.drawArc(232f, 38f, 278f, 62f, 0f, 180f, true, p)
      val sx = 55f + (frame * 2 % 230)
      p.color = Color.rgb(190, 207, 220)
      val ship = android.graphics.Path().apply { moveTo(sx, 72f); lineTo(sx + 28f, 80f); lineTo(sx + 4f, 88f); close() }
      c.drawPath(ship, p); p.color = Color.CYAN; c.drawCircle(sx + 5f, 80f, 2f, p)
      p.color = Color.rgb(92, 28, 112); c.drawOval(sx - 14f, 78f, sx + 2f, 84f, p)
    } else {
      // Default offline cinematic landscape with a moving horizon light.
      p.color = Color.rgb(22, 39, 52)
      val hills = android.graphics.Path().apply { moveTo(0f, ground); lineTo(60f, 92f); lineTo(112f, ground); lineTo(185f, 100f); lineTo(255f, ground); lineTo(320f, 95f); lineTo(320f, 150f); lineTo(0f, 150f); close() }
      c.drawPath(hills, p)
      p.color = Color.rgb(255, 193, 93)
      c.drawCircle(255f - (frame % 90), 68f, 8f, p)
    }
"""
    s = s.replace(anchor, art + "\n" + anchor, 1)
    target.write_text(s, encoding="utf-8")
print("Offline scene artwork patch applied.")
