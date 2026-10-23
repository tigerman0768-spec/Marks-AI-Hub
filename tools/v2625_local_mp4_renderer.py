from pathlib import Path

root = Path("app")
screen = root / "lib" / "film_creator_screen.dart"
if not screen.exists():
    raise SystemExit("Film Creator source not found")
s = screen.read_text()

if "marks_ai/local_video" not in s:
    s = s.replace(
        "import 'package:flutter/material.dart';",
        "import 'package:flutter/material.dart';\nimport 'package:flutter/services.dart';",
        1,
    )

old = """      if (_baseUrl().isEmpty) {
        throw Exception('Real AI film generation needs your deployed Mark’s AI backend URL. Your project is still saved on this phone.');
      }"""
new = """      if (_baseUrl().isEmpty) {
        await _generateLocalFilm();
        return;
      }"""
if old in s:
    s = s.replace(old, new, 1)
elif "await _generateLocalFilm();" not in s:
    raise SystemExit("Could not locate Film Creator backend-required branch")

marker = "  Future<void> _generateFilm() async {"
method = r'''
  Future<void> _generateLocalFilm() async {
    if (idea.text.trim().isEmpty) {
      throw Exception('Please describe the story before generating your film.');
    }
    if (mounted) setState(() => status = 'Rendering your film locally on this phone…');
    final result = await const MethodChannel('marks_ai/local_video').invokeMethod<String>(
      'renderFilm',
      <String, dynamic>{
        'title': title.text.trim().isEmpty ? 'My Film' : title.text.trim(),
        'idea': idea.text.trim(),
        'genre': genre,
        'style': style,
        'lengthMinutes': length,
        'aspectRatio': aspect,
      },
    );
    if (result == null || result.isEmpty) {
      throw Exception('The video renderer did not return a saved MP4.');
    }
    filmUrl = result;
    await _saveState('local_render_complete');
    if (!mounted) return;
    await showDialog<void>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Local film created'),
        content: SelectableText(
          'A locally rendered animated storyboard film has been saved. It uses your story text to create visual title and scene cards; it is not AI-generated live-action footage.\\n\\nSaved to:\\n$result',
        ),
        actions: [
          TextButton(onPressed: () => Navigator.of(context).pop(), child: const Text('CLOSE')),
        ],
      ),
    );
  }

'''
if "Future<void> _generateLocalFilm()" not in s:
    if marker not in s:
        raise SystemExit("Film generation method marker missing")
    s = s.replace(marker, method + marker, 1)

screen.write_text(s)

android = root / "android" / "app" / "src" / "main" / "kotlin" / "com" / "marksai" / "app" / "MainActivity.kt"
if not android.exists():
    # Host preparation currently generates this namespace in this project.
    android.parent.mkdir(parents=True, exist_ok=True)
    android.write_text("package com.marksai.app\n\nimport io.flutter.embedding.android.FlutterActivity\n\nclass MainActivity : FlutterActivity()\n")

kotlin = r'''package com.marksai.app

import android.content.ContentValues
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Paint
import android.graphics.RectF
import android.media.MediaCodec
import android.media.MediaCodecInfo
import android.media.MediaFormat
import android.media.MediaMuxer
import android.net.Uri
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
import java.util.concurrent.Executors
import kotlin.math.max

class MainActivity : FlutterActivity() {
    private val channelName = "marks_ai/local_video"
    private val executor = Executors.newSingleThreadExecutor()

    override fun configureFlutterEngine(flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)
        MethodChannel(flutterEngine.dartExecutor.binaryMessenger, channelName).setMethodCallHandler { call, result ->
            if (call.method != "renderFilm") {
                result.notImplemented()
                return@setMethodCallHandler
            }
            val args = call.arguments as? Map<*, *> ?: emptyMap<Any, Any>()
            val title = args["title"]?.toString()?.take(100) ?: "My Film"
            val idea = args["idea"]?.toString()?.take(2000) ?: ""
            val genre = args["genre"]?.toString() ?: "Drama"
            val style = args["style"]?.toString() ?: "Cinematic"
            val minutes = (args["lengthMinutes"] as? Number)?.toInt()?.coerceIn(1, 60) ?: 1
            executor.execute {
                try {
                    val file = renderStoryboard(title, idea, genre, style, minutes)
                    val saved = publishVideo(file, title)
                    runOnUiThread { result.success(saved.toString()) }
                } catch (e: Exception) {
                    runOnUiThread { result.error("LOCAL_RENDER_FAILED", e.message ?: "MP4 render failed", null) }
                }
            }
        }
    }

    private fun renderStoryboard(title: String, idea: String, genre: String, style: String, minutes: Int): File {
        val width = 640
        val height = 360
        val fps = 2
        val totalFrames = minutes * 60 * fps
        val outputDir = File(cacheDir, "marks_ai_render")
        if (!outputDir.exists()) outputDir.mkdirs()
        val safeTitle = title.replace(Regex("[^A-Za-z0-9_-]"), "_").take(40).ifBlank { "film" }
        val out = File(outputDir, safeTitle + "_" + System.currentTimeMillis() + ".mp4")
        val format = MediaFormat.createVideoFormat(MediaFormat.MIMETYPE_VIDEO_AVC, width, height)
        format.setInteger(MediaFormat.KEY_COLOR_FORMAT, MediaCodecInfo.CodecCapabilities.COLOR_FormatSurface)
        format.setInteger(MediaFormat.KEY_BIT_RATE, 1_500_000)
        format.setInteger(MediaFormat.KEY_FRAME_RATE, fps)
        format.setInteger(MediaFormat.KEY_I_FRAME_INTERVAL, 2)
        val codec = MediaCodec.createEncoderByType(MediaFormat.MIMETYPE_VIDEO_AVC)
        var muxer: MediaMuxer? = null
        var muxerStarted = false
        var trackIndex = -1
        try {
            codec.configure(format, null, null, MediaCodec.CONFIGURE_FLAG_ENCODE)
            val surface = codec.createInputSurface()
            codec.start()
            muxer = MediaMuxer(out.absolutePath, MediaMuxer.OutputFormat.MUXER_OUTPUT_MPEG_4)
            val info = MediaCodec.BufferInfo()
            val paint = Paint(Paint.ANTI_ALIAS_FLAG).apply { textAlign = Paint.Align.CENTER }
            val scenes = splitScenes(idea)
            for (frame in 0 until totalFrames) {
                val canvas: Canvas = surface.lockCanvas(null)
                try {
                    drawScene(canvas, paint, title, genre, style, scenes[((frame.toLong() * scenes.size) / totalFrames).toInt().coerceIn(0, scenes.lastIndex)], frame, totalFrames, width, height)
                } finally {
                    surface.unlockCanvasAndPost(canvas)
                }
                drain(codec, muxer, info, false) { idx, fmt ->
                    if (muxerStarted) throw IllegalStateException("Encoder output format changed twice")
                    trackIndex = muxer!!.addTrack(fmt)
                    muxer!!.start()
                    muxerStarted = true
                } { idx, data, bufferInfo ->
                    if (muxerStarted && bufferInfo.size > 0) {
                        data.position(bufferInfo.offset)
                        data.limit(bufferInfo.offset + bufferInfo.size)
                        muxer!!.writeSampleData(trackIndex, data, bufferInfo)
                    }
                }
            }
            codec.signalEndOfInputStream()
            drain(codec, muxer, info, true) { _, fmt ->
                if (!muxerStarted) {
                    trackIndex = muxer!!.addTrack(fmt)
                    muxer!!.start()
                    muxerStarted = true
                }
            } { _, data, bufferInfo ->
                if (muxerStarted && bufferInfo.size > 0) {
                    data.position(bufferInfo.offset)
                    data.limit(bufferInfo.offset + bufferInfo.size)
                    muxer!!.writeSampleData(trackIndex, data, bufferInfo)
                }
            }
            if (!muxerStarted || !out.exists() || out.length() < 1024) {
                throw IllegalStateException("The MP4 encoder did not produce a valid video file")
            }
            return out
        } finally {
            try { codec.stop() } catch (_: Exception) {}
            codec.release()
            try { muxer?.stop() } catch (_: Exception) {}
            muxer?.release()
        }
    }

    private fun drain(
        codec: MediaCodec,
        muxer: MediaMuxer?,
        info: MediaCodec.BufferInfo,
        end: Boolean,
        onFormat: (Int, MediaFormat) -> Unit,
        onBuffer: (Int, java.nio.ByteBuffer, MediaCodec.BufferInfo) -> Unit
    ) {
        var idle = 0
        while (true) {
            val index = codec.dequeueOutputBuffer(info, if (end) 10_000 else 0)
            when {
                index == MediaCodec.INFO_TRY_AGAIN_LATER -> {
                    if (!end || ++idle > 100) return
                }
                index == MediaCodec.INFO_OUTPUT_FORMAT_CHANGED -> onFormat(index, codec.outputFormat)
                index >= 0 -> {
                    val buffer = codec.getOutputBuffer(index)
                    if (buffer != null && info.size > 0 && info.flags and MediaCodec.BUFFER_FLAG_CODEC_CONFIG == 0) {
                        onBuffer(index, buffer, info)
                    }
                    val finished = info.flags and MediaCodec.BUFFER_FLAG_END_OF_STREAM != 0
                    codec.releaseOutputBuffer(index, false)
                    if (finished) return
                }
            }
        }
    }

    private fun splitScenes(idea: String): List<String> {
        val clean = idea.replace(Regex("\\s+"), " ").trim()
        val words = clean.split(" ").filter { it.isNotBlank() }
        if (words.isEmpty()) return listOf("A new story begins.")
        val chunk = max(1, words.size / 5)
        return (0 until words.size step chunk).take(6).map { start ->
            words.drop(start).take(chunk + 3).joinToString(" ").take(220)
        }.ifEmpty { listOf(clean.take(220)) }
    }

    private fun drawScene(
        canvas: Canvas, paint: Paint, title: String, genre: String, style: String,
        scene: String, frame: Int, totalFrames: Int, width: Int, height: Int
    ) {
        val phase = frame.toFloat() / max(1, totalFrames)
        val colors = intArrayOf(Color.rgb(10, 18, 42), Color.rgb(35, 20, 62), Color.rgb(10, 46, 58), Color.rgb(54, 24, 30))
        val bg = colors[(frame / max(1, totalFrames / colors.size)) % colors.size]
        canvas.drawColor(bg)
        paint.color = Color.argb(70, 255, 255, 255)
        paint.style = Paint.Style.STROKE
        paint.strokeWidth = 1f
        for (i in 0..9) {
            val x = ((i * 79 + frame * 3) % (width + 50)).toFloat()
            val y = ((i * 43 + frame * 2) % height).toFloat()
            canvas.drawCircle(x, y, 5f + (i % 3), paint)
        }
        paint.style = Paint.Style.FILL
        paint.color = Color.rgb(230, 187, 110)
        canvas.drawRoundRect(RectF(42f, 38f, 598f, 43f), 3f, 3f, paint)
        paint.color = Color.WHITE
        paint.textSize = 13f
        canvas.drawText(genre.uppercase(Locale.getDefault()) + "  •  " + style.uppercase(Locale.getDefault()), width / 2f, 68f, paint)
        paint.textSize = 29f
        paint.isFakeBoldText = true
        canvas.drawText(title.take(36), width / 2f, 126f, paint)
        paint.isFakeBoldText = false
        paint.color = Color.rgb(230, 187, 110)
        canvas.drawRoundRect(RectF(120f, 148f, 520f, 150f), 1f, 1f, paint)
        paint.color = Color.WHITE
        paint.textSize = 18f
        val lines = wrap(scene, 48)
        lines.take(4).forEachIndexed { index, line -> canvas.drawText(line, width / 2f, 190f + index * 25f, paint) }
        paint.color = Color.argb(190, 255, 255, 255)
        paint.textSize = 11f
        canvas.drawText("SCENE " + (frame / max(1, totalFrames / 5) + 1).coerceAtMost(5) + "   •   " + String.format(Locale.US, "%02d:%02d", frame / (2 * 60), (frame / 2) % 60), width / 2f, 328f, paint)
        paint.color = Color.rgb(230, 187, 110)
        canvas.drawRect(42f, 340f, 42f + 556f * phase, 344f, paint)
    }

    private fun wrap(text: String, limit: Int): List<String> {
        val result = mutableListOf<String>()
        var line = ""
        for (word in text.split(" ")) {
            if ((line + " " + word).trim().length > limit && line.isNotEmpty()) {
                result.add(line)
                line = word
            } else line = (line + " " + word).trim()
        }
        if (line.isNotEmpty()) result.add(line)
        return result
    }

    private fun publishVideo(source: File, title: String): Uri {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            val values = ContentValues().apply {
                put(MediaStore.Video.Media.DISPLAY_NAME, source.name)
                put(MediaStore.Video.Media.MIME_TYPE, "video/mp4")
                put(MediaStore.Video.Media.RELATIVE_PATH, "Movies/Marks AI")
                put(MediaStore.Video.Media.IS_PENDING, 1)
            }
            val uri = contentResolver.insert(MediaStore.Video.Media.EXTERNAL_CONTENT_URI, values)
                ?: throw IllegalStateException("Could not create a Gallery entry for the MP4")
            try {
                contentResolver.openOutputStream(uri)?.use { output ->
                    FileInputStream(source).use { input -> input.copyTo(output) }
                } ?: throw IllegalStateException("Could not open the Gallery output stream")
                values.clear()
                values.put(MediaStore.Video.Media.IS_PENDING, 0)
                contentResolver.update(uri, values, null, null)
                return uri
            } catch (e: Exception) {
                contentResolver.delete(uri, null, null)
                throw e
            }
        }
        return Uri.fromFile(source)
    }

    override fun onDestroy() {
        executor.shutdown()
        super.onDestroy()
    }
}
'''
android.write_text(kotlin)
print("Added local animated-storyboard MP4 renderer and Gallery publishing bridge.")
