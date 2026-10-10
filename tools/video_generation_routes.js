const RUNWAY_BASE = 'https://api.dev.runwayml.com';

function requireKey() {
  const key = process.env.RUNWAYML_API_SECRET;
  if (!key) {
    const error = new Error('RUNWAYML_API_SECRET is not configured on the backend.');
    error.statusCode = 503;
    throw error;
  }
  return key;
}

function runwayHeaders(key) {
  return {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${key}`,
    'X-Runway-Version': '2024-11-06'
  };
}

function clampDuration(value) {
  const n = Number(value);
  if (!Number.isFinite(n)) return 5;
  return Math.max(2, Math.min(10, Math.round(n)));
}

function mapAspectRatio(value, imageToVideo = false) {
  const v = String(value || '16:9');
  // Gen-4.5 text-to-video supports landscape and portrait. Square output
  // is supported for image-to-video, so don't send square to the text route.
  const map = {
    '16:9': '1280:720',
    '9:16': '720:1280',
    '1280:720': '1280:720',
    '720:1280': '720:1280'
  };
  if (imageToVideo) {
    map['1:1'] = '960:960';
    map['960:960'] = '960:960';
  }
  return map[v] || '1280:720';
}

async function runwayRequest(path, options) {
  const key = requireKey();
  let response;
  try {
    response = await fetch(RUNWAY_BASE + path, {
      ...options,
      // Don't leave generation/status requests hanging forever if the provider
      // connection stalls. AbortSignal.timeout is supported by current Node LTS.
      signal: AbortSignal.timeout(60_000),
      headers: {
        ...runwayHeaders(key),
        ...(options && options.headers ? options.headers : {})
      }
    });
  } catch (cause) {
    const error = new Error(
      cause && cause.name === 'TimeoutError'
        ? 'Runway provider request timed out after 60 seconds.'
        : 'Could not connect to the Runway video-generation service.'
    );
    error.statusCode = 504;
    error.cause = cause;
    throw error;
  }
  let text;
  try {
    // Reading a provider response body can stall independently of fetch().
    text = await response.text();
  } catch (cause) {
    const timedOut = cause && (cause.name === 'TimeoutError' || cause.name === 'AbortError');
    const error = new Error(timedOut
      ? 'Runway provider response timed out after 60 seconds.'
      : 'Could not read the Runway provider response.');
    error.statusCode = timedOut ? 504 : 502;
    error.cause = cause;
    throw error;
  }
  let body;
  try {
    body = text ? JSON.parse(text) : {};
  } catch (_) {
    body = { raw: text };
  }
  if (!response.ok) {
    const error = new Error(body.error || body.message || `Runway request failed (${response.status})`);
    error.statusCode = response.status >= 500 ? 502 : response.status;
    error.details = body;
    throw error;
  }
  return body;
}

function registerVideoGenerationRoutes(app) {
  app.post('/api/video/generate', async (req, res) => {
    try {
      const body = req.body || {};
      const scene = body.scene || {};
      const prompt = String(scene.prompt || body.prompt || '').trim();
      if (!prompt) {
        return res.status(400).json({ error: 'A scene prompt is required.' });
      }

      const promptImage = scene.promptImage || body.promptImage;
      const hasPromptImage = Boolean(promptImage);
      const payload = {
        model: 'gen4.5',
        promptText: prompt,
        ratio: mapAspectRatio(scene.aspectRatio || body.aspectRatio, hasPromptImage),
        duration: clampDuration(scene.durationSeconds || body.durationSeconds)
      };

      if (hasPromptImage) {
        payload.promptImage = promptImage;
      }

      // Runway has separate text-to-video and image-to-video endpoints.
      // Most scenes from Mark's AI are prompt-only, so send them to the
      // text-to-video endpoint; use image-to-video only when a reference image
      // was actually supplied.
      const task = await runwayRequest(hasPromptImage ? '/v1/image_to_video' : '/v1/text_to_video', {
        method: 'POST',
        body: JSON.stringify(payload)
      });

      if (!task || typeof task.id !== 'string' || !task.id.trim()) {
        const error = new Error('Runway accepted no usable task ID; no generation job was saved.');
        error.statusCode = 502;
        throw error;
      }

      return res.status(202).json({
        provider: 'runway',
        status: 'PENDING',
        jobId: task.id,
        taskId: task.id
      });
    } catch (error) {
      console.error('[video/generate]', error);
      return res.status(error.statusCode || 500).json({
        error: error.message || 'Video generation request failed.',
        details: error.details || undefined
      });
    }
  });

  app.get('/api/video/status/:taskId', async (req, res) => {
    try {
      const taskId = String(req.params.taskId || '').trim();
      if (!taskId) {
        return res.status(400).json({ error: 'A task ID is required.' });
      }
      const task = await runwayRequest('/v1/tasks/' + encodeURIComponent(taskId), {
        method: 'GET'
      });
      if (!task || typeof task.status !== 'string' || !task.status.trim()) {
        const error = new Error('Runway returned a task status response without a usable status.');
        error.statusCode = 502;
        throw error;
      }
      return res.json({
        provider: 'runway',
        jobId: typeof task.id === 'string' && task.id.trim() ? task.id : taskId,
        status: task.status,
        output: task.output || [],
        failure: task.failure || task.failureCode || null,
        failureCode: task.failureCode || null
      });
    } catch (error) {
      console.error('[video/status]', error);
      return res.status(error.statusCode || 500).json({
        error: error.message || 'Video status request failed.',
        details: error.details || undefined
      });
    }
  });
}

module.exports = { registerVideoGenerationRoutes };
