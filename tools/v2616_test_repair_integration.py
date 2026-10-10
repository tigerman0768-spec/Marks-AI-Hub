from pathlib import Path
import sys

root = Path(__file__).resolve().parents[1]
workflow = root / ".github" / "workflows" / "build-apk-v2591-hybrid-repair.yml"
preflight = root / "tools" / "v2613_preflight_repair_scripts.py"
status_patch = root / "tools" / "v2614_fix_status_url_base_path.py"
w = workflow.read_text(encoding="utf-8")
pf = preflight.read_text(encoding="utf-8")
sp = status_patch.read_text(encoding="utf-8")
required_scripts = [
    "v2613_preflight_repair_scripts.py",
    "v2614_fix_status_url_base_path.py",
    "v2615_test_status_url_patch_wiring.py",
]
checks = {
    "workflow watches v2615 test changes": "tools/v2615_test_status_url_patch_wiring.py" in w,
    "workflow runs v2615 test after v2614 patch": w.find("python3 ../tools/v2614_fix_status_url_base_path.py") < w.find("python3 ../tools/v2615_test_status_url_patch_wiring.py"),
    "preflight checks v2614": '"v2614_fix_status_url_base_path.py"' in pf,
    "preflight checks v2615": '"v2615_test_status_url_patch_wiring.py"' in pf,
    "v2614 is a single, guarded source replacement": "Could not locate status URL construction" in sp and "if new in s" in sp,
    "v2614 keeps task identifier encoded": "Uri.encodeComponent(activeTask)" in sp,
}
errors = [name for name, ok in checks.items() if not ok]
for name, ok in checks.items():
    print(("PASS: " if ok else "FAIL: ") + name)
if errors:
    print("Repair integration validation failed:", *errors, sep="\n - ", file=sys.stderr)
    raise SystemExit(1)
print("Repair integration validation passed.")
