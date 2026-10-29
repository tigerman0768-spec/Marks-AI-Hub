'use strict';
// No-cost checks for the real backend route handlers. Never contacts Runway.
const assert = require('node:assert/strict');
const test = require('node:test');
const { registerVideoGenerationRoutes } = require('./video_generation_routes');

function makeApp() {
  const routes = new Map();
  registerVideoGenerationRoutes({
    get(path, fn) { routes.set('GET ' + path, fn); },
    post(path, fn) { routes.set('POST ' + path, fn); }
  });
  return async (method, path, body = {}, params = {}) => {
    const handler = routes.get(method + ' ' + path);
    assert.ok(handler, 'missing route: ' + method + ' ' + path);
    const res = {
      code: 200, payload: undefined,
      status(code) { this.code = code; return this; },
      json(payload) { this.payload = payload; return this; }
    };
    await handler({ body, params }, res);
    return { status: res.code, body: res.payload };
  };
}

test('health does not expose credentials', async () => {
  const original = process.env.RUNWAYML_API_SECRET;
  process.env.RUNWAYML_API_SECRET = 'local-test-secret-not-real';
  try {
    const call = makeApp();
    const result = await call('GET', '/api/video/health');
    assert.equal(result.status, 200);
    assert.equal(result.body.generationReady, true);
    assert.equal(JSON.stringify(result.body).includes('local-test-secret-not-real'), false);
  } finally {
    if (original === undefined) delete process.env.RUNWAYML_API_SECRET;
    else process.env.RUNWAYML_API_SECRET = original;
  }
});

test('missing credentials fails safely without network access', async () => {
  const original = process.env.RUNWAYML_API_SECRET;
  delete process.env.RUNWAYML_API_SECRET;
  try {
    const call = makeApp();
    const health = await call('GET', '/api/video/health');
    assert.equal(health.status, 200);
    assert.equal(health.body.generationReady, false);
    const generation = await call('POST', '/api/video/generate', { prompt: 'Safe test scene' });
    assert.equal(generation.status, 503);
    assert.match(generation.body.error, /not configured/i);
  } finally {
    if (original !== undefined) process.env.RUNWAYML_API_SECRET = original;
  }
});

test('empty scene prompt is rejected before contacting provider', async () => {
  const call = makeApp();
  const result = await call('POST', '/api/video/generate', { prompt: '   ' });
  assert.equal(result.status, 400);
  assert.match(result.body.error, /prompt/i);
});

test('missing status task ID is rejected before contacting provider', async () => {
  const call = makeApp();
  const result = await call('GET', '/api/video/status/:taskId', {}, { taskId: '' });
  assert.equal(result.status, 400);
  assert.match(result.body.error, /task ID/i);
});
