#!/usr/bin/env python3
from pathlib import Path

root = Path("build")
server_js = root / "server.js"
route_source = Path("tools/video_generation_routes.js")
if not server_js.exists():
    raise SystemExit("build/server.js not found")
if not route_source.exists():
    raise SystemExit("tools/video_generation_routes.js not found")

text = server_js.read_text(encoding="utf-8")
marker = "const { registerVideoGenerationRoutes } = require('./server/video_generation_routes');"
if marker not in text:
    text = marker + "\n" + text

registration = "registerVideoGenerationRoutes(app);"
if registration not in text:
    candidates = ["const app = express();", "let app = express();", "var app = express();"]
    hit = next((c for c in candidates if c in text), None)
    if not hit:
        raise SystemExit("Could not find Express app declaration in build/server.js")
    text = text.replace(hit, hit + "\n" + registration, 1)

server_js.write_text(text, encoding="utf-8")
target = root / "server" / "video_generation_routes.js"
target.parent.mkdir(parents=True, exist_ok=True)
target.write_text(route_source.read_text(encoding="utf-8"), encoding="utf-8")
print("Video generation routes patched into build/server.js")
