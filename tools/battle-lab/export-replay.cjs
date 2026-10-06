'use strict';
const fs = require('node:fs');
const path = require('node:path');
const {createHash} = require('node:crypto');
const {verifyReplay} = require('./episode.cjs');
const {BattleEnvironment} = require('./environment.cjs');
const {extractChannelMessages} = require('./reference.cjs');
const escape = value => String(value).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));

// Reconstruct only after verifying every observation, accepted action and outcome.
// The viewer receives the spectator channel, never the serialized private state.
function exportReplay(replay, sourceHash) {
  verifyReplay(replay);
  const env = new BattleEnvironment(replay.config);
  let log;
  try {
    for (const step of replay.steps) env.step(step.choices);
    log = extractChannelMessages(env.snapshot().battle.log.join('\n'), [0])[0]
      .filter(line => !line.startsWith('|t:|')).join('\n');
  } finally { env.close(); }
  const labels = replay.agents.map((agent, i) => `p${i + 1}: ${agent.name}`);
  const html = `<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Omni Battle Lab · 已校验对战回放</title>
<style>body{font-family:system-ui,sans-serif;margin:24px}header{max-width:1180px;margin:0 auto 24px}header p{line-height:1.65}code{overflow-wrap:anywhere}</style></head><body>
<header><h1>Omni Battle Lab · 对战回放</h1>
<p>${escape(labels.join(' vs '))} · ${escape(replay.config.format)} · ${replay.result.turn} 回合${replay.result.truncated ? ' · 已截断（非完整对局）' : ''}<br>
点击 Play 播放；Next turn 逐回合前进；Switch sides 切换视角。</p>
<p>来自实际保存的模拟对局，已重新结算并核对全部决策摘要。此为参考模拟器动画，不是 GBA 游戏画面。播放器及精灵素材从 Pokémon Showdown 在线加载；对局不上传到回放服务器。</p>
<details><summary>来源校验</summary><p>原始 replay SHA-256：<code>${escape(sourceHash)}</code><br>结算引擎：${escape(replay.config.reference)}；播放器为在线版本。</p></details></header>
<script type="text/plain" class="battle-log-data">${log.replace(/<\//g, '<\\/')}</script>
<script src="https://play.pokemonshowdown.com/js/replay-embed.js"></script>
</body></html>`;
  return {html, log};
}
if (require.main === module) {
  const [input, output] = process.argv.slice(2);
  if (!input || !output) throw new Error('Usage: node tools/battle-lab/export-replay.cjs INPUT.replay.json OUTPUT.html');
  const source = fs.readFileSync(input);
  const exported = exportReplay(JSON.parse(source), createHash('sha256').update(source).digest('hex'));
  fs.mkdirSync(path.dirname(path.resolve(output)), {recursive:true});
  fs.writeFileSync(output, exported.html);
  console.log(JSON.stringify({output:path.resolve(output), verified:true, publicLogLines:exported.log.split('\n').length}));
}
module.exports = {exportReplay};
