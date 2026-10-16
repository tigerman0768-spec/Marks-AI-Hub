# Mark's AI Video Backend

This small Node.js service connects Mark's AI's scene generator to Runway video generation. It is designed for a Hostinger Node.js Web App deployment.

## What it provides

- `GET /api/video/health` — reports whether the server and provider configuration are ready; never returns the secret.
- `POST /api/video/generate` — submits a prompt and returns a provider task ID.
- `GET /api/video/status/:taskId` — polls the same task and returns its status/output URL.
- Request limits for billable generation and status polling.
- HTTPS-only provider output URLs, bounded request timeouts and structured errors.

## Deploy on Hostinger

1. Create a Node.js Web App connected to this repository and set its application/root directory to `backend`.
2. Use Node.js 20 or newer.
3. Set the start command to `npm start` (or use the package's start script).
4. Add `RUNWAYML_API_SECRET` as a **private environment variable** in Hostinger. Never commit it into GitHub or put it in the Android app.
5. Optionally set `CORS_ORIGIN` to a comma-separated allow-list. If omitted, CORS allows app origins; the provider key remains server-side.
6. Deploy, then visit `https://YOUR-DOMAIN/api/video/health`. It should return JSON with `ok: true` and `generationReady: true` only after the private provider secret is configured.
7. In Mark's AI, open the scene planner's **GENERATE VIDEO CLIPS** action and enter `https://YOUR-DOMAIN/api/video/generate` when prompted. The app derives the status endpoint from that URL.

## Important

Real AI video generation is a billable provider operation and may take time. The app must receive a task ID, poll until a terminal state, download the resulting MP4, and validate the downloaded clip before treating that scene as complete. A healthy endpoint alone does not prove a clip has been generated. Do not expose the provider secret in source code, screenshots, app settings, or client-side configuration.
