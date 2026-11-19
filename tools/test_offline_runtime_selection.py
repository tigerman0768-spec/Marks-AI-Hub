#!/usr/bin/env python3
"""Guard the approved offline runtime decision against accidental overclaims."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
doc = ROOT / "docs" / "OFFLINE_RUNTIME_SELECTION.md"
text = doc.read_text(encoding="utf-8")
required = [
    "LiteRT-LM Android/Kotlin API",
    "LiteRT Runtime",
    "model file remains a separate",
    "complete upstream licence",
    "airplane-mode tests",
    "does not mean the runtime has been integrated",
    "does not promise full-length photorealistic video diffusion",
]
missing = [item for item in required if item not in text]
for item in required:
    print(("PASS" if item in text else "FAIL") + ": " + item)
if missing:
    raise SystemExit("Missing runtime decision safeguards: " + ", ".join(missing))
print("PASS: offline runtime selection safeguards.")
