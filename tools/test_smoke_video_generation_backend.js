#!/usr/bin/env node
'use strict';

// Exercise the deployed smoke-test client against a local fake backend. This
// validates the diagnostic/generate/poll/download path without spending credits.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { spawn } = require('node:child_process');
const http = require('node:http');

async function main() {
  const mp4 = Buffer.alloc(2048);
  mp4.write('ftyp', 4, 'ascii');
  const server = http.createServer((req, res) => {
    res.setHeader('content-type', 'application/json');
    if (req.url === '/api/video/health') {
      res.end(JSON.stringify({ ok: true, provider: 'runway', model: 'gen4.5', configured: true, generationReady: true }));
    } else if (req.url === '/api/video/generate' && req.method === 'POST') {
      res.statusCode = 202;
      res.end(JSON.stringify({ taskId: 'test-task-1', jobId: 'test-task-1' }));
    } else if (req.url === '/api/video/status/test-task-1') {
      res.end(JSON.stringify({ status: 'SUCCEEDED', output: ['https://localhost.invalid/fake.mp4'] }));
    } else if (req.url === '/fake.mp4') {
      res.setHeader('content-type', 'video/mp4');
      res.end(mp4);
    } else {
      res.statusCode = 404;
      res.end(JSON.stringify({ error: 'not found' }));
    }
  });

  // The client correctly insists on HTTPS for remote hosts. The fake local
  // server returns an HTTPS-shaped URL, so serve the clip by intercepting fetch
  // only in this child process via NODE_OPTIONS preload.
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'marks-ai-video-smoke-'));
  const preload = path.join(dir, 'fake-fetch.cjs');
  fs.writeFileSync(preload, `
const originalFetch = global.fetch;
global.fetch = async (input, init) => {
  const url = String(input);
  if (url === 'https://localhost.invalid/fake.mp4') {
    return originalFetch(process.env.FAKE_CLIP_URL, init);
  }
  return originalFetch(input, init);
};
`);

  await new Promise((resolve, reject) => {
    server.once('error', reject);
    server.listen(0, '127.0.0.1', resolve);
  });
  const port = server.address().port;
  const run = await new Promise((resolve, reject) => {
    const child = spawn(process.execPath, [path.join(__dirname, 'smoke_video_generation_backend.js')], {
      cwd: dir,
      encoding: 'utf8',
      env: {
        ...process.env,
        VIDEO_BACKEND_URL: 'http://127.0.0.1:' + port,
        VIDEO_GENERATION_SMOKE_PROMPT: 'A simple test clip',
        VIDEO_SMOKE_TIMEOUT_MS: '5000',
        FAKE_CLIP_URL: 'http://127.0.0.1:' + port + '/fake.mp4',
        NODE_OPTIONS: [process.env.NODE_OPTIONS, '--require=' + preload].filter(Boolean).join(' ')
      }
    });
    let stdout = '';
    let stderr = '';
    child.stdout.setEncoding('utf8');
    child.stderr.setEncoding('utf8');
    child.stdout.on('data', chunk => { stdout += chunk; });
    child.stderr.on('data', chunk => { stderr += chunk; });
    const timer = setTimeout(() => {
      child.kill('SIGKILL');
      reject(new Error('Local smoke-test child timed out. stdout: ' + stdout + ' stderr: ' + stderr));
    }, 30000);
    child.once('error', error => { clearTimeout(timer); reject(error); });
    child.once('close', (code, signal) => {
      clearTimeout(timer);
      resolve({ status: code, signal, stdout, stderr });
    });
  });
  try {
    assert.equal(run.status, 0, 'smoke test succeeds: ' + run.stderr + run.stdout);
    assert.match(run.stdout, /live generation completed/);
    assert.equal(fs.statSync(path.join(dir, 'video-backend-smoke-test.mp4')).size, 2048);
    assert.match(fs.readFileSync(path.join(dir, 'video-backend-smoke-test.txt'), 'utf8'), /result=PASS/);
    console.log('PASS: deployed video smoke-test client health/generate/poll/download flow');
    // Health-only mode must never submit a billable generation request.
    const healthOnly = await new Promise((resolve, reject) => {
      const child = spawn(process.execPath, [path.join(__dirname, 'smoke_video_generation_backend.js')], {
        cwd: dir,
        env: {
          ...process.env,
          VIDEO_BACKEND_URL: 'http://127.0.0.1:' + port,
          VIDEO_GENERATION_SMOKE_PROMPT: '',
          VIDEO_SMOKE_TIMEOUT_MS: '5000',
          NODE_OPTIONS: [process.env.NODE_OPTIONS, '--require=' + preload].filter(Boolean).join(' ')
        }
      });
      let stdout = '';
      let stderr = '';
      child.stdout.setEncoding('utf8');
      child.stderr.setEncoding('utf8');
      child.stdout.on('data', chunk => { stdout += chunk; });
      child.stderr.on('data', chunk => { stderr += chunk; });
      child.once('error', reject);
      child.once('close', (code, signal) => resolve({ code, signal, stdout, stderr }));
    });
    assert.equal(healthOnly.code, 0, 'health-only diagnostic succeeds without a generation prompt: ' + healthOnly.stderr);
    assert.match(healthOnly.stdout, /Live generation was not requested; no clip was created/);
    assert.equal(fs.existsSync(path.join(dir, 'video-backend-smoke-test.mp4')), true,
      'health-only run must not delete or overwrite the previous smoke artifact');
    console.log('PASS: health-only smoke mode does not request a billable clip');

  } finally {
    server.close();
    fs.rmSync(dir, { recursive: true, force: true });
  }
}

main().catch(error => {
  console.error(error);
  process.exitCode = 1;
});
