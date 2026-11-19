# Mark's AI — Offline AI Model Pack Architecture

## Product decision

Mark's AI is offline-first. Core project editing, screenplay planning, character records, scene planning, timeline editing, audio assembly, rendering and export must work without a paid provider or a remote generation API. Model inference must run locally on a supported device or on a user-owned local computer; no cloud inference is required.

## Important distinction

An inference engine is software; a trained model is a separate set of learned weights and tokenizer/configuration assets. Shipping the engine without the weights does not provide AI generation. Conversely, bundling large weights does not guarantee they fit or run on every Android device. The app must detect hardware, memory, storage, model format and licence compatibility before enabling a model.

## Runtime layout

- Flutter application: project UI, screenplay, character bible, scene cards, timeline, render queue and model-pack manager.
- Native inference bridge: Android Kotlin/JNI boundary for a compatible on-device runtime; keep the bridge behind a capability interface so unsupported devices fall back cleanly.
- Model pack store: versioned, checksummed model manifests and files in app-private storage. Support import/install, pause/resume, integrity verification, safe removal and storage estimates.
- Local orchestration: scene queue, prompt conditioning, reference-image handling, seed management, cancellation, progress and resumable jobs. No network request is made by the offline generation path.
- Media pipeline: generated stills/short motion assets, procedural camera moves, transitions, audio mix, subtitles and MP4 encoding using the existing local renderer.
- Project persistence: SQLite/local files; store model ID/version, seed, prompt, scene metadata and asset paths so projects can be reopened.

## Model roles (separate packs)

1. Text/story model: screenplay expansion, shot lists, dialogue and scene descriptions. Use a small quantised instruction model only where device memory permits; provide a deterministic rules-based screenplay fallback.
2. Image model: scene keyframes, locations, props and character reference sheets. This is the first generative model to integrate because still-image inference is substantially more practical on a phone than full video diffusion.
3. Motion model: animate keyframes or generate short clips. Treat this as an optional, hardware-gated pack; do not promise real-time or feature-length video generation on a handset.
4. Speech model: offline text-to-speech and optional speech recognition. Voice packs are separate, with voice licensing recorded in the manifest.
5. Audio pack: bundled, licence-cleared music and sound effects, with local procedural ambience generation.

## Android device tiers

- Tier A — Android device with sufficient RAM, storage and supported accelerator: run compact quantised text/image models locally; expose conservative resolution and frame-count limits.
- Tier B — device supports CPU inference only or has limited memory: run story/shot planning and editing locally; use procedural motion and local image assets; disable unsupported generative packs with a clear explanation.
- Tier C — user-owned local computer on the same offline workflow: allow the desktop/local companion runtime to process larger models, then transfer outputs to the Android project. This is optional and must not be required for core editing/export.

The app must never assume that a flagship phone can run a multi-billion-parameter video diffusion model. Capability detection, memory budgeting and measured inference tests decide availability.

## Model manifest contract

Each pack manifest must declare:
- stable pack ID, semantic version, display name and model role;
- model format/runtime and supported Android ABIs/API levels;
- minimum RAM, recommended RAM, minimum free storage and accelerator requirements;
- input/output dimensions, context/frame limits and expected memory budget;
- SHA-256 for every asset and total installed size;
- upstream model identity, exact licence identifier and required attribution;
- offline-only flag, safety notes and supported quantisation;
- compatibility status and a test prompt for install verification.

Do not bundle or redistribute model weights until the exact upstream licence permits redistribution, commercial use (if applicable), modification/quantisation and the intended packaging. Record the licence and attribution in-app. Never silently download weights in the background.

## Privacy and network guarantees

- Offline mode makes no generation, analytics or telemetry requests.
- Model installation is an explicit user action; the UI shows pack size and storage requirements before installation.
- No prompt, image, character reference or generated media leaves the device in offline mode.
- Optional update checks must be separate from inference and disabled when the user selects strict offline mode.

## Required implementation gates

1. Add model-pack manifest parsing, storage accounting, checksum verification and install/remove UI.
2. Add hardware capability detection and a model compatibility report; test on real Android hardware.
3. Add the native inference bridge with a tiny test model before integrating a large model.
4. Integrate one compact text model and prove screenplay/shot planning works in airplane mode.
5. Integrate one image model and prove a prompt produces a genuine image file in airplane mode; verify dimensions and decode.
6. Add character-reference conditioning and save/reopen continuity metadata.
7. Add optional short-motion generation only after memory, thermal and battery tests pass.
8. Feed generated assets into the existing timeline/FFmpeg pipeline; verify a playable MP4, exact duration, audio sync and Gallery export.
9. Run an airplane-mode end-to-end test. Fail the release if any generation route attempts to call a remote provider.

## Release acceptance tests

- Enable airplane mode before app launch; create and save a project.
- Install a model pack from local storage and verify SHA-256 before activation.
- Generate a screenplay, scene plan and at least one real model-generated image without network access.
- Close and reopen the app; confirm projects, model selection and generated assets persist.
- Assemble a short film, probe actual duration and decode the MP4, then export it to the phone.
- Test low-memory cancellation, thermal pause, interrupted jobs, insufficient storage and corrupted model files.
- Confirm the offline route contains no HTTP client invocation and no provider secret requirement.

## Current status

This document is the approved architecture decision. It does not claim that model weights, a native inference runtime or a complete offline generative-video engine have already been added. The existing illustrated offline renderer remains a fallback until the model-backed gates above pass.
