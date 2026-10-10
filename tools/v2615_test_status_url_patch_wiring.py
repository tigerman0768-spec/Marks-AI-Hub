from pathlib import Path
import sys

root = Path(__file__).resolve().parents[1]
workflow = root / ".github" / "workflows" / "build-apk-v2591-hybrid-repair.yml"
patch = root / "tools" / "v2614_fix_status_url_base_path.py"
if not workflow.is_file() or not patch.is_file():
    raise SystemExit("Workflow or v2614 patch script is missing")
w = workflow.read_text(encoding="utf-8")
p = patch.read_text(encoding="utf-8")
checks = {
    "workflow watches v2614 changes": "tools/v2614_fix_status_url_base_path.py" in w,
    "workflow applies v2614": "python3 ../tools/v2614_fix_status_url_base_path.py" in w,
    "patch preserves configured URL prefix": "endpointPath.substring" in p and "basePath + '/api/video/status/'" in p,
    "patch URL-encodes task IDs": "Uri.encodeComponent(activeTask)" in p,
    "patch refuses unknown source rather than overwriting blindly": "No supported status URL construction found" in p,
    "patch accepts already-correct current downloader source": "Current status URL implementation already preserves API and base paths" in p,
}
failed = [name for name, ok in checks.items() if not ok]
for name, ok in checks.items():
    print(("PASS: " if ok else "FAIL: ") + name)
if failed:
    print("Status URL regression checks failed: " + ", ".join(failed), file=sys.stderr)
    raise SystemExit(1)
print("All v2614 workflow regression checks passed.")
