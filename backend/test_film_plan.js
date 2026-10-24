'use strict';

const assert = require('node:assert/strict');
const { buildFilmPlan } = require('./film_plan');

const one = buildFilmPlan({ title: 'Forest Walk', idea: 'A man walks his dog through a misty forest', durationMinutes: 1, sceneCount: 4 });
assert.equal(one.scenes.length, 4);
assert.equal(one.totalDurationSeconds, 60);
assert.equal(one.scenes.reduce((sum, scene) => sum + scene.durationSeconds, 0), 60);
assert.ok(one.scenes.every(scene => scene.prompt.includes('misty forest')));
assert.equal(one.scenes[0].title, 'Opening');
assert.equal(one.scenes[3].title, 'Finale');

const hour = buildFilmPlan({ idea: 'A building rises from an empty site', durationMinutes: 60, sceneCount: 30, genre: 'construction timelapse' });
assert.equal(hour.totalDurationSeconds, 3600);
assert.equal(hour.scenes.length, 30);
assert.equal(hour.scenes.reduce((sum, scene) => sum + scene.durationSeconds, 0), 3600);
assert.throws(() => buildFilmPlan({ idea: '   ' }), /film idea or prompt/i);
assert.throws(() => buildFilmPlan({ idea: 'test', durationMinutes: 61 }), /between 1 and 60/i);
console.log('PASS: film planner validates input and allocates exact 1-minute and 60-minute scene timelines.');
