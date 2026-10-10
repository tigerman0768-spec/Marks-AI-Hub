from pathlib import Path

p = Path(__file__).resolve().parents[1] / "app" / "lib" / "scene_prompt_screen.dart"
if not p.exists():
    raise SystemExit("scene_prompt_screen.dart not found")
s = p.read_text(encoding="utf-8")

# v2605 already introduced a guarded status decoder. Do not insist on the
# pre-v2605 one-line form, because that would make the repair pipeline fail
# even when the malformed-JSON recovery is already present.
if "v2609 malformed status recovery" in s:
    print("v2609 malformed status recovery already applied")
    raise SystemExit(0)
if "Invalid video status response:" in s and "status = jsonDecode(statusBody);" in s:
    print("Existing guarded status JSON recovery is already present")
    raise SystemExit(0)

needle = "          final dynamic status = jsonDecode(statusBody);"
if needle not in s:
    raise SystemExit("No supported status decoder found; refusing unsafe patch")
replacement = """          // v2609 malformed status recovery: proxies can briefly return HTML or partial JSON.
          dynamic status;
          try {
            status = jsonDecode(statusBody);
            if (status is! Map) throw const FormatException('Status response must be a JSON object');
          } catch (e) {
            scene['status'] = 'failed';
            scene['error'] = 'Invalid video status response: ' + e.toString();
            scene['generationFailureAt'] = DateTime.now().toIso8601String();
            scene['generationFailureType'] = e.runtimeType.toString();
            failed++;
            finished = true;
            break;
          }"""
p.write_text(s.replace(needle, replacement, 1), encoding="utf-8")
print("v2609 added guarded status JSON recovery.")
