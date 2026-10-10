from pathlib import Path
import ast
import sys

root = Path(__file__).resolve().parents[1]
names = [
"v2592_patch_film_creator.py", "v2594_add_video_status.py",
"v2595_add_clip_library.py", "v2596_add_film_assembly.py",
"v2597_add_mp4_renderer.py", "v2600_add_local_video_studio.py",
"v2601_fix_film_creator_feedback.py", "v2602_fix_screenplay_dart.py",
"v2603_construction_timelapse.py", "v2604_scene_planner_local_video.py",
"v2605_download_generated_clips.py", "v2606_resume_safe_video_generation.py",
"v2607_save_finished_film_to_gallery.py", "v2608_recover_scene_submission_errors.py",
"v2609_recover_malformed_status_json.py", "v2610_validate_scene_and_final_mp4.py",
"v2611_validate_video_playability.py", "v2612_validate_film_pipeline.py"]
errors = []
for name in names:
    path = root / "tools" / name
    if not path.is_file():
        errors.append("missing: tools/" + name)
        continue
    try:
        ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        print("PASS:", name)
    except SyntaxError as exc:
        errors.append(f"syntax error in {name}:{exc.lineno}: {exc.msg}")
if errors:
    print("Patch preflight failed:", *errors, sep="\n - ", file=sys.stderr)
    raise SystemExit(1)
print("Patch preflight passed:", len(names), "scripts")
