# 战争开场插画

`world-war-v1.png` 是为 Pokémon Omni 新生成的大规模宝可梦战争插画，1536×1024。使用内置 **image_gen.imagegen**；精确提示词见 `world-war-v1.prompt.txt`，哈希与范围见 `world-war-v1.json`。

作为既定第一次世界大战末期背景的无名群像使用：空中、水面与地面同时交战，前线增援压力衔接联盟会议。此图不定义世界地图、新战役日期、交战地区、具体伤亡或胜负。不是官方动画截图；物种外观尚未逐只经过动画设定稿核验。

`tools/build_opening_stages.py` 完整缩放至 288×192，编译为 RGB555，由实际 GBA 在 240×160 窗口里横移镜头。插画中每只宝可梦目前没有独立动作帧。舞台所有碰撞格阻挡，不允许把绘制场景当作可行走地图；人物会议室继续使用来源地图与真实地块碰撞。

剧本在 `content/opening/prologue.json`；正文、演员档案和世界线同步维护于 `docs/37-acted-opening-screenplay.md`、`content/story/characters.json` 和 `content/story/worldline.json`。匿名群像与无线电声音分别登记，未命名个体没有编造生平或最终结局。

音乐采用归档 ROM 中已核实的经典《训练家对战》，尾句转入《希尔弗公司》以衔接议事室。没有新增合成音效或宣称已经完成配音。
