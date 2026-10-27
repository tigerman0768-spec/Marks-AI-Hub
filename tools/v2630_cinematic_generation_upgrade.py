#!/usr/bin/env python3
"""Upgrade Mark's AI from template-first animation to a cinematic real-AI scene pipeline."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app" / "lib"
scene_path = APP / "scene_prompt_screen.dart"
local_path = APP / "local_video_studio_screen.dart"

if not scene_path.is_file() or not local_path.is_file():
    raise SystemExit("Required Film Creator and Local Video Studio screens are missing")

scene = scene_path.read_text(encoding="utf-8")

helper_marker = "  String _cinematicPromptForScene("
if helper_marker not in scene:
    insertion = "  String? _findVideoUrl(dynamic output) {"
    if insertion not in scene:
        raise SystemExit("Could not locate scene URL helper; refusing unsafe cinematic prompt patch")
    helper = r'''  String _cinematicPromptForScene(Map<String, dynamic> scene, FilmCreatorProject film, int index) {
    final raw = (scene['prompt'] ?? '').toString().trim();
    if (raw.isEmpty) return raw;
    final lower = raw.toLowerCase();
    final explicitlyAnimated = [
      'animation', 'animated', 'cartoon', 'anime', 'illustration',
      'stop motion', 'claymation', '2d animation', '3d animation',
    ].any((word) => lower.contains(word));
    final visualTreatment = explicitlyAnimated
        ? 'premium cinematic animation with richly detailed environments, sophisticated materials, naturalistic motion, deliberate composition, nuanced lighting and polished feature-film production value'
        : 'photorealistic live-action cinema, believable human and animal anatomy, physically plausible movement, detailed real-world materials, natural skin and surface texture, cinematic depth of field, realistic shadows, high dynamic range and carefully controlled exposure';
    const shotPlans = [
      'Use a wide 24mm establishing shot with a slow, stable dolly-in to establish geography and scale.',
      'Use a 35mm medium-wide tracking shot, smoothly following the main action with motivated camera movement.',
      'Use a 50mm close detail shot with a gentle push-in and selective focus on the most important action.',
      'Use a low-angle 35mm hero shot with a slow crane rise, keeping the subject grounded and correctly proportioned.',
      'Use a controlled aerial-style reveal that moves laterally to show the surrounding environment and spatial layout.',
      'Use a steady gimbal follow shot at human eye level, with natural parallax and no sudden camera jumps.',
      'Use a composed 50mm environmental shot with a subtle lateral slider move and clear foreground, subject and background separation.',
    ];
    final sceneNumber = (scene['number'] ?? index + 1).toString();
    final filmTitle = film.title.trim().isEmpty ? 'the same film' : film.title.trim();
    final shot = shotPlans[index % shotPlans.length];
    return raw +
        '. CINEMATIC PRODUCTION DIRECTION — Scene ' + sceneNumber +
        ' of "' + filmTitle + '". ' + visualTreatment + '. ' + shot +
        ' Maintain strict continuity with adjacent scenes: the same character identity, face, age, clothing, props, architecture, weather, time of day and colour grade wherever the story requires them. Preserve the described subject and action as the clear focal point; use coherent blocking, realistic scale, natural motion blur and physically plausible lighting. Professional feature-film cinematography, clean image detail, stable temporal motion, 24 fps film cadence, 16:9 composition. No unintended morphing, duplicated people or animals, flicker, jump cuts inside the shot, UI, captions, logos or watermarks.';
  }

'''
    scene = scene.replace(insertion, helper + insertion, 1)

# The backend prioritizes scene.prompt over the top-level prompt, so override both.
payload_marker = """          req.add(utf8.encode(jsonEncode({
            'project': p.state, 'scene': scene, 'prompt': scene['prompt'],
            'durationSeconds': scene['durationSeconds'] ?? 8,
            'aspectRatio': p.aspectRatio, 'provider': 'backend',
          })));"""
payload_replacement = """          final cinematicPrompt = _cinematicPromptForScene(scene, p, i);
          final requestScene = Map<String, dynamic>.from(scene);
          requestScene['prompt'] = cinematicPrompt;
          scene['submittedPrompt'] = cinematicPrompt;
          req.add(utf8.encode(jsonEncode({
            'project': p.state, 'scene': requestScene, 'prompt': cinematicPrompt,
            'durationSeconds': scene['durationSeconds'] ?? 8,
            'aspectRatio': p.aspectRatio, 'provider': 'backend',
          })));"""
if payload_marker in scene:
    scene = scene.replace(payload_marker, payload_replacement, 1)
elif "'scene': requestScene, 'prompt': cinematicPrompt" not in scene:
    raise SystemExit("Could not safely locate the AI generation request payload")
if "_cinematicPromptForScene(scene, p, i)" not in scene:
    raise SystemExit("Cinematic prompt helper is not connected to scene submission")
scene_path.write_text(scene, encoding="utf-8")

local = local_path.read_text(encoding="utf-8")
# Stop labelling the procedural drawing engine as if it generated arbitrary AI video.
local = local.replace(
    "label: Text(rendering ? 'RENDERING LOCALLY…' : 'GENERATE VIDEO')",
    "label: Text(rendering ? 'RENDERING ILLUSTRATED PREVIEW…' : 'CREATE ILLUSTRATED PREVIEW (OFFLINE)')",
)
local = local.replace(
    "label: Text(rendering ? 'RENDERING LOCALLY…' : 'CREATE ILLUSTRATED PREVIEW (OFFLINE)')",
    "label: Text(rendering ? 'RENDERING ILLUSTRATED PREVIEW…' : 'CREATE ILLUSTRATED PREVIEW (OFFLINE)')",
)
return_marker = "      FilledButton.icon(onPressed: rendering ? null : () { _render(); },"
if "RETURN TO REAL AI FILM GENERATION" not in local:
    if return_marker not in local:
        raise SystemExit("Could not locate local preview button to add a clear route back to AI generation")
    return_button = """      if (widget.projectId != null) ...[
        OutlinedButton.icon(
          onPressed: rendering ? null : () => Navigator.of(context).pop(),
          icon: const Icon(Icons.auto_awesome),
          label: const Text('RETURN TO REAL AI FILM GENERATION'),
        ),
        const SizedBox(height: 8),
      ],
"""
    local = local.replace(return_marker, return_button + return_marker, 1)
if "CREATE ILLUSTRATED PREVIEW (OFFLINE)" not in local:
    raise SystemExit("Local preview button label was not updated")
if "RETURN TO REAL AI FILM GENERATION" not in local:
    raise SystemExit("AI-generation return action was not added")
local_path.write_text(local, encoding="utf-8")
print("PASS: AI scene requests now receive cinematic, continuity-aware prompts.")
print("PASS: offline shape animation is clearly labelled as an illustrated preview.")
print("PASS: Local Video Studio has a direct return to real AI film generation.")
