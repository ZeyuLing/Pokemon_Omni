'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const {runEpisode} = require('../tools/battle-lab/episode.cjs');
const {teams} = require('../tools/battle-lab/fixtures.cjs');
const {exportReplay} = require('../tools/battle-lab/export-replay.cjs');

test('viewer exports verified spectator events and rejects corrupted observations', () => {
  const replay = runEpisode({teams:teams.slice(0,2).map(t => t.team), seed:[1,2,3,4]},
    [{name:'power',seed:1},{name:'power',seed:2}]);
  const {log, html} = exportReplay(replay, 'test-source');
  assert.ok(log.includes(`|win|${replay.result.winner}`));
  assert.ok(log.includes('|turn|1'));
  assert.doesNotMatch(log, /\|split\||\|request\||\|t:\|/);
  assert.match(html, /class="battle-log-data"/);
  replay.steps[0].observations[0] = 'corrupt';
  assert.throws(() => exportReplay(replay, 'test-source'), /Observation mismatch/);
});
