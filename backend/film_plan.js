'use strict';

const GENRES = new Set(['cinematic', 'sci-fi', 'construction timelapse', 'nature', 'animation', 'documentary', 'horror', 'comedy']);

function clean(value, max = 500) {
  return String(value == null ? '' : value).replace(/[\u0000-\u001f]/g, ' ').trim().slice(0, max);
}

function buildFilmPlan(input = {}) {
  const title = clean(input.title, 100) || 'Untitled Film';
  const idea = clean(input.idea || input.prompt, 1200);
  if (!idea) {
    const error = new Error('Add a film idea or prompt before creating a plan.');
    error.status = 400;
    throw error;
  }
  const rawMinutes = Number(input.durationMinutes ?? input.lengthMinutes ?? 1);
  if (!Number.isFinite(rawMinutes) || rawMinutes < 1 || rawMinutes > 60) {
    const error = new Error('Film duration must be between 1 and 60 minutes.');
    error.status = 400;
    throw error;
  }
  const durationMinutes = Math.round(rawMinutes);
  const requestedScenes = Number(input.sceneCount || Math.ceil(durationMinutes / 0.5));
  const sceneCount = Math.max(1, Math.min(30, Number.isFinite(requestedScenes) ? Math.round(requestedScenes) : 2));
  const genreInput = clean(input.genre, 50).toLowerCase();
  const genre = GENRES.has(genreInput) ? genreInput : 'cinematic';
  const seconds = durationMinutes * 60;
  const base = Math.floor(seconds / sceneCount);
  let remainder = seconds % sceneCount;
  const scenes = Array.from({ length: sceneCount }, (_, index) => {
    const durationSeconds = base + (remainder-- > 0 ? 1 : 0);
    const number = index + 1;
    const beat = number === 1 ? 'Establish the world, subject, mood and visual hook.'
      : number === sceneCount ? 'Deliver the payoff and a strong closing image.'
      : number === Math.ceil(sceneCount / 2) ? 'Introduce a turning point that raises the stakes.'
      : 'Advance the story with a distinct visual action and clear continuity.';
    return {
      sceneNumber: number,
      title: number === 1 ? 'Opening' : number === sceneCount ? 'Finale' : 'Scene ' + number,
      durationSeconds,
      prompt: [idea, 'Genre: ' + genre + '.', 'Scene ' + number + ' of ' + sceneCount + '.', beat,
        'Create original moving footage, coherent motion, cinematic composition, consistent subjects and lighting. No title cards or embedded captions.'].join(' '),
      camera: number === 1 ? 'Slow establishing push-in' : number === sceneCount ? 'Controlled cinematic pull-back' : 'Smooth tracking shot',
      transition: number === sceneCount ? 'fade-out' : 'match-cut',
      generationStatus: 'not_started'
    };
  });
  return {
    title, idea, genre, durationMinutes, totalDurationSeconds: seconds,
    sceneCount, scenes,
    assembly: { status: 'waiting_for_generated_clips', outputFormat: 'mp4' },
    note: 'This plan does not itself create AI footage. Connect a configured video-generation provider to generate each scene, then assemble the returned clips.'
  };
}

module.exports = { buildFilmPlan };
