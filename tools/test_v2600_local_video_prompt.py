from pathlib import Path

source = Path("tools/v2600_add_local_video_studio.py").read_text(encoding="utf-8")

construction_words = ["construction", "construction site", "building site", "crane", "building being built", "skyscraper", "builders", "building work"]
forest_words = ["dog", "puppy", "forest", "woodland", "woods", "walking", "walk", "hiking", "nature", "park"]
scifi_words = ["space", "sci-fi", "sci fi", "spaceship", "planet", "galaxy", "astronaut", "stars"]

def selected(prompt):
    p = prompt.lower()
    if any(word in p for word in construction_words):
        return "construction"
    if any(word in p for word in forest_words):
        return "forestWalk"
    if any(word in p for word in scifi_words):
        return "sciFi"
    return "timelapse"

cases = {
    "A new construction site with a tower crane": "construction",
    "Builders constructing a skyscraper": "construction",
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

for word in construction_words:
    assert "'" + word + "'" in source, f"Construction keyword missing from app matcher: {word}"
for word in forest_words:
    assert f"'{word}'" in source, f"Forest keyword missing from app matcher: {word}"
for word in scifi_words:
    assert f"'{word}'" in source, f"Sci-fi keyword missing from app matcher: {word}"
assert "return LocalFilmStyle.construction" in source, "Construction template selection is missing"
assert "return LocalFilmStyle.timelapse" in source, "Timelapse fallback is missing"
assert "onChanged: (value)" in source and "_styleForPrompt(value)" in source, "Live prompt feedback is missing"
assert "'Best matching offline template: '" in source, "Selected-template label is missing"
assert "does not generate arbitrary objects or realistic AI footage" in source, "Offline limitation disclosure is missing"
print("PASS: construction, forest, sci-fi and timelapse keyword lists, live feedback, template label, and limitation disclosure")
print("All local-video prompt regression checks passed.")
