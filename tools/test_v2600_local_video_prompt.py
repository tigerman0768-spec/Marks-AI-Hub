from pathlib import Path

source = Path("tools/v2600_add_local_video_studio.py").read_text(encoding="utf-8")
checks = {
    "forest prompt keywords": all(word in source for word in ["'dog'", "'forest'", "'walking'", "'park'"]),
    "sci-fi prompt keywords": all(word in source for word in ["'spaceship'", "'planet'", "'galaxy'"]),
    "timelapse fallback": "return LocalFilmStyle.timelapse" in source,
    "live prompt feedback": "onChanged: (value)" in source and "_styleForPrompt(value)" in source,
    "visible selected-template label": "'Best matching offline template: '" in source,
    "honest offline-template limitation": "does not generate arbitrary objects or realistic AI footage" in source,
}
for label, passed in checks.items():
    print(("PASS" if passed else "FAIL") + ": " + label)
assert all(checks.values()), "Local Video Studio prompt regression checks failed"
print("All local-video prompt regression checks passed.")
