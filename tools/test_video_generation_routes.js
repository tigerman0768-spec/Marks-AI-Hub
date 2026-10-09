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
      return { ok: true, status: 200, text: async () => JSON.stringify({ id: 'task/a', status: 'SUCCEEDED', output: ['https://cdn.example.test/clip.mp4'] }) };
    };
    result = await h.call('GET', '/api/video/status/:taskId', { params: { taskId: 'task/a' } });
    assert.equal(result.code, 200);
    assert.equal(calls[0].url, 'https://api.dev.runwayml.com/v1/tasks/task%2Fa');
    assert.equal(result.payload.status, 'SUCCEEDED');
    assert.deepEqual(result.payload.output, ['https://cdn.example.test/clip.mp4']);

    global.fetch = async () => ({ ok: true, status: 200, text: async () => JSON.stringify({ status: 'PENDING' }) });
    result = await h.call('POST', '/api/video/generate', { body: { prompt: 'Malformed provider response' } });
    assert.equal(result.code, 502, 'provider response without task ID is rejected');
    assert.match(result.payload.error, /usable task ID/);

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
