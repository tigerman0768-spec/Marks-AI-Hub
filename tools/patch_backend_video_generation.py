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
# Express parses request bodies in middleware such as express.json(). Register
# these routes immediately before listen(), not beside app creation, so they
# cannot accidentally run before the JSON parser and other middleware.
text = re.sub(r"(?m)^\s*registerVideoGenerationRoutes\(app\);\s*\n?", "", text)

# Fail closed if the extracted backend has no JSON body parser: otherwise
# POST /api/video/generate could see an empty req.body even with valid JSON.
parser_patterns = [r"app\.use\s*\(\s*express\.json\s*\(", r"app\.use\s*\(\s*bodyParser\.json\s*\("]
parser_matches = [re.search(pattern, text) for pattern in parser_patterns]
parser_matches = [match for match in parser_matches if match]
if not parser_matches:
    raise SystemExit("Could not find express.json() or bodyParser.json() middleware in build/server.js")
last_parser_position = max(match.start() for match in parser_matches)

listen = re.search(r"(?m)^([^\\n]*\\bapp\\.listen\\s*\\()", text)
if listen:
    line_start = listen.start()
    text = text[:line_start] + registration + "\n" + text[line_start:]
else:
    # Support source layouts whose listen call is not on a line by itself.
    if "app.listen(" not in text:
        raise SystemExit("Could not find app.listen() in build/server.js to register video routes after middleware")
    text = text.replace("app.listen(", registration + "\napp.listen(", 1)

registration_position = text.find(registration)
listen_position = text.find("app.listen(")
if registration_position < last_parser_position:
    raise SystemExit("Video routes were inserted before JSON body parsing middleware")
if listen_position < 0 or registration_position > listen_position:
    raise SystemExit("Video routes must be registered before app.listen()")

server_js.write_text(text, encoding="utf-8")
target = root / "server" / "video_generation_routes.js"
target.parent.mkdir(parents=True, exist_ok=True)
target.write_text(route_source.read_text(encoding="utf-8"), encoding="utf-8")
print("Video generation routes patched after middleware, immediately before app.listen()")
