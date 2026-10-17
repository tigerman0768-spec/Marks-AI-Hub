# Mark's AI video backend — release checklist

Use this checklist to enable **real AI video generation**. Building the Android APK does not configure the cloud provider by itself.

## 1. Deploy the backend on Hostinger

- [ ] In Hostinger, create a **Node.js Web App** connected to this GitHub repository.
- [ ] Set the application/root directory to `backend`.
- [ ] Select Node.js **20 or newer**.
- [ ] Use `npm start` as the start command.
- [ ] Add `RUNWAYML_API_SECRET` in Hostinger's private environment variables. Never put the provider secret in Dart code, Git, the APK, or this checklist.
- [ ] Deploy and copy the public HTTPS base URL, for example `https://your-domain.example`.

## 2. Verify the deployment before generating anything

Open `https://YOUR-DOMAIN/api/video/health` in a browser. A ready backend returns JSON containing:

- `"ok": true`
- `"provider": "runway"`
- `"generationReady": true`

If `generationReady` is false, do not try to generate a film yet. Check that the secret is configured on the deployed Hostinger app and redeploy/restart it.

## 3. Connect Mark's AI

In the Film Creator scene planner, choose **GENERATE VIDEO CLIPS** and enter the full HTTPS endpoint:

```
https://YOUR-DOMAIN/api/video/generate
```

The app checks the health endpoint before submitting paid generation requests. It asks for confirmation because each scene can incur provider usage charges. The app then saves the task ID, polls the matching status endpoint, downloads the clip, validates the MP4 and makes it available for film assembly.

## 4. Run the final smoke test

In GitHub, open **Actions** and run **Mark's AI deployed video backend smoke test**.

- Add the deployed HTTPS base URL as the Actions secret `VIDEO_BACKEND_URL`.
- To test health only, leave `VIDEO_GENERATION_SMOKE_PROMPT` unset.
- To test real generation, add `VIDEO_GENERATION_SMOKE_PROMPT` as a repository Actions secret with a short, simple prompt. This can incur provider charges.
- A successful generation run must upload an MP4 and verify it with FFmpeg/ffprobe.

## 5. Final acceptance on the phone

- [ ] Install the APK from the successful **Mark's AI v2604 LOCAL VIDEO ROUTE APK** workflow artifact.
- [ ] Open a film project and plan scenes.
- [ ] Generate a small test (one or two scenes first).
- [ ] Confirm the scenes finish and download.
- [ ] Assemble the finished film.
- [ ] Play the MP4 inside Mark's AI.
- [ ] Save it to the **Marks AI Films** phone gallery album and play it from Gallery/Photos.

**Release status:** source-level tests and Android package builds are automated. Do not mark real AI generation as verified until the deployed smoke test and phone acceptance checks above pass.
