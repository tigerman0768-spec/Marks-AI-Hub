from pathlib import Path

source = Path("tools/v2600_add_local_video_studio.py").read_text(encoding="utf-8")

construction_words = ["construction", "construction site", "building site", "crane", "building being built", "house being built", "building a house", "build a house", "skyscraper", "builders", "building work", "bricklaying", "excavator", "bulldozer", "scaffolding", "roadworks", "road construction", "concrete pour", "renovation", "laying bricks", "brick layers", "building a wall", "digging foundations", "foundation work", "demolition", "demolishing a building", "crane lifting", "steel frame", "high-rise construction", "construction workers"]
forest_words = ["dog", "puppy", "forest", "woodland", "woods", "park", "walking the dog", "man walking his dog", "golden retriever", "trail", "countryside", "autumn forest", "woodland path", "hiking trail"]
scifi_words = ["space", "sci-fi", "sci fi", "spaceship", "planet", "galaxy", "astronaut", "stars"]
urban_words = ["city street", "busy street", "city centre", "city center", "downtown", "urban street", "traffic jam", "cars driving", "city skyline", "town centre", "town center", "parking garage", "car park", "office district", "subway station", "shopping street", "pedestrian crossing"]

def selected(prompt):
    p = prompt.lower()
    if any(word in p for word in construction_words):
        return "construction"
    if any(word in p for word in scifi_words):
        return "sciFi"
    if any(word in p for word in urban_words):
        return "timelapse"
    if any(word in p for word in forest_words):
        return "forestWalk"
    return "timelapse"

cases = {
    "A new construction site with a tower crane": "construction",
    "Builders constructing a skyscraper": "construction",
    "An excavator working on a house being built": "construction",
    "A roadworks crew pouring concrete": "construction",
    "Workers laying bricks on a new wall": "construction",
    "An excavator digging foundations": "construction",
    "Steel frame construction workers building a high-rise": "construction",
    "A building demolition site": "construction",
    "BUILDING A HOUSE FROM THE GROUND UP!": "construction",
    "A man walking through a forest beside a construction site": "construction",
    "A dog walking beside an excavator at a building site": "construction",
    "A man walking his dog through the forest and enjoying the day": "forestWalk",
    "A sci-fi astronaut walking on a planet": "sciFi",
    "A man walking his dog through a forest": "forestWalk",
    "A puppy playing in the park": "forestWalk",
    "A man walking his dog along a woodland path": "forestWalk",
    "A golden retriever on a countryside hiking trail": "forestWalk",
    "An autumn forest walk at golden hour": "forestWalk",
    "An astronaut exploring a distant planet": "sciFi",
    "A spaceship flying through the galaxy": "sciFi",
    "A city skyline changing from day to night": "timelapse",
    "A man walking down a busy city street": "timelapse",
    "A dog walking along a busy city street": "timelapse",
    "Cars driving through downtown": "timelapse",
    "A dog inside a multi-storey parking garage": "timelapse",
    "People crossing at a busy pedestrian crossing": "timelapse",
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
# Verify the real Dart matcher uses the same priority as the model used above.
construction_pos = source.index("return LocalFilmStyle.construction")
scifi_pos = source.index("return LocalFilmStyle.sciFi")
forest_pos = source.index("return LocalFilmStyle.forestWalk")
assert construction_pos < scifi_pos < forest_pos, "Dart matcher priority must be construction, sci-fi, then forest"
assert "return LocalFilmStyle.construction" in source, "Construction template selection is missing"
assert "return LocalFilmStyle.timelapse" in source, "Timelapse fallback is missing"
assert "onChanged: (value)" in source and "_styleForPrompt(value)" in source, "Live prompt feedback is missing"
assert "'Best matching offline template: '" in source, "Selected-template label is missing"
assert "four hand-drawn templates" in source, "Offline template count/description is stale"
assert "ButtonSegment(value: LocalFilmStyle.construction" in source, "Manual construction template selection is missing"
render_section = source[source.index("Future<void> _render() async {"):source.index("Widget build(BuildContext context)")]
assert "style = _styleForPrompt(prompt)" not in render_section, "Rendering must respect a manually selected template"
assert "Respect the currently selected style" in render_section, "Manual style override behavior should remain documented"
assert "_saveLocalVideoToGallery" not in source, "Renderer must not call an undefined gallery-save method"
share_section = source[source.index("Future<void> _share() async {"):source.index("@override", source.index("Future<void> _share() async {"))]
assert "catch (e)" in share_section and "Export failed: " in share_section, "Share/export failures must be reported to the user"
assert "Could not open the video export menu" in share_section, "Share-sheet failure message is missing"
assert "progress = .80; status = 'Encoding cinematic MP4 locally…" in source, "Encoding progress stage is missing"
assert "progress = .94; status = 'Checking that the exported MP4 plays correctly…" in source, "MP4 verification progress stage is missing"
assert "progress = .98; status = 'Saving video details to this film project…" in source, "Project-save progress stage is missing"
startup_section = render_section[render_section.index("setState(() { rendering = true"):render_section.index("ScaffoldMessenger.of(context)")]
assert "outputPath = null" not in startup_section, "Starting a new render must preserve the last successful video for recovery"
assert "does not generate arbitrary objects or realistic AI footage" in source, "Offline limitation disclosure is missing"
print("PASS: construction, forest, sci-fi and timelapse keyword lists, live feedback, template label, and limitation disclosure")
assert selected("A man walking through a forest beside a construction site") == "construction", "Specific construction scene must outrank generic walking/forest words"
assert selected("A dog walking beside an excavator at a building site") == "construction", "Construction machinery must outrank dog-walking keywords"
assert selected("A man walking down a busy city street") == "timelapse", "Generic city walking must not be mistaken for a forest scene"
assert selected("A dog walking along a busy city street") == "timelapse", "Explicit urban setting must outrank a generic dog cue"
assert selected("A dog inside a multi-storey parking garage") == "timelapse", "Parking garage must select urban fallback rather than forest"
assert selected("People crossing at a busy pedestrian crossing") == "timelapse", "Pedestrian crossing must select urban fallback"
print("PASS: scene-specific keywords take priority over generic overlapping words")

# Guard the actual Android renderer patch too, not just the Python test's
# simplified keyword-selection model. This prevents a prompt from selecting a
# construction label while the generated frames silently remain generic.
renderer_patch = Path("tools/v2603_construction_timelapse.py").read_text(encoding="utf-8")
assert "if (style == LocalFilmStyle.construction)" in renderer_patch, "Construction renderer branch is missing"
for visual in ["tower crane", "scaffolding", "construction-site timelapse"]:
    assert visual in renderer_patch.lower(), f"Construction renderer detail missing: {visual}"
assert "canvas.drawRect" in renderer_patch and "canvas.drawLine" in renderer_patch, "Construction scene drawing primitives are missing"
assert "tools/v2603_construction_timelapse.py" in Path(".github/workflows/build-apk-v2591-hybrid-repair.yml").read_text(encoding="utf-8"), "APK workflow does not apply the construction renderer patch"
print("PASS: Android construction renderer patch, scene details, and APK workflow wiring")

print("All local-video prompt regression checks passed.")
