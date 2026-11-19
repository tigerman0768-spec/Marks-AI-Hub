#!/usr/bin/env python3
"""Install the offline model-pack capability/integrity bridge into the Flutter app."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app"
LIB = APP / "lib"
ANDROID = APP / "android"
if not (LIB / "main.dart").is_file():
    raise SystemExit("Flutter app/lib/main.dart is missing")

candidates = list((ANDROID / "app" / "src" / "main").rglob("MainActivity.kt")) + list((ANDROID / "app" / "src" / "main").rglob("MainActivity.java"))
if len(candidates) != 1:
    raise SystemExit(f"Expected exactly one Android MainActivity source; found {len(candidates)}")
main = candidates[0]
if main.suffix != ".kt":
    raise SystemExit("Offline model bridge currently requires the Kotlin Flutter MainActivity; Java activity is not modified")

source = main.read_text(encoding="utf-8")
package_match = re.search(r"^package\s+([\w.]+)", source, re.M)
if not package_match:
    raise SystemExit("Could not determine Android package from MainActivity.kt")
package_name = package_match.group(1)
bridge = main.parent / "OfflineModelPackBridge.kt"
bridge.write_text(f'''package {package_name}

import android.app.ActivityManager
import android.content.Context
import android.os.Build
import android.os.StatFs
import io.flutter.plugin.common.BinaryMessenger
import io.flutter.plugin.common.MethodChannel
import java.io.File
import java.io.FileInputStream
import java.security.MessageDigest

/**
 * Local-only model pack diagnostics. This does NOT load or execute model weights.
 * Paths are restricted to the app-private files directory.
 */
object OfflineModelPackBridge {{
    private const val CHANNEL = "marks_ai/offline_models"

    fun register(messenger: BinaryMessenger, context: Context) {{
        MethodChannel(messenger, CHANNEL).setMethodCallHandler {{ call, result ->
            when (call.method) {{
                "getCapabilities" -> result.success(capabilities(context))
                "verifyModelFile" -> {{
                    val relative = call.argument<String>("relativePath")
                    val expected = call.argument<String>("expectedSha256")
                    if (relative.isNullOrBlank() || expected.isNullOrBlank()) {{
                        result.error("INVALID_ARGUMENT", "relativePath and expectedSha256 are required", null)
                    }} else {{
                        try {{
                            result.success(verifyFile(context, relative, expected))
                        }} catch (e: Exception) {{
                            result.error("MODEL_VERIFY_FAILED", e.message ?: "Model file verification failed", null)
                        }}
                    }}
                }}
                else -> result.notImplemented()
            }}
        }}
    }}

    private fun capabilities(context: Context): Map<String, Any> {{
        val activity = context.getSystemService(Context.ACTIVITY_SERVICE) as ActivityManager
        val memory = ActivityManager.MemoryInfo()
        activity.getMemoryInfo(memory)
        val storage = StatFs(context.filesDir.absolutePath)
        return mapOf(
            "androidApi" to Build.VERSION.SDK_INT,
            "deviceModel" to Build.MODEL.orEmpty(),
            "manufacturer" to Build.MANUFACTURER.orEmpty(),
            "supportedAbis" to Build.SUPPORTED_ABIS.toList(),
            "totalRamBytes" to memory.totalMem,
            "availableRamBytes" to memory.availMem,
            "lowMemory" to memory.lowMemory,
            "appPrivateFreeBytes" to storage.availableBytes,
            "runtimeIntegrated" to false,
            "modelInferenceReady" to false
        )
    }}

    private fun verifyFile(context: Context, relativePath: String, expectedSha256: String): Map<String, Any> {{
        require(expectedSha256.matches(Regex("^[a-fA-F0-9]{{64}}$"))) {{ "Expected SHA-256 must contain 64 hexadecimal characters" }}
        val root = context.filesDir.canonicalFile
        val candidate = File(root, relativePath).canonicalFile
        require(candidate.path.startsWith(root.path + File.separator)) {{ "Model file path escapes app-private storage" }}
        require(candidate.isFile && candidate.canRead()) {{ "Model file is missing or unreadable" }}
        val digest = MessageDigest.getInstance("SHA-256")
        FileInputStream(candidate).use {{ input ->
            val buffer = ByteArray(1024 * 1024)
            while (true) {{
                val count = input.read(buffer)
                if (count <= 0) break
                digest.update(buffer, 0, count)
            }}
        }}
        val actual = digest.digest().joinToString("") {{ "%02x".format(it) }}
        return mapOf(
            "valid" to actual.equals(expectedSha256, ignoreCase = true),
            "sha256" to actual,
            "sizeBytes" to candidate.length(),
            "relativePath" to root.toPath().relativize(candidate.toPath()).toString()
        )
    }}
}}
''', encoding="utf-8")

if "OfflineModelPackBridge.register(" not in source:
    if "import io.flutter.embedding.engine.FlutterEngine" not in source:
        package_line = re.search(r"^package[^\\n]*\\n", source, re.M)
        if not package_line:
            raise SystemExit("MainActivity package declaration not found")
        source = source[:package_line.end()] + "import io.flutter.embedding.engine.FlutterEngine\\n" + source[package_line.end():]

    method = re.search(r"override\\s+fun\\s+configureFlutterEngine\\s*\\(\\s*flutterEngine\\s*:\\s*FlutterEngine\\s*\\)\\s*\\{", source)
    registration = "OfflineModelPackBridge.register(flutterEngine.dartExecutor.binaryMessenger, applicationContext)"
    if method:
        depth = 1
        cursor = method.end()
        while cursor < len(source) and depth:
            if source[cursor] == "{": depth += 1
            elif source[cursor] == "}": depth -= 1
            cursor += 1
        if depth:
            raise SystemExit("Could not find end of existing configureFlutterEngine method")
        source = source[:cursor-1] + "\\n        " + registration + "\\n    " + source[cursor-1:]
    else:
        pos = source.rfind("}")
        if pos < 0:
            raise SystemExit("MainActivity class closing brace not found")
        hook = "\\n    override fun configureFlutterEngine(flutterEngine: FlutterEngine) {\\n        super.configureFlutterEngine(flutterEngine)\\n        " + registration + "\\n    }\\n"
        source = source[:pos] + hook + source[pos:]
    main.write_text(source, encoding="utf-8")

dart = r'''import 'package:flutter/services.dart';

/// Local-only Android model-pack diagnostics and integrity verification.
///
/// This service deliberately does not claim to load or run a model. A model
/// inference runtime and a compatible, licensed model pack are separate gates.
class OfflineModelPackService {
  static const MethodChannel _channel = MethodChannel('marks_ai/offline_models');

  Future<Map<String, dynamic>> getCapabilities() async {
    final result = await _channel.invokeMapMethod<String, dynamic>('getCapabilities');
    if (result == null) throw StateError('Android model capability response was empty');
    return Map<String, dynamic>.from(result);
  }

  /// Verifies a model file already inside app-private storage.
  /// The path must be relative to the app's private files directory.
  Future<Map<String, dynamic>> verifyModelFile({
    required String relativePath,
    required String expectedSha256,
  }) async {
    final result = await _channel.invokeMapMethod<String, dynamic>(
      'verifyModelFile',
      {'relativePath': relativePath, 'expectedSha256': expectedSha256},
    );
    if (result == null) throw StateError('Android model verification response was empty');
    return Map<String, dynamic>.from(result);
  }
}
'''
(LIB / "offline_model_pack_service.dart").write_text(dart, encoding="utf-8")
print("Installed Android offline model capability and SHA-256 verification bridge.")
print("NOTE: This is pack diagnostics only; it does not load model weights or perform inference.")
