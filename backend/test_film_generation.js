'use strict';

const assert = require('node:assert/strict');
const { createFilmGenerator, extractVideoUrl } = require('./film_generation');

assert.equal(extractVideoUrl({ thumbnail: 'https://example.com/image.jpg', output: [{ videoUrl: 'https://example.com/clip.mp4' }] }), 'https://example.com/clip.mp4');
assert.equal(extractVideoUrl('http://insecure.example/clip.mp4'), null);
assert.throws(() => createFilmGenerator({ baseUrl: 'http://localhost:3000' }), /HTTPS/);
assert.throws(() => createFilmGenerator({ baseUrl: '' }), /backend URL/);

const calls = [];
const fetchImpl = async (url, options = {}) => {
  calls.push({ url, options });
  if (url.endsWith('/api/video/generate')) {
    return { ok: true, json: async () => ({ jobId: 'job-1', taskId: 'job-1' }) };
  }
  if (url.endsWith('/api/video/status/job-1')) {
    return { ok: true, json: async () => ({ status: 'SUCCEEDED', output: [{ videoUrl: 'https://cdn.example/clip.mp4' }] }) };
  }
  throw new Error('Unexpected request ' + url);
};
(async () => {
  const events = [];
  const generator = createFilmGenerator({ baseUrl: 'https://backend.example', fetchImpl, pollIntervalMs: 0, onProgress: event => events.push(event) });
  const result = await generator.generateFilm({
    title: 'Forest Walk', durationMinutes: 1,
    scenes: [
      { sceneNumber: 1, prompt: 'A man starts walking through a forest', durationSeconds: 5 },
      { sceneNumber: 2, prompt: 'The dog runs through the leaves', durationSeconds: 5 }
    ]
  });
  assert.equal(result.status, 'clips_ready_for_assembly');
  assert.equal(result.scenes.length, 2);
  assert.equal(result.scenes[1].videoUrl, 'https://cdn.example/clip.mp4');
  assert.equal(calls.filter(call => call.url.endsWith('/api/video/generate')).length, 2);
  assert.ok(events.some(event => event.status === 'CLIPS_READY_FOR_ASSEMBLY'));
  console.log('PASS: film generator submits scenes sequentially, polls status, validates HTTPS and returns clips for assembly.');
})().catch(error => { console.error(error); process.exitCode = 1; });
