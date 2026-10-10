from pathlib import Path
import sys

root = Path(__file__).resolve().parents[1]
workflow_path = root / ".github/workflows/build-apk-v2591-hybrid-repair.yml"
preflight_path = root / "tools/v2613_preflight_repair_scripts.py"
coverage_path = root / "tools/v2617_test_test_coverage.py"
workflow = workflow_path.read_text(encoding="utf-8")
preflight = preflight_path.read_text(encoding="utf-8")
coverage = coverage_path.read_text(encoding="utf-8")
checks = {
    "workflow watches v2617 audit": "tools/v2617_test_test_coverage.py" in workflow,
    "workflow executes v2617 audit": "python3 ../tools/v2617_test_test_coverage.py" in workflow,
    "preflight includes v2617 audit": '"v2617_test_test_coverage.py"' in preflight,
    "audit is not self-recursive": "v2618_test_build_guard_coverage.py" not in coverage,
    "audit checks real build command is present": "flutter build apk --release" in workflow,
    "workflow verifies and checksums APK": "sha256sum build/install/Mark_s_AI_v2604.apk" in workflow,
    "workflow uploads APK artifact": "actions/upload-artifact@v4" in workflow and "Marks-AI-v2604-LOCAL-VIDEO-ROUTE-APK" in workflow,
}
failed = [name for name, ok in checks.items() if not ok]
for name, ok in checks.items():
    print(("PASS: " if ok else "FAIL: ") + name)
if failed:
    print("Build guard coverage failed:", *failed, sep="\n - ", file=sys.stderr)
    raise SystemExit(1)
print("Build guard coverage passed.")
