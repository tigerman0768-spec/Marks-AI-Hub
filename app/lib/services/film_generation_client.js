'use strict';

/**
 * Client-side orchestration helper for Mark's AI film generation.
 * It calls the existing backend endpoints; provider credentials never enter the app.
 * A caller must explicitly start this function because scene submission may incur provider charges.
 */

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

function createFilmGenerator({ baseUrl, fetchImpl = fetch, onProgress = () => {}, pollIntervalMs = 4000, timeoutMs = 12 * 60 * 1000 } = {}) {
  const root = String(baseUrl || '').trim().replace(/\/+$/, '');
  if (!root) throw new Error('Set the deployed HTTPS video backend URL first.');
  if (!/^https:\/\//i.test(root)) throw new Error('The video backend URL must use HTTPS.');

  async function request(path, options = {}) {
    const response = await fetchImpl(root + path, {
      ...options,
      headers: { 'content-type': 'application/json', ...(options.headers || {}) }
    });
    const body = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(body.error || ('Video backend request failed (' + response.status + ')'));
    return body;
  }

  async function generateScene(scene, options = {}) {
    const startedAt = Date.now();
    const submitted = await request('/api/video/generate', {
      method: 'POST',
      body: JSON.stringify({
        scene: {
          prompt: scene.prompt,
          durationSeconds: scene.durationSeconds,
          aspectRatio: options.aspectRatio || '16:9',
          promptImage: scene.promptImage
        }
      })
    });
    const taskId = submitted.taskId || submitted.jobId;
    if (!taskId) throw new Error('The provider did not return a video task ID.');
    let lastStatus = 'PENDING';
    while (Date.now() - startedAt < timeoutMs) {
      await sleep(pollIntervalMs);
      const result = await request('/api/video/status/' + encodeURIComponent(taskId));
      lastStatus = String(result.status || 'UNKNOWN').toUpperCase();
      onProgress({ type: 'scene', sceneNumber: scene.sceneNumber, status: lastStatus, taskId });
      if (lastStatus === 'SUCCEEDED' || lastStatus === 'COMPLETED') {
        const output = result.output;
        const url = extractVideoUrl(output);
        if (!url) throw new Error('Scene ' + scene.sceneNumber + ' completed but returned no usable video URL.');
        return { sceneNumber: scene.sceneNumber, taskId, status: 'SUCCEEDED', videoUrl: url };
      }
      if (['FAILED', 'CANCELLED', 'CANCELED'].includes(lastStatus)) {
        throw new Error('Scene ' + scene.sceneNumber + ' generation ' + lastStatus.toLowerCase() + ': ' + String(result.failureMessage || result.failure || 'provider gave no reason'));
      }
    }
    throw new Error('Timed out waiting for scene ' + scene.sceneNumber + ' (last status ' + lastStatus + '). The provider task may still be running.');
  }

  async function generateFilm(plan, options = {}) {
    if (!plan || !Array.isArray(plan.scenes) || !plan.scenes.length) throw new Error('A film plan with scenes is required.');
    if (plan.scenes.length > 30) throw new Error('A film may contain at most 30 generated scenes per request.');
    const results = [];
    for (const scene of plan.scenes) {
      onProgress({ type: 'film', status: 'GENERATING', completedScenes: results.length, totalScenes: plan.scenes.length, sceneNumber: scene.sceneNumber });
      // Sequential generation avoids bursting provider requests and makes progress easy to follow.
      const result = await generateScene(scene, options);
      results.push(result);
      onProgress({ type: 'film', status: 'SCENE_READY', completedScenes: results.length, totalScenes: plan.scenes.length, sceneNumber: scene.sceneNumber });
    }
    onProgress({ type: 'film', status: 'CLIPS_READY_FOR_ASSEMBLY', completedScenes: results.length, totalScenes: plan.scenes.length });
    return {
      title: plan.title,
      durationMinutes: plan.durationMinutes,
      status: 'clips_ready_for_assembly',
      scenes: results,
      assemblyRequired: true,
      message: 'All generated clips are ready. Download them securely and assemble with FFmpeg before calling this a finished film.'
    };
  }

  return { generateScene, generateFilm };
}

function extractVideoUrl(value, depth = 0) {
  if (depth > 8 || value == null) return null;
  if (typeof value === 'string') {
    try {
      const url = new URL(value);
      return url.protocol === 'https:' ? url.toString() : null;
    } catch (_) { return null; }
  }
  if (Array.isArray(value)) {
    for (const item of value) {
      const found = extractVideoUrl(item, depth + 1);
      if (found) return found;
    }
    return null;
  }
  if (typeof value === 'object') {
    for (const key of ['videoUrl', 'video_url', 'contentUrl', 'content_url', 'downloadUrl', 'download_url', 'output', 'outputs', 'result', 'assets', 'data', 'url', 'uri']) {
      const found = extractVideoUrl(value[key], depth + 1);
      if (found) return found;
    }
  }
  return null;
}

module.exports = { createFilmGenerator, extractVideoUrl };
