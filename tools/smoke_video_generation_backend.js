#!/usr/bin/env node
'use strict';

// Optional deployed-backend smoke test. By default it only checks health;
// setting VIDEO_GENERATION_SMOKE_PROMPT explicitly opts into a billable clip.
const base = String(process.env.VIDEO_BACKEND_URL || '').trim().replace(/\/+$/, '');
const prompt = String(process.env.VIDEO_GENERATION_SMOKE_PROMPT || '').trim();
const timeoutMs = Math.max(5000, Number(process.env.VIDEO_SMOKE_TIMEOUT_MS) || 180000);
if (!base) {
  console.error('VIDEO_BACKEND_URL is required (the deployed backend base URL).');
  process.exit(2);
}
let parsed;
try { parsed = new URL(base); } catch (_) {
  console.error('VIDEO_BACKEND_URL must be a valid URL.');
  process.exit(2);
}
if (parsed.protocol !== 'https:' && !(parsed.protocol === 'http:' && ['localhost', '127.0.0.1', '10.0.2.2'].includes(parsed.hostname))) {
  console.error('VIDEO_BACKEND_URL must use HTTPS outside local development.');
  process.exit(2);
}
async function request(path, options = {}) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 20000);
  try {
    const response = await fetch(base + path, { ...options, signal: controller.signal });
    const raw = await response.text();
    let body;
    try { body = raw ? JSON.parse(raw) : {}; } catch (_) { body = { raw }; }
    if (!response.ok) throw new Error(path + ' returned HTTP ' + response.status + ': ' + String(body.error || body.message || 'request failed'));
    return body;
  } finally { clearTimeout(timer); }
}
async function main() {
  const health = await request('/api/video/health');
  if (health.ok !== true || health.provider !== 'runway') throw new Error('Backend health response is not the expected video API contract.');
  console.log('PASS: deployed video API health endpoint responds.');
  console.log('Provider:', health.provider, '| model:', health.model, '| configured:', Boolean(health.configured));
  if (!prompt) {
    if (!health.generationReady) {
      console.warn('WARNING: backend is reachable, but video generation is not configured. Set RUNWAYML_API_SECRET on the backend before requesting clips.');
      console.log('PASS: health-only diagnostic completed. No generation request was sent and no clip was created.');
      return;
    }
    console.log('PASS: provider credentials are configured. Live generation was not requested; no clip was created.');
    return;
  }
  if (!health.generationReady) throw new Error('Backend is not configured for generation; no clip was requested.');
  const task = await request('/api/video/generate', {
    method: 'POST', headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ prompt, durationSeconds: 2, aspectRatio: '16:9' })
  });
  const taskId = String(task.taskId || task.jobId || '').trim();
  if (!taskId) throw new Error('Generation endpoint did not return a task ID.');
  console.log('PASS: provider accepted generation request. Task ID:', taskId);
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    await new Promise(resolve => setTimeout(resolve, 5000));
    let status;
    try {
      status = await request('/api/video/status/' + encodeURIComponent(taskId));
    } catch (error) {
      // Status polling is safe to retry: it cannot create a second billable
      // generation task. Treat throttling and transient gateway/server errors
      // as temporary, but never retry the initial POST /generate request.
      if (/returned HTTP (408|425|429|500|502|503|504)\b/.test(error.message)) {
        console.warn('Temporary status polling error; retrying same task:', error.message);
        continue;
      }
      throw error;
    }
    const state = String(status.status || '').toUpperCase();
    if (['FAILED', 'CANCELLED', 'CANCELED', 'THROTTLED'].includes(state)) throw new Error('Generation reached terminal state ' + state + ': ' + String(status.failureMessage || status.failure || 'provider did not supply a reason'));
    if (['SUCCEEDED', 'COMPLETED', 'COMPLETE'].includes(state)) {
      // Search all candidate fields rather than using ?? here: providers can return
      // output: [] while placing the actual clip in outputs/contentUrl/assets.
      const output = [status.output, status.outputs, status.videoUrl, status.video_url,
        status.contentUrl, status.content_url, status.downloadUrl, status.download_url,
        status.url, status.result, status.assets, status.data];
      function findVideoUrl(value) {
        if (typeof value === 'string') {
          try {
            const candidate = new URL(value);
            return candidate.protocol === 'https:' && candidate.hostname ? candidate.toString() : null;
          } catch (_) { return null; }
        }
        if (Array.isArray(value)) {
          for (const item of value) { const found = findVideoUrl(item); if (found) return found; }
        }
        if (value && typeof value === 'object') {
          // Provider responses can include poster/thumbnail URLs beside the
          // real clip. Prefer explicit video fields and never treat image-only
          // metadata as a generated movie URL.
          for (const key of ['videoUrl', 'video_url', 'contentUrl', 'content_url', 'downloadUrl', 'download_url', 'output', 'outputs', 'result', 'assets', 'data', 'url', 'uri']) {
            const found = findVideoUrl(value[key]); if (found) return found;
          }
          const nonVideoKeys = new Set(['thumbnail', 'thumbnailUrl', 'thumbnail_url', 'poster', 'posterUrl', 'poster_url', 'preview', 'previewUrl', 'preview_url', 'image', 'imageUrl', 'image_url']);
          for (const [key, child] of Object.entries(value)) {
            if (nonVideoKeys.has(key)) continue;
            const found = findVideoUrl(child); if (found) return found;
          }
        }
        return null;
      }
      const videoUrl = findVideoUrl(output);
      if (!videoUrl) throw new Error('Provider marked the task successful but supplied no usable HTTPS video URL.');
      const controller = new AbortController();
      const timer = setTimeout(() => controller.abort(), 120000);
      let response;
      let bytes;
      try {
        response = await fetch(videoUrl, { signal: controller.signal });
        if (!response.ok) throw new Error('Generated video download returned HTTP ' + response.status + '.');
        bytes = Buffer.from(await response.arrayBuffer());
      } finally { clearTimeout(timer); }
      if (bytes.length < 1024 || bytes.toString('ascii', 4, 8) !== 'ftyp') {
        throw new Error('Generated output download is not a valid MP4 (missing ftyp signature or file is too small).');
      }
      require('node:fs').writeFileSync('video-backend-smoke-test.mp4', bytes);
      require('node:fs').writeFileSync('video-backend-smoke-test.txt',
        'result=PASS\nprovider=Runway\ntask_status=' + state + '\nmp4_bytes=' + bytes.length + '\nmp4_signature=ftyp\n');
      console.log('PASS: live generation completed; downloaded MP4 passed container signature validation (' + bytes.length + ' bytes).');
      return;
    }
  }
  throw new Error('Generation task ' + taskId + ' did not reach a terminal state before timeout.');
}
main().catch(error => { console.error('VIDEO BACKEND SMOKE TEST FAILED:', error.message); process.exitCode = 1; });
