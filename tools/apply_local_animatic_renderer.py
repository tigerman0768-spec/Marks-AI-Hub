#!/usr/bin/env python3
"""Patch Mark's AI with a native local MP4 storyboard preview."""
from pathlib import Path
root = Path(__file__).resolve().parents[1] / "app"
dart = root / "lib/film_creator_screen.dart"
s = dart.read_text(encoding="utf-8")
if "marksai/local_video_renderer" not in s:
    s = s.replace("import 'package:flutter/material.dart';", "import 'package:flutter/material.dart';\nimport 'package:flutter/services.dart';", 1)
if "Future<void> _generateLocalPreview()" not in s:
    marker = "  Future<void> _generateFilm() async {"
    method = """
  static const MethodChannel _localRenderer = MethodChannel('marksai/local_video_renderer');
  Future<void> _generateLocalPreview() async {
    setState(() { saving = true; status = 'Rendering local storyboard MP4…'; });
    try {
      await _save(create: projectId == null);
      final result = await _localRenderer.invokeMapMethod<String, dynamic>('renderPreview', <String, dynamic>{
        'title': title.text.trim().isEmpty ? 'Untitled Film' : title.text.trim(),
        'idea': idea.text.trim().isEmpty ? 'A new story begins.' : idea.text.trim(),
        'genre': genre,
      });
      final path = result?['path']?.toString();
      if (path == null || path.isEmpty) throw Exception('Renderer returned no MP4 path.');
      await _saveState('local_preview_complete');
      if (!mounted) return;
      await showDialog<void>(context: context, builder: (_) => AlertDialog(
        title: const Text('Storyboard preview created'),
        content: SelectableText('A 30-second MP4 preview was rendered on this phone and saved to Movies/MarksAI.\\n\\n' + path + '\\n\\nThis is an animated storyboard preview, not AI-generated cinematic footage.'),
        actions: [TextButton(onPressed: () => Navigator.of(context).pop(), child: const Text('CLOSE'))],
      ));
    } catch (e) { _error('Local video render failed: ' + e.toString()); }
    finally { if (mounted) setState(() => saving = false); }
  }

"""
    if marker not in s: raise SystemExit("Generate Film method anchor missing")
    s = s.replace(marker, method + marker, 1)
if "GENERATE LOCAL MP4 PREVIEW" not in s:
    marker = """          FilledButton.icon(
            onPressed: saving ? null : _generateFilm,
            icon: const Icon(Icons.movie_creation),
            label: const Text('GENERATE FILM'),
          ),"""
    replacement = """          FilledButton.icon(
            onPressed: saving ? null : _generateLocalPreview,
            icon: const Icon(Icons.video_file),
            label: const Text('GENERATE LOCAL MP4 PREVIEW'),
          ),
          const Padding(
            padding: EdgeInsets.only(top: 6),
            child: Text('Creates an on-device animated storyboard MP4. Full AI cinematic footage needs a working AI backend.', style: TextStyle(color: Colors.white70)),
          ),
          const SizedBox(height: 12),
          FilledButton.icon(
            onPressed: saving ? null : _generateFilm,
            icon: const Icon(Icons.movie_creation),
            label: const Text('GENERATE AI FILM'),
          ),"""
    if marker not in s: raise SystemExit("Generate Film button anchor missing")
    s = s.replace(marker, replacement, 1)
dart.write_text(s, encoding="utf-8")

kotlin = root / "android/app/src/main/kotlin/com/marksai/app/MainActivity.kt"
kotlin.parent.mkdir(parents=True, exist_ok=True)
kotlin.write_text(r'''package com.marksai.app
import android.content.ContentValues
import android.graphics.Bitmap
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Paint
import android.media.MediaCodec
import android.media.MediaCodecInfo
import android.media.MediaFormat
import android.media.MediaMuxer
import android.os.Build
import android.provider.MediaStore
import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodChannel
import java.io.File
import java.io.FileInputStream
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import kotlin.math.min

class MainActivity : FlutterActivity() {
  override fun configureFlutterEngine(engine: FlutterEngine) {
    super.configureFlutterEngine(engine)
    MethodChannel(engine.dartExecutor.binaryMessenger, "marksai/local_video_renderer").setMethodCallHandler { call, result ->
      if (call.method != "renderPreview") { result.notImplemented(); return@setMethodCallHandler }
      val title = call.argument<String>("title") ?: "Untitled Film"
      val idea = call.argument<String>("idea") ?: "A new story begins."
      val genre = call.argument<String>("genre") ?: "Drama"
      Thread {
        try {
          val savedUri = renderPreview(title, idea, genre)
          runOnUiThread { result.success(mapOf("path" to savedUri, "bytes" to savedUri.length)) }
        } catch (e: Exception) {
          runOnUiThread { result.error("LOCAL_RENDER_FAILED", e.message ?: "Video encoding failed", null) }
        }
      }.start()
    }
  }

  private fun renderPreview(title: String, idea: String, genre: String): String {
    val w = 320; val h = 180; val fps = 10; val count = 300
    val temp = File(cacheDir, "marksai_preview_" + System.currentTimeMillis() + ".mp4")
    val fmt = MediaFormat.createVideoFormat(MediaFormat.MIMETYPE_VIDEO_AVC, w, h)
    fmt.setInteger(MediaFormat.KEY_COLOR_FORMAT, MediaCodecInfo.CodecCapabilities.COLOR_FormatYUV420Planar)
    fmt.setInteger(MediaFormat.KEY_BIT_RATE, 650000); fmt.setInteger(MediaFormat.KEY_FRAME_RATE, fps)
    fmt.setInteger(MediaFormat.KEY_I_FRAME_INTERVAL, 1)
    val codec = MediaCodec.createEncoderByType(MediaFormat.MIMETYPE_VIDEO_AVC)
    var muxer: MediaMuxer? = null; var started = false; var track = -1
    val info = MediaCodec.BufferInfo()
    val bitmap = Bitmap.createBitmap(w, h, Bitmap.Config.ARGB_8888)
    try {
      codec.configure(fmt, null, null, MediaCodec.CONFIGURE_FLAG_ENCODE); codec.start()
      muxer = MediaMuxer(temp.absolutePath, MediaMuxer.OutputFormat.MUXER_OUTPUT_MPEG_4)
      var frame = 0; var inputDone = false; var outputDone = false
      while (!outputDone) {
        if (!inputDone) {
          val ix = codec.dequeueInputBuffer(10000)
          if (ix >= 0) {
            val input = codec.getInputBuffer(ix) ?: throw IllegalStateException("Missing encoder input")
            if (frame >= count) {
              codec.queueInputBuffer(ix, 0, 0, frame * 1000000L / fps, MediaCodec.BUFFER_FLAG_END_OF_STREAM); inputDone = true
            } else {
              draw(bitmap, title, idea, genre, frame, count)
              val bytes = toYuv(bitmap); input.clear()
              if (input.remaining() < bytes.size) throw IllegalStateException("Encoder input buffer is too small")
              input.put(bytes); codec.queueInputBuffer(ix, 0, bytes.size, frame * 1000000L / fps, 0); frame++
            }
          }
        }
        val ox = codec.dequeueOutputBuffer(info, 10000)
        when {
          ox == MediaCodec.INFO_OUTPUT_FORMAT_CHANGED -> {
            track = muxer.addTrack(codec.outputFormat); muxer.start(); started = true
          }
          ox >= 0 -> {
            val data = codec.getOutputBuffer(ox)
            if (data != null && info.size > 0) {
              if (!started) throw IllegalStateException("MP4 muxer did not start")
              data.position(info.offset); data.limit(info.offset + info.size); muxer.writeSampleData(track, data, info)
            }
            codec.releaseOutputBuffer(ox, false)
            if ((info.flags and MediaCodec.BUFFER_FLAG_END_OF_STREAM) != 0) outputDone = true
          }
        }
      }
    } finally {
      try { codec.stop() } catch (_: Exception) {}
      codec.release()
      if (started) try { muxer?.stop() } catch (_: Exception) {}
      muxer?.release(); bitmap.recycle()
    }
    if (!temp.exists() || temp.length() < 2048) throw IllegalStateException("MP4 output is missing or empty")
    val stamp = SimpleDateFormat("yyyyMMdd_HHmmss", Locale.US).format(Date())
    val safe = title.replace(Regex("[^A-Za-z0-9_-]"), "_").take(35).ifBlank { "Film" }
    val values = ContentValues().apply {
      put(MediaStore.Video.Media.DISPLAY_NAME, "MarksAI_" + safe + "_" + stamp + ".mp4")
      put(MediaStore.Video.Media.MIME_TYPE, "video/mp4")
      if (Build.VERSION.SDK_INT >= 29) {
        put(MediaStore.Video.Media.RELATIVE_PATH, "Movies/MarksAI")
        put(MediaStore.Video.Media.IS_PENDING, 1)
      }
    }
    val uri = contentResolver.insert(MediaStore.Video.Media.EXTERNAL_CONTENT_URI, values)
      ?: throw IllegalStateException("Could not create Movies library item")
    try {
      contentResolver.openOutputStream(uri)?.use { out -> FileInputStream(temp).use { it.copyTo(out) } }
        ?: throw IllegalStateException("Could not open Movies output")
      if (Build.VERSION.SDK_INT >= 29) contentResolver.update(uri, ContentValues().apply { put(MediaStore.Video.Media.IS_PENDING, 0) }, null, null)
    } catch (e: Exception) { contentResolver.delete(uri, null, null); throw e }
    return uri.toString()
  }

  private fun draw(bitmap: Bitmap, title: String, idea: String, genre: String, frame: Int, total: Int) {
    val c = Canvas(bitmap); val p = Paint(Paint.ANTI_ALIAS_FLAG)
    val scene = min(4, frame * 5 / total)
    val tops = intArrayOf(Color.rgb(8,20,54), Color.rgb(42,18,65), Color.rgb(12,58,54), Color.rgb(73,31,25), Color.rgb(10,20,32))
    val bottoms = intArrayOf(Color.rgb(40,100,145), Color.rgb(125,55,130), Color.rgb(48,130,100), Color.rgb(180,90,45), Color.rgb(45,70,90))
    for (y in 0 until 180) {
      val t = y / 180f; p.color = Color.rgb(
        (Color.red(tops[scene])*(1-t)+Color.red(bottoms[scene])*t).toInt(),
        (Color.green(tops[scene])*(1-t)+Color.green(bottoms[scene])*t).toInt(),
        (Color.blue(tops[scene])*(1-t)+Color.blue(bottoms[scene])*t).toInt())
      c.drawRect(0f, y.toFloat(), 320f, y+1f, p)
    }
    for (i in 0 until 25) {
      p.color = if (i%4==0) Color.rgb(255,220,150) else Color.LTGRAY
      c.drawCircle(((i*47+frame*(i%3+1))%330).toFloat(), ((i*29)%125).toFloat(), if(i%4==0) 2f else 1f, p)
    }
    p.color = Color.argb(210, 3, 7, 18); c.drawRect(0f, 130f, 320f, 180f, p)
    for (i in 0 until 8) { p.color=Color.argb(90,0,0,0); val x=i*42f-(frame%40); c.drawRect(x,105f-(i%3)*12f,x+25f,151f,p) }
    p.color=Color.WHITE; p.textAlign=Paint.Align.CENTER; p.textSize=17f; p.isFakeBoldText=true
    c.drawText(if(scene==4) "THE END" else title.take(27),160f,61f,p)
    p.isFakeBoldText=false; p.textSize=10f
    c.drawText(arrayOf("OPENING","THE JOURNEY","TURNING POINT","THE CLIMAX","RESOLUTION")[scene],160f,82f,p)
    p.textSize=8f; c.drawText(genre.uppercase(Locale.getDefault())+" • STORYBOARD PREVIEW",160f,164f,p)
    c.drawText(idea.replace('\n',' ').take(52),160f,176f,p)
  }

  private fun toYuv(bitmap: Bitmap): ByteArray {
    val w=bitmap.width; val h=bitmap.height; val pixels=IntArray(w*h)
    bitmap.getPixels(pixels,0,w,0,0,w,h)
    val out=ByteArray(w*h*3/2); var yi=0; var ui=w*h; var vi=ui+w*h/4
    for (y in 0 until h) for (x in 0 until w) {
      val col=pixels[y*w+x]; val r=Color.red(col); val g=Color.green(col); val b=Color.blue(col)
      out[yi++]=(((66*r+129*g+25*b+128 shr 8)+16).coerceIn(0,255)).toByte()
      if(y%2==0 && x%2==0) {
        out[ui++]=(((-38*r-74*g+112*b+128 shr 8)+128).coerceIn(0,255)).toByte()
        out[vi++]=(((112*r-94*g-18*b+128 shr 8)+128).coerceIn(0,255)).toByte()
      }
    }
    return out
  }
}
''', encoding="utf-8")
print("Local MP4 storyboard renderer patch applied.")
