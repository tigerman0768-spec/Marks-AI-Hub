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
  assert.match(appPatch, /status\['failureCode'\] \?\? status\['failure_code'\] \?\? status\['code'\]/, 'failed generation stores provider failure codes');
  assert.match(appPatch, /status\['failureMessage'\] \?\? status\['failure_message'\]/, 'failed generation stores provider failure messages');
  assert.match(appPatch, /uri\.scheme == 'https' && uri\.host\.isNotEmpty/, 'clip downloader accepts only valid HTTPS URLs');
  assert.match(appPatch, /output\['video_url'\].*output\['contentUrl'\].*output\['downloadUrl'\]/s, 'clip URL extraction supports common provider output field names');
  assert.match(appPatch, /Direct video download failed:/, 'direct clip download errors are recorded without escaping the scene handler');
  assert.match(appPatch, /Generate request failed:/, 'submission network and malformed-response errors are isolated to the scene');
  assert.match(appPatch, /generationFailureAt/, 'submission failures record their timestamp');
  assert.match(appPatch, /generationFailureType/, 'submission failures record their exception type');
  assert.match(appPatch, /Invalid video status response:/, 'malformed successful status responses fail clearly per scene');
  assert.match(appPatch, /status is! Map/, 'status polling rejects non-object JSON responses');
  assert.match(appPatch, /No task ID or usable HTTPS video URL returned/, 'direct responses without a valid clip URL fail clearly');
  assert.match(appPatch, /scene\.remove\('downloadFailureAt'\)/, 'successful downloads clear stale failure timestamps');
  assert.match(appPatch, /scene\.remove\('downloadFailureType'\)/, 'successful downloads clear stale failure types');
  assert.match(appPatch, /Uri\.encodeComponent\(activeTask\)/, 'status polling encodes the validated active task ID');
  assert.match(appPatch, /uri\.path\.endsWith\('\/api\/video\/status'\)/, 'status endpoint URLs are not given a duplicate API path');
  assert.ok(appPatch.includes("uri.path.replaceFirst(RegExp(r'/$'), '')"), 'custom backend path prefixes are preserved when polling status');
  assert.match(appPatch, /uri\.scheme != 'https'.*uri\.scheme == 'http' && isLocalDevelopmentHost/s, 'remote backend endpoints require HTTPS');
  assert.match(appPatch, /uri\.host == 'localhost'.*uri\.host == '127\.0\.0\.1'.*uri\.host == '10\.0\.2\.2'/s, 'HTTP exception is limited to local development hosts');
  assert.doesNotMatch(appPatch, /Uri\.encodeComponent\(task\)/, 'status polling does not pass a nullable task ID');
  const originalFetch = global.fetch;
  const originalKey = process.env.RUNWAYML_API_SECRET;
  const h = createHarness();
  const calls = [];
  try {
    delete process.env.RUNWAYML_API_SECRET;
    let health = await h.call('GET', '/api/video/health');
    assert.equal(health.code, 200, 'health route stays available without provider credentials');
    assert.deepEqual(health.payload, {
      ok: true, provider: 'runway', model: 'gen4.5', configured: false, generationReady: false
    }, 'health route clearly reports unconfigured video generation without exposing secrets');

    process.env.RUNWAYML_API_SECRET = 'test-only-key';
    health = await h.call('GET', '/api/video/health');
    assert.equal(health.payload.configured, true);
    assert.equal(health.payload.generationReady, true);
    assert.doesNotMatch(JSON.stringify(health.payload), /test-only-key/, 'health route never exposes the provider secret');

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

    // Invalid reference images should fail before calling the provider.
    calls.length = 0;
    result = await h.call('POST', '/api/video/generate', {
      body: { prompt: 'Reject a local image path', promptImage: '/storage/emulated/0/Pictures/reference.png' }
    });
    assert.equal(result.code, 400, 'local filesystem paths are not valid provider image URLs');
    assert.equal(calls.length, 0, 'invalid image URL is rejected before provider access');

    result = await h.call('POST', '/api/video/generate', {
      body: { prompt: 'Reject insecure image URL', promptImage: 'http://example.test/reference.png' }
    });
    assert.equal(result.code, 400, 'non-HTTPS image URLs are rejected');

    result = await h.call('POST', '/api/video/generate', {
      body: { prompt: 'Reject malformed image URL', promptImage: 'https://' }
    });
    assert.equal(result.code, 400, 'HTTPS URL without a hostname is rejected');
    assert.equal(calls.length, 0, 'malformed image URL is rejected before provider access');

    calls.length = 0;
    global.fetch = async (url, options) => {
      calls.push({ url, options });
      return { ok: true, status: 200, text: async () => JSON.stringify({ id: 'task-trimmed-image' }) };
    };
    result = await h.call('POST', '/api/video/generate', {
      body: { prompt: 'Normalize image URL', promptImage: '  https://example.test/reference.png  ' }
    });
    assert.equal(result.code, 202, 'valid URL with surrounding whitespace is normalized');
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

    // Normalize alternate provider output field names instead of discarding a completed clip URL.
    for (const [field, value] of [
      ['outputs', ['https://cdn.example.test/outputs-variant.mp4']],
      ['videoUrl', 'https://cdn.example.test/video-url-variant.mp4'],
      ['video_url', 'https://cdn.example.test/video-url-snake-variant.mp4'],
      ['url', 'https://cdn.example.test/url-variant.mp4']
    ]) {
      global.fetch = async () => ({
        ok: true, status: 200,
        text: async () => JSON.stringify({ status: 'SUCCEEDED', [field]: value })
      });
      result = await h.call('GET', '/api/video/status/:taskId', {
        params: { taskId: 'alternate-output-' + field }
      });
      assert.equal(result.code, 200);
      assert.deepEqual(result.payload.output, value,
        'status route preserves alternate provider output field: ' + field);
    }

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
    assert.equal(result.payload.failure, 'The request was rejected by provider policy.',
      'provider failure summary prefers the human-readable message');
    assert.equal(result.payload.failureCode, 'CONTENT_POLICY',
      'structured provider failure code is preserved separately');
    assert.equal(result.payload.failureMessage, 'The request was rejected by provider policy.',
      'provider failure message is preserved');
    assert.equal(result.payload.completedAt, '2026-10-10T12:00:00.000Z',
      'provider completion timestamp is preserved');
    assert.equal(result.payload.createdAt, '2026-10-10T11:59:00.000Z',
      'provider creation timestamp is preserved');

    // Some provider responses expose only snake-case failure fields.
    global.fetch = async () => ({
      ok: true, status: 200,
      text: async () => JSON.stringify({
        status: 'FAILED',
        failure_code: 'CONTENT_POLICY',
        failure_message: 'Prompt rejected by provider.'
      })
    });
    result = await h.call('GET', '/api/video/status/:taskId', {
      params: { taskId: 'snake-case-failure' }
    });
    assert.equal(result.payload.failure, 'Prompt rejected by provider.',
      'app-facing failure summary falls back to snake-case message');
    assert.equal(result.payload.failureCode, 'CONTENT_POLICY');
    assert.equal(result.payload.failureMessage, 'Prompt rejected by provider.');


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
