#!/usr/bin/env python3
"""Regression-test production route injection order and idempotency."""
from pathlib import Path
import subprocess
import sys
import tempfile
import shutil

REPO = Path(__file__).resolve().parents[1]
PATCH = REPO / "tools" / "patch_backend_video_generation.py"
ROUTES = REPO / "tools" / "video_generation_routes.js"

with tempfile.TemporaryDirectory(prefix="marks-ai-route-patch-") as temp:
    root = Path(temp)
    (root / "tools").mkdir()
    (root / "build" / "server").mkdir(parents=True)
    shutil.copy2(PATCH, root / "tools" / PATCH.name)
    shutil.copy2(ROUTES, root / "tools" / ROUTES.name)
    server = root / "build" / "server.js"
    server.write_text(
        "const express = require('express');\n"
        "const app = express();\n"
        "app.use(express.json({ limit: '2mb' }));\n"
        "app.use(express.urlencoded({ extended: true }));\n"
        "app.get('/api/health', (_req, res) => res.json({ok:true}));\n"
        "app.listen(3000);\n",
        encoding="utf-8",
    )

    def patch():
        subprocess.run(
            [sys.executable, "tools/patch_backend_video_generation.py"],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        )

    patch()
    content = server.read_text(encoding="utf-8")
    parser_at = content.index("app.use(express.json")
    route_at = content.index("registerVideoGenerationRoutes(app);")
    listen_at = content.index("app.listen(")
    assert parser_at < route_at < listen_at, (
        "Video routes must register after JSON body parsing and before listen()"
    )
    assert content.count("registerVideoGenerationRoutes(app);") == 1
    assert (root / "build" / "server" / "video_generation_routes.js").read_text(
        encoding="utf-8"
    ) == ROUTES.read_text(encoding="utf-8")

    patch()
    content = server.read_text(encoding="utf-8")
    assert content.count("registerVideoGenerationRoutes(app);") == 1, (
        "Running the patch twice must not duplicate route registration"
    )
    assert content.index("app.use(express.json") < content.index(
        "registerVideoGenerationRoutes(app);"
    ) < content.index("app.listen(")

print("PASS: video route patch registers after JSON middleware, before listen(), and is idempotent")
