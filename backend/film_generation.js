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
    // Runway Gen-4.5 accepts clips of at most 10 seconds. Split longer story
    // beats into provider-sized shots rather than silently shortening them.
    const shots = [];
    for (const scene of plan.scenes) {
      const duration = Math.max(1, Math.round(Number(scene.durationSeconds) || 5));
      const count = Math.ceil(duration / 10);
      for (let part = 0; part < count; part += 1) {
        const shotDuration = Math.min(10, duration - part * 10);
        shots.push({
          ...scene,
          sceneNumber: scene.sceneNumber,
          shotNumber: part + 1,
          durationSeconds: shotDuration,
          prompt: count === 1 ? scene.prompt : scene.prompt + ' Shot ' + (part + 1) + ' of ' + count + '. Continue the same action and maintain character, wardrobe, location and lighting continuity.'
        });
      }
    }
    if (shots.length > 30) throw new Error('This plan needs ' + shots.length + ' generated clips, but this run is limited to 30 clips. Shorten the film or choose fewer seconds per story beat before starting paid generation.');
    const results = [];
    for (const shot of shots) {
      onProgress({ type: 'film', status: 'GENERATING', completedScenes: results.length, totalScenes: shots.length, sceneNumber: shot.sceneNumber, shotNumber: shot.shotNumber });
      // Sequential generation avoids bursting provider requests and makes progress easy to follow.
      const result = await generateScene(shot, options);
      results.push({ ...result, shotNumber: shot.shotNumber, durationSeconds: shot.durationSeconds });
      onProgress({ type: 'film', status: 'SCENE_READY', completedScenes: results.length, totalScenes: shots.length, sceneNumber: shot.sceneNumber, shotNumber: shot.shotNumber });
    }
    onProgress({ type: 'film', status: 'CLIPS_READY_FOR_ASSEMBLY', completedScenes: results.length, totalScenes: shots.length });
    return {
      title: plan.title,
      durationMinutes: plan.durationMinutes,
      requestedDurationSeconds: plan.totalDurationSeconds,
      generatedClipSeconds: results.reduce((sum, clip) => sum + clip.durationSeconds, 0),
      status: 'clips_ready_for_assembly',
      scenes: results,
      assemblyRequired: true,
      message: 'Generated clips are ready for assembly. Provider clip duration is limited to 10 seconds; download and join all clips with FFmpeg before calling this a finished film.'
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
