# Mark's AI — Project Checkpoint
**Date:** 2026-10-29  
**Checkpoint branch:** `checkpoint/2026-10-29`  
**Repository:** https://github.com/tigerman0768-spec/Marks-AI-Hub  
**Base commit:** `fab071704b66634af6e8c6261650a7025a715647`

## Current build status
- GitHub Actions run **40810120559** — “Build Mark's AI APK v2590 FINAL” — completed successfully.
- Java 17/Flutter setup, package retrieval, known Dart repairs, diagnostic analysis, release APK build, APK verification/staging, and artifact upload all completed successfully.
- Run link: https://github.com/tigerman0768-spec/Marks-AI-Hub/actions/runs/40810120559
- APK artifact: `Marks-AI-v2590-APK-FINAL`, 24,906,306 bytes (artifact archive; not a direct public APK release link).
- Source diagnostics artifact: `Marks-AI-v2590-source-diagnostics`.
- There is an existing public release for **v2604** with a direct APK link: https://github.com/tigerman0768-spec/Marks-AI-Hub/releases/download/marks-ai-v2604/Marks-AI-v2604.apk. Do not treat that as a newly verified release or claim its live AI movie generation works.
- The separate install-test workflow runs **40810473009** and **40810464963** concluded failure. The API returned zero jobs for run 40810473009, so the precise failure cause is not yet confirmed. Do not say phone installation passed.

## Verified versus unverified
- Earlier hybrid testing confirmed the app could launch, render/decode a local MP4, and export it through Android MediaStore.
- Local FFmpeg assembly tests and mocked generation checks exist.
- **The v2590 APK build itself succeeded, but this is not proof of installation success or real AI video generation.**
- **Real AI video generation and a complete multi-scene AI film remain unverified.**
- The live Runway smoke test workflow is `.github/workflows/live-video-smoke-test.yml`; it requires the GitHub Actions secret `RUNWAYML_API_SECRET` and makes a real, potentially billable short clip. Never paste API keys into chat.
- The deployed-backend smoke test requires `VIDEO_BACKEND_URL`; a real generation test also needs backend credentials. Do not assume a hosted backend exists: the user has said Hostinger is not set up and wants to avoid spending money unnecessarily.

## Next steps
1. Diagnose the install-test workflow failure and get a trustworthy install/smoke test result.
2. If an APK artifact is offered, explain whether it is an artifact archive or a direct release APK link.
3. Keep the goal focused on reliable real AI scene generation, clip download, joining scenes into a finished film, and saving the finished MP4 to the phone Gallery.
4. Run live provider verification only if the required secret is already configured securely and the user is aware the provider test may cost credits.
5. Continue from this checkpoint; do not restart the project or imply that a mocked/offline preview is a real AI-generated film.
