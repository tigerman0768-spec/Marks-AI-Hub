from pathlib import Path
import re

source = Path("tools/v2600_add_local_video_studio.py").read_text(encoding="utf-8")

def keywords_before(style_name):
    pattern = r"\[(.*?)\]\.any\(\(word\) => p\.contains\(word\)\)\) return LocalFilmStyle\." + re.escape(style_name)
    match = re.search(pattern, source, re.S)
    assert match, f"Could not find keyword matcher for {style_name}"
    return re.findall(r"'([^']+)'", match.group(1))

forest_words = keywords_before("forestWalk")
scifi_words = keywords_before("sciFi")

def selected(prompt):
    p = prompt.lower()
    if any(word in p for word in forest_words):
        return "forestWalk"
    if any(word in p for word in scifi_words):
        return "sciFi"
    return "timelapse"

cases = {
    "A man walking his dog through a forest": "forestWalk",
    "A puppy playing in the park": "forestWalk",
    "An astronaut exploring a distant planet": "sciFi",
    "A spaceship flying through the galaxy": "sciFi",
    "A city skyline changing from day to night": "timelapse",
}
for prompt, expected in cases.items():
    actual = selected(prompt)
    print(f"{'PASS' if actual == expected else 'FAIL'}: {prompt!r} -> {actual}")
    assert actual == expected, f"{prompt!r}: expected {expected}, got {actual}"

assert "onChanged: (value)" in source and "_styleForPrompt(value)" in source, "Live prompt feedback is missing"
assert "'Best matching offline template: '" in source, "Selected-template label is missing"
assert "does not generate arbitrary objects or realistic AI footage" in source, "Offline limitation disclosure is missing"
print("PASS: live feedback, selected-template label, and limitation disclosure")
print("All local-video prompt regression checks passed.")
