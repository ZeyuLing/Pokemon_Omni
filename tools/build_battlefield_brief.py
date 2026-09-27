"""Render the per-unit blocking sheet from the actual game data."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
b=json.loads((ROOT/'content/opening/battlefield.json').read_text('utf8'))
a=b['actors']
out=['# 战场逐单位部署表','',
     '由 `tools/build_battlefield_brief.py` 从实际开场数据生成；坐标是本地地图像素，不是世界地理。',
     '', '中央目标：控制岩台通道。该设定只决定这一场的走位，不确定战争起因、战略资源、同盟或结局。', '',
     '关都北侧突击；丰缘西口重装防守；神奥南侧楔形推进；合众东口拦截。尖兵与两翼在前，支援在后，指挥官、训练家与救护人员留在本队后方。', '',
     '中间两条正面交火线：快龙—烈焰猴、暴飞龙—哥德小姐。其余十六条是具体的侧翼接触线，不随机跨场选敌。倒地后仅存活战斗员重新选敌，伤员不再作为目标。', '',
     '身体与射线：宝可梦八向素材，面向目标；移动时面向行进方向。人类面向本队前沿或指定伙伴，救护人员到位后转向伤者。', '']
for team,faction in enumerate(b['factions']):
 out += [f"## {faction['name']}",'','| 实例 | 人物／宝可梦 | 战术岗位 | 初始 → 到位 | 对手／注视对象 | 部署理由 |','|---|---|---|---|---|---|']
 for u in a:
  if u['team']!=team:continue
  d=u['deployment'];out.append(f"| {u['id']} | {u['name']} | {d['station']} | {tuple(u['at'])} → {tuple(u['to'])} | {a[u['target']]['name']} | {d['purpose']} |")
 out.append('')
(ROOT/'docs/41-battlefield-deployment.md').write_text('\n'.join(out),encoding='utf8')
print(f'Rendered {len(a)} unit assignments from runtime deployment data')
