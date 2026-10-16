# Install and test Mark's AI on Android

## Download the release APK

1. Open the [successful v2604 Android build](https://github.com/tigerman0768-spec/Marks-AI-Hub/actions/runs/38974541714).
2. In the **Artifacts** section, download `Marks-AI-v2604-LOCAL-VIDEO-ROUTE-APK`.
3. Extract the ZIP. It contains:
   - `Mark_s_AI_v2604.apk` — Android installer
   - `Mark_s_AI_v2604.apk.sha256` — SHA-256 checksum
   - `BUILD_INFO.txt` — source commit and build details
4. On the Android phone, open the APK from Downloads or My Files. If Android asks, allow installation from that file source, then retry the install.

Only install builds you trust. The APK is unsigned by a store publisher or signed with the build's configured signing setup; check the workflow's signing-verification result before sharing it.

## First-run test checklist

- Launch Mark's AI and confirm the main screen opens.
- Open Film Creator and save a small test project.
- Open **Create Video Locally**.
- Try one prompt for each supported template: construction site, forest/dog walk, sci-fi space scene, and city/timelapse.
- Generate a short video and wait for the app's MP4 verification message.
- Export the MP4, then open it in the phone's video player.
- Close and reopen the app to check saved project details.

If a test fails, note the screen, exact error message, and action immediately before it happened.

## Current video-generation limitations

The local video studio uses four stylised, hand-drawn templates and produces a playable MP4 offline. It does **not** create arbitrary photorealistic footage from any text prompt. The separate remote AI-video route depends on a correctly configured backend and provider credentials; a successful APK build alone does not prove that a remote provider is configured or available.

## Build provenance

- Workflow: [Mark's AI v2604 LOCAL VIDEO ROUTE APK](https://github.com/tigerman0768-spec/Marks-AI-Hub/actions/runs/38974541714)
- Source commit: `fb3b8bc721672dfc0ead941edbb6f1fab66af507`
- The artifact ZIP includes the APK checksum and build manifest. Compare the APK's SHA-256 to the value in `Mark_s_AI_v2604.apk.sha256` if verifying the downloaded file.
