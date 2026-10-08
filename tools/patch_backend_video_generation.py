#!/usr/bin/env python3
from pathlib import Path
import re

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
    patterns = [
        r"const app = express\(\);", r"let app = express\(\);", r"var app = express\(\);",
        r"const app = \(0, express_1\.default\)\(\);", r"let app = \(0, express_1\.default\)\(\);", r"var app = \(0, express_1\.default\)\(\);",
        r"const app = express_1\.default\(\);", r"let app = express_1\.default\(\);", r"var app = express_1\.default\(\);",
        r"const app = require\(['\"]express['\"]\)\(\);",
    ]
    hit = next((p for p in patterns if re.search(p, text)), None)
    if hit:
        text = re.sub(hit, lambda m: m.group(0) + "\n" + registration, text, count=1)
    elif "app.listen(" in text:
        text = text.replace("app.listen(", registration + "\napp.listen(", 1)
    else:
        raise SystemExit("Could not find an Express app declaration or app.listen() in build/server.js")

server_js.write_text(text, encoding="utf-8")
target = root / "server" / "video_generation_routes.js"
target.parent.mkdir(parents=True, exist_ok=True)
target.write_text(route_source.read_text(encoding="utf-8"), encoding="utf-8")
print("Video generation routes patched into build/server.js")
