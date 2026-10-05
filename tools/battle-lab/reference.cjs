'use strict';
// Reuse the repository's exact dependency and pnpm lock; no second simulator install.
const {createRequire} = require('node:module');
const path = require('node:path');
const referenceRequire = createRequire(path.resolve(__dirname, '../legality-reference/package.json'));
const version = referenceRequire('pokemon-showdown/package.json').version;
if (version !== '0.11.11') throw new Error(`Expected pokemon-showdown 0.11.11, found ${version}`);
module.exports = {
  ...referenceRequire('pokemon-showdown'),
  extractChannelMessages: referenceRequire('pokemon-showdown/dist/sim/battle').extractChannelMessages,
  version,
};
