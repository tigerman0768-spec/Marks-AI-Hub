#!/usr/bin/env python3
"""Source-level tests for the Android offline model-pack bridge."""
from pathlib import Path

root = Path(__file__).resolve().parents[1]
patch = (root / "tools" / "v2640_add_offline_model_pack_bridge.py").read_text(encoding="utf-8")
checks = [
    ("Android bridge reports hardware and memory capabilities", '"getCapabilities"' in patch and "totalRamBytes" in patch and "supportedAbis" in patch),
    ("model integrity uses SHA-256", 'MessageDigest.getInstance("SHA-256")' in patch),
    ("model paths are confined to app-private storage", 'candidate.path.startsWith(root.path + File.separator)' in patch),
    ("Flutter channel is local and stable", "marks_ai/offline_models" in patch),
    ("inference is not falsely advertised as ready", '"modelInferenceReady" to false' in patch),
    ("bridge explicitly disclaims model inference", "does not load or run a model" in patch),
    ("Dart service exposes capability and integrity calls", "getCapabilities()" in patch and "verifyModelFile(" in patch),
]
failed = []
for label, ok in checks:
    print(("PASS" if ok else "FAIL") + ": " + label)
    if not ok: failed.append(label)
if failed: raise SystemExit("Offline bridge tests failed: " + "; ".join(failed))
print("PASS: offline model-pack bridge source checks.")
