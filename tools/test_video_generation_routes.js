const assert = require('node:assert/strict');
const { registerVideoGenerationRoutes } = require('./video_generation_routes');

function createHarness() {
  const routes = new Map();
  const app = {
    post(path, handler) { routes.set('POST ' + path, handler); },
    get(path, handler) { routes.set('GET ' + path, handler); }
  };
  registerVideoGenerationRoutes(app);
  async function call(method, path, { body = {}, params = {} } = {}) {
    const handler = routes.get(method + ' ' + path);
    assert.ok(handler, 'route registered: ' + method + ' ' + path);
    const result = { code: 200, payload: undefined };
    const res = {
      status(code) { result.code = code; return this; },
      json(payload) { result.payload = payload; return this; }
    };
    await handler({ body, params }, res);
    return result;
  }
  return { call };
}

async function main() {
  // Keep the Android scene-polling repair covered by the backend test workflow:
  // completed tasks without a downloadable URL must fail clearly, not spin for 15 minutes.
  const fs = require('node:fs');
  const path = require('node:path');
  const appPatch = fs.readFileSync(path.join(__dirname, 'v2605_download_generated_clips.py'), 'utf8');
  assert.match(appPatch, /Provider marked generation successful but returned no usable video URL/,
    'scene polling reports success-without-output immediately');
  assert.match(appPatch, /failureMessage/, 'scene state retains provider failure messages');
  assert.match(appPatch, /failureCode/, 'scene state retains provider failure codes');
  assert.match(appPatch, /Status check HTTP/, 'terminal status HTTP errors are surfaced');
  assert.match(appPatch, /errorData\['failure_message'\]/, 'terminal HTTP error bodies preserve provider messages');
  assert.match(appPatch, /scene\['downloadedAt'\]/, 'successful downloads record their timestamp');
  assert.match(appPatch, /scene\.remove\('failureMessage'\)/, 'successful retry clears stale failure details');
  assert.match(appPatch, /scene\['downloadFailureAt'\]/, 'failed downloads record their timestamp');
  assert.match(appPatch, /scene\['downloadFailureType'\]/, 'failed downloads record their error type');
  assert.match(appPatch, /scene\.remove\('downloadFailureAt'\)/, 'successful downloads clear stale failure timestamps');
  assert.match(appPatch, /scene\.remove\('downloadFailureType'\)/, 'successful downloads clear stale failure types');
  const originalFetch = global.fetch;
  const originalKey = process.env.RUNWAYML_API_SECRET;
  const h = createHarness();
  const calls = [];
  try {
    delete process.env.RUNWAYML_API_SECRET;
    let result = await h.call('POST', '/api/video/generate', { body: {} });
    assert.equal(result.code, 400, 'empty prompt is rejected before provider access');

    result = await h.call('POST', '/api/video/generate', { body: { prompt: '  ' } });
    assert.equal(result.code, 400, 'whitespace prompt is rejected');

    process.env.RUNWAYML_API_SECRET = 'test-only-key';
    global.fetch = async (url, options) => {
      calls.push({ url, options });
      return { ok: true, status: 200, text: async () => JSON.stringify({ id: 'task-123' }) };
    };

    result = await h.call('POST', '/api/video/generate', {
      body: { scene: { prompt: 'A cinematic sunrise', durationSeconds: 99, aspectRatio: '9:16' } }
    });
    assert.equal(result.code, 202);
    assert.equal(result.payload.taskId, 'task-123');
    assert.equal(calls[0].url, 'https://api.dev.runwayml.com/v1/text_to_video');
    const textPayload = JSON.parse(calls[0].options.body);
    assert.equal(textPayload.promptText, 'A cinematic sunrise');
    assert.equal(textPayload.duration, 10, 'duration is clamped to provider maximum');
    assert.equal(textPayload.ratio, '720:1280', 'portrait ratio is mapped');

    // Gen-4.5 text-to-video does not support square output; normalize it.
    calls.length = 0;
    global.fetch = async (url, options) => {
      calls.push({ url, options });
      return { ok: true, status: 200, text: async () => JSON.stringify({ id: 'task-square-text' }) };
    };
    result = await h.call('POST', '/api/video/generate', {
      body: { prompt: 'Square composition', aspectRatio: '1:1' }
    });
    assert.equal(result.code, 202);
    assert.equal(JSON.parse(calls[0].options.body).ratio, '1280:720',
      'unsupported square text-to-video ratio falls back to landscape');
    assert.equal(calls[0].options.headers.Authorization, 'Bearer test-only-key');

    calls.length = 0;
    global.fetch = async (url, options) => {
      calls.push({ url, options });
      return { ok: true, status: 200, text: async () => JSON.stringify({ id: 'task-image' }) };
    };
    result = await h.call('POST', '/api/video/generate', {
      body: { prompt: 'Animate this still', promptImage: 'https://example.test/reference.png' }
    });
    assert.equal(result.code, 202);
    assert.equal(calls[0].url, 'https://api.dev.runwayml.com/v1/image_to_video');
    assert.equal(JSON.parse(calls[0].options.body).promptImage, 'https://example.test/reference.png');

    calls.length = 0;
    global.fetch = async (url, options) => {
      calls.push({ url, options });
      return { ok: true, status: 200, text: async () => JSON.stringify({ id: 'task-square-image' }) };
    };
    result = await h.call('POST', '/api/video/generate', {
      body: { prompt: 'Square reference image', promptImage: 'https://example.test/reference.png', aspectRatio: '1:1' }
    });
    assert.equal(result.code, 202);
    assert.equal(JSON.parse(calls[0].options.body).ratio, '960:960',
      'square image-to-video ratio remains supported');

    calls.length = 0;
    global.fetch = async (url, options) => {
      calls.push({ url, options });
      return { ok: true, status: 200, text: async () => JSON.stringify({ id: 'task/a', status: 'SUCCEEDED', output: ['https://cdn.example.test/clip.mp4'] }) };
    };
    result = await h.call('GET', '/api/video/status/:taskId', { params: { taskId: 'task/a' } });
    assert.equal(result.code, 200);
    assert.equal(calls[0].url, 'https://api.dev.runwayml.com/v1/tasks/task%2Fa');
    assert.equal(result.payload.status, 'SUCCEEDED');
    assert.equal(result.payload.jobId, 'task/a', 'status response includes the requested task ID');
    assert.deepEqual(result.payload.output, ['https://cdn.example.test/clip.mp4']);

    // Some provider status responses omit their own ID. The API must
    // retain the requested task ID so the app can keep tracking this job.
    global.fetch = async () => ({
      ok: true, status: 200,
      text: async () => JSON.stringify({
        status: 'SUCCEEDED',
        output: ['https://cdn.example.test/fallback-id.mp4']
      })
    });
    result = await h.call('GET', '/api/video/status/:taskId', {
      params: { taskId: 'requested-task-id' }
    });
    assert.equal(result.code, 200);
    assert.equal(result.payload.jobId, 'requested-task-id',
      'requested task ID is preserved when provider omits its ID');

    // A successful status without output must not imply a downloadable clip.
    global.fetch = async () => ({
      ok: true, status: 200,
      text: async () => JSON.stringify({ status: 'SUCCEEDED' })
    });
    result = await h.call('GET', '/api/video/status/:taskId', {
      params: { taskId: 'success-without-output' }
    });
    assert.equal(result.code, 200,
      'status can be returned when provider omits output');
    assert.equal(result.payload.status, 'SUCCEEDED');
    assert.deepEqual(result.payload.output, [],
      'backend returns no outputs rather than inventing a video URL');

    // Provider failure details should be surfaced without losing the task ID.
    global.fetch = async () => ({
      ok: true, status: 200,
      text: async () => JSON.stringify({
        id: 'failed-task-42',
        status: 'FAILED',
        failure: 'The request was rejected by provider policy.',
        failure_code: 'CONTENT_POLICY',
        failureMessage: 'The request was rejected by provider policy.',
        completedAt: '2026-10-10T12:00:00.000Z',
        createdAt: '2026-10-10T11:59:00.000Z'
      })
    });
    result = await h.call('GET', '/api/video/status/:taskId', {
      params: { taskId: 'failed-task-42' }
    });
    assert.equal(result.code, 200);
    assert.equal(result.payload.jobId, 'failed-task-42');
    assert.equal(result.payload.status, 'FAILED');
    assert.equal(result.payload.failure, 'CONTENT_POLICY',
      'provider failure reason is preserved for troubleshooting');
    assert.equal(result.payload.failureCode, 'CONTENT_POLICY',
      'structured provider failure code is preserved separately');
    assert.equal(result.payload.failureMessage, 'The request was rejected by provider policy.',
      'provider failure message is preserved');
    assert.equal(result.payload.completedAt, '2026-10-10T12:00:00.000Z',
      'provider completion timestamp is preserved');
    assert.equal(result.payload.createdAt, '2026-10-10T11:59:00.000Z',
      'provider creation timestamp is preserved');


    global.fetch = async () => ({ ok: true, status: 200, text: async () => JSON.stringify({ status: 'PENDING' }) });
    result = await h.call('GET', '/api/video/status/:taskId', { params: { taskId: '' } });
    assert.equal(result.code, 400, 'empty task IDs are rejected before provider access');

    global.fetch = async () => ({ ok: true, status: 200, text: async () => JSON.stringify({ id: 'task-no-status' }) });
    result = await h.call('GET', '/api/video/status/:taskId', { params: { taskId: 'task-no-status' } });
    assert.equal(result.code, 502, 'malformed status responses fail instead of polling forever');
    assert.match(result.payload.error, /without a usable status/);

    global.fetch = async () => ({ ok: true, status: 200, text: async () => JSON.stringify({ status: 'PENDING' }) });
    result = await h.call('POST', '/api/video/generate', { body: { prompt: 'Malformed provider response' } });
    assert.equal(result.code, 502, 'provider response without task ID is rejected');
    assert.match(result.payload.error, /usable task ID/);

    global.fetch = async () => ({ ok: true, status: 200, text: async () => { const error = new Error('body timeout'); error.name = 'TimeoutError'; throw error; } });
    result = await h.call('POST', '/api/video/generate', { body: { prompt: 'Provider body timeout' } });
    assert.equal(result.code, 504, 'provider response-body timeouts are reported as gateway timeouts');
    assert.match(result.payload.error, /response timed out/);

    global.fetch = async () => ({ ok: false, status: 429, text: async () => JSON.stringify({ message: 'Rate limited' }) });
    result = await h.call('POST', '/api/video/generate', { body: { prompt: 'Retry later' } });
    assert.equal(result.code, 429);
    assert.equal(result.payload.error, 'Rate limited');

    global.fetch = async () => { const error = new Error('network offline'); error.name = 'TypeError'; throw error; };
    result = await h.call('POST', '/api/video/generate', { body: { prompt: 'Network error path' } });
    assert.equal(result.code, 504);
    assert.match(result.payload.error, /Could not connect/);

    delete process.env.RUNWAYML_API_SECRET;
    result = await h.call('POST', '/api/video/generate', { body: { prompt: 'Missing secret path' } });
    assert.equal(result.code, 503);
    assert.match(result.payload.error, /RUNWAYML_API_SECRET/);

    console.log('PASS: video generation route tests (prompt validation, text/image routing, payload mapping, status polling, provider errors, missing secret)');
  } finally {
    global.fetch = originalFetch;
    if (originalKey === undefined) delete process.env.RUNWAYML_API_SECRET;
    else process.env.RUNWAYML_API_SECRET = originalKey;
  }
}

main().catch(error => {
  console.error(error);
  process.exitCode = 1;
});
