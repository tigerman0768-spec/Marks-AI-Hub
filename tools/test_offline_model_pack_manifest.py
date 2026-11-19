#!/usr/bin/env python3
"""Validate the offline model-pack manifest contract without third-party packages."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
schema_path = ROOT / "assets" / "model_packs" / "manifest.schema.json"
example_path = ROOT / "assets" / "model_packs" / "manifest.example.json"
schema = json.loads(schema_path.read_text(encoding="utf-8"))
pack = json.loads(example_path.read_text(encoding="utf-8"))

checks = [
    ("schema declares JSON Schema 2020-12", schema.get("$schema", "").endswith("2020-12/schema")),
    ("schema requires offlineOnly", "offlineOnly" in schema.get("required", [])),
    ("example declares offline-only mode", pack.get("offlineOnly") is True),
    ("example has a supported model role", pack.get("role") in {"text", "image", "motion", "speech", "audio"}),
    ("example includes at least one asset", isinstance(pack.get("files"), list) and bool(pack["files"])),
    ("example includes hardware requirements", all(k in pack.get("requirements", {}) for k in ("minimumRamBytes", "recommendedRamBytes", "minimumFreeStorageBytes", "androidApiMin", "abis"))),
    ("example includes explicit licence metadata", all(k in pack.get("licence", {}) for k in ("modelName", "source", "licenceId", "redistributionAllowed", "commercialUseAllowed", "attribution"))),
    ("example is clearly marked as a non-installable placeholder", "not installed" in pack.get("name", "").lower() and "placeholder" in " ".join(pack.get("safetyNotes", [])).lower()),
]
for asset in pack.get("files", []):
    path = Path(asset.get("path", ""))
    checks.append(("asset path is relative and traversal-safe", not path.is_absolute() and ".." not in path.parts))
    checks.append(("asset has a positive declared size", isinstance(asset.get("sizeBytes"), int) and asset["sizeBytes"] > 0))
    checks.append(("asset has a SHA-256 digest", bool(re.fullmatch(r"[0-9a-fA-F]{64}", asset.get("sha256", "")))))

failed = []
for label, ok in checks:
    print(("PASS" if ok else "FAIL") + ": " + label)
    if not ok:
        failed.append(label)
if failed:
    raise SystemExit("Offline model-pack manifest validation failed: " + "; ".join(failed))
print("PASS: offline model-pack manifest contract.")
