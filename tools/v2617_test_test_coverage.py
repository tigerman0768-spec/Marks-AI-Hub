from pathlib import Path
import sys

root = Path(__file__).resolve().parents[1]
workflow = root / ".github/workflows/build-apk-v2591-hybrid-repair.yml"
preflight = root / "tools/v2613_preflight_repair_scripts.py"
integration = root / "tools/v2616_test_repair_integration.py"
status_patch = root / "tools/v2614_fix_status_url_base_path.py"
w = workflow.read_text(encoding="utf-8")
pf = preflight.read_text(encoding="utf-8")
it = integration.read_text(encoding="utf-8")
sp = status_patch.read_text(encoding="utf-8")
checks = {
    "workflow watches this test": "tools/v2617_test_test_coverage.py" in w,
    "workflow executes test after integration test": w.find("python3 ../tools/v2616_test_repair_integration.py") < w.find("python3 ../tools/v2617_test_test_coverage.py"),
    "preflight checks v2616 integration test": '"v2616_test_repair_integration.py"' in pf,
    "v2616 integration test checks workflow order": "workflow runs v2615 test after v2614 patch" in it,
    "v2614 URL encoding assertion exists": "Uri.encodeComponent(activeTask)" in sp,
    "v2614 safely rejects unsupported source and recognizes current source": "No supported status URL construction found" in sp and "Current status URL implementation already preserves API and base paths" in sp,
}
failed = [k for k,v in checks.items() if not v]
for k,v in checks.items():
    print(("PASS: " if v else "FAIL: ") + k)
if failed:
    print("Test coverage audit failed:", *failed, sep="\n - ", file=sys.stderr)
    raise SystemExit(1)
print("Test coverage audit passed.")
