'use strict';

const assert = require('node:assert/strict');
const { spawn } = require('node:child_process');
const path = require('node:path');

async function main() {
  const port = 34000 + Math.floor(Math.random() * 1000);
  const child = spawn(process.execPath, [path.join(__dirname, 'server.js')], {
    env: { ...process.env, PORT: String(port), RUNWAYML_API_SECRET: '' },
    stdio: ['ignore', 'pipe', 'pipe']
  });
  let logs = '';
  child.stdout.on('data', chunk => { logs += chunk.toString(); });
  child.stderr.on('data', chunk => { logs += chunk.toString(); });
  const base = 'http://127.0.0.1:' + port;
  try {
    let response;
    for (let i = 0; i < 40; i++) {
      if (child.exitCode !== null) throw new Error('Backend exited during startup: ' + logs);
      try {
        response = await fetch(base + '/api/video/health', { signal: AbortSignal.timeout(1000) });
        break;
      } catch (_) {
        await new Promise(resolve => setTimeout(resolve, 250));
      }
    }
    assert.ok(response, 'backend should start and respond to health checks');
    assert.equal(response.status, 200);
    const health = await response.json();
    assert.equal(health.ok, true);
    assert.equal(health.provider, 'runway');
    assert.equal(health.configured, false);
    assert.equal(health.generationReady, false);
    assert.equal(JSON.stringify(health).includes('RUNWAYML_API_SECRET'), false, 'health response must not expose secret names or values');

    response = await fetch(base + '/');
    assert.equal(response.status, 200);
    assert.equal((await response.json()).ok, true);

    response = await fetch(base + '/api/video/generate', {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ prompt: 'Test only; no provider secret is configured' })
    });
    assert.equal(response.status, 503, 'generation must fail safely without provider credentials');
    const error = await response.json();
    assert.match(error.error, /RUNWAYML_API_SECRET is not configured/);
    console.log('PASS: backend starts, health does not leak credentials, and generation fails safely without a secret.');
  } finally {
    child.kill('SIGTERM');
  }
}

main().catch(error => {
  console.error(error);
  process.exitCode = 1;
});
