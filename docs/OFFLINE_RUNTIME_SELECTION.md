# Mark's AI — Offline Runtime Selection (Implementation Decision)

## Decision

Use Google's **LiteRT-LM Android/Kotlin API** as the first runtime candidate for local screenplay and scene-planning text generation. Keep it behind a small native Android bridge so Flutter screens do not depend directly on runtime-specific classes.

Use Google's **LiteRT Runtime** (CompiledModel API) as the candidate inference runtime for later image-generation and vision packs. Do not treat LiteRT-LM as an image-generation pipeline: it is the text/multimodal LLM orchestration layer, while image generation requires a separate compatible generative image model and pipeline.

Official technical references:
- LiteRT overview and Android setup: https://developers.google.com/edge/litert/overview
- LiteRT-LM overview and supported model families: https://developers.google.com/edge/litert-lm/overview
- Android LiteRT integration: https://developer.android.com/ai/custom
- Android model loading example for llama.cpp (alternative only): https://github.com/crc-org/llama.cpp/blob/main/docs/android.md

## Why this first

- Android support and Kotlin APIs are documented by the runtime maintainers.
- The text model is a smaller, more testable first milestone than phone-based video diffusion.
- It can support screenplay expansion, dialogue drafting, shot lists, continuity notes and prompt preparation.
- It can be tested independently in airplane mode before it is connected to the film editor.
- The model file remains a separate, explicit model pack; the runtime library alone does not provide model weights.

## Model and licence gate

No model weights are selected or bundled by this decision. A candidate model must pass all of these checks before it is offered in Mark's AI:
1. Confirm the exact model revision, model format and compatibility with the chosen LiteRT-LM release.
2. Read the complete upstream licence and any gated-download conditions.
3. Confirm redistribution in an app/model pack is permitted, including commercial use if Mark later sells the app.
4. Include the required terms, restrictions and attribution in the app and pack.
5. Measure real memory use, generation speed, thermal behaviour and battery drain on the target Android device.
6. Verify the model works with networking disabled.

For example, Gemma models have their own Terms of Use. Those terms contain distribution conditions and use restrictions; do not assume that open weights mean unrestricted redistribution. Review the exact terms for the exact model before packaging it: https://ai.google.dev/gemma/terms/

## First implementation slice

1. Add a native Android model-runtime bridge with explicit states: unavailable, runtime-ready, model-missing, model-loading, ready, generating, failed and cancelled.
2. Add a model-pack installer that imports a user-selected local file, checks available storage, verifies every declared file size and SHA-256, and only then marks the pack installed.
3. Add an offline text-generation screen for screenplay, dialogue and shot-list tasks.
4. Persist model ID/version, prompt, generation settings and output in the local film project.
5. Add airplane-mode tests proving generation does not call any remote provider.
6. Build and run the APK, then test on the actual Samsung device before declaring the model supported.

## Explicitly not claimed

This decision does not mean the runtime has been integrated, a model has been selected, model weights have been downloaded, or offline inference has been proven. Those are separate implementation and test milestones.

It also does not promise full-length photorealistic video diffusion on a phone. Image generation and short-motion generation remain separate, hardware-gated milestones. The existing procedural/illustrated renderer remains a clearly labelled fallback until genuine model-generated assets are produced and verified.
