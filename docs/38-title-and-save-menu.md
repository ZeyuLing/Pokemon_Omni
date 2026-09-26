# 封面与存档菜单

2026-09-26。此前标题画面把三只图鉴图片、“新的冒险／继续冒险”和调试提示混在一起。本次在真实 GBA adapter 中分成独立封面与存档菜单，浏览器只运行同一份 ROM。

## 现在的启动流程

1. `/play` 或默认构建开机显示 Pokémon Omni 封面及闪烁的 `PRESS START`。A、B、START 均进入存档菜单；切换有淡出／淡入，持续按住按键不会顺势选择新游戏。
2. 无有效存档时只显示“新的游戏”；已有存档时默认选择“继续游戏”，下面是“新的游戏”。上下选择，A／START 确认，B 返回封面。当前没有实现完整设置菜单，因此不摆放无法使用的设置选项。
3. 继续游戏直接恢复已有位置与进度。新的游戏进入既有序章；有存档时先提示覆盖，B 可取消。完成序章或确认跳过后才创建新存档。
4. 调试入口独立保留：`/play?dex`、`/play?opening`、`/play?cast`。封面 SELECT 直接开图鉴，L 回放、R 画册；返回来源画面。未领取图鉴也可查看，不自动领取伙伴、不推进剧情。

`tools/build_pallet.ps1` 默认构建封面启动版。`-StoryStart` 作为兼容参数等同默认，`-DebugDex` 构建开机直达图鉴版，输出到 `build/pallet-debug/omni-pallet.gba`，不替换普通 `/play` 使用的 ROM。两个参数不能同时使用。`-ReuseAssets` 仅用于资源编译产物已经更新后的代码迭代。

## 美术与来源边界

- 封面读取锁定 [FireRed 素材版本](https://github.com/pret/pokefirered/tree/c75f352304d529f6ba92d4f74b9cf8b5c3810788/graphics/title_screen) 的 Pokémon 标志、喷火龙与 `PRESS START`，保留原生像素及 tilemap 位置。Omni 字样与黑色背景为本作适配。不是火箭队封面的复制，也未移植火红的全部片头效果；最终专属封面美术仍可替换，当前喷火龙不确立新的剧情设定。
- `tools/build_title_assets.py` 从源图、tilemap、调色板编译 78,336 字节的素材，未将截图贴入游戏。来源 URL、提交、哈希与署名见 `assets/source/title-screen.json`。原图及二进制留在忽略目录。
- 存档页使用用户归档火箭队 ROM 的真实边框和中文字库。选项正文原点 `(16,9)`，外框 `(8,0,224,32)`；有存档时继续框高 64，下一选项从 y=64 开始。布局参照 [main_menu.c](https://github.com/pret/pokeemerald/blob/5eff78649e7170a877b961ef0b3da13b81a16038/src/main_menu.c)。新增文字也来自同一 ROM 字库。
- 继续框显示小智、实际记录的游玩时间、图鉴登记数与徽章数。当前未开放道馆，所以正常存档徽章为零。菜单高亮使用明暗变化；未选项的暗色经过 RGB555 量化，未声称它与来源硬件混色结果逐像素相同。
- 配乐保留已经核实的经典真新镇曲。没有把它标注为火红标题曲；这一轮未新增合成配乐。

## 存档与可复用核心

游玩时长与徽章位于 `OmniAdventure`，仍是 portable C 的进度字段。GBA adapter 从 64 Hz 硬件时钟累计实际游玩时间，与 1／2／4 倍行走步数无关；封面、存档选择、画册、回放及封面直达图鉴不计时。计时上限为 999:59:59。

OADV 写入 v3、140 字节；读取兼容 v1／v2 的 132 字节。新增字段为第 128 字节起的时长、132 字节的徽章数，136 字节起为校验和。旧版本无历史计时数据，读取时从零开始累计。OPAL 外层写入 v2，图鉴数据起点由 148 变为 156，兼容读取旧 v1。仍采用两个事务存档槽，旧槽／新槽独立校验，浏览器导入器同步支持两种格式。没有清空现有浏览器存档。

封面、菜单、按键、淡入淡出和素材都属于 GBA adapter；没有把平台绘图逻辑塞进剧情或战斗核心。浏览器直达参数仅模拟 ROM 里的真实按键，并逐帧排空音频队列，不修改模拟器 RAM。

## 本轮验证

```powershell
./tools/build_pallet.ps1
node tests/pallet-smoke.cjs
node tests/startup-rom.cjs
node tests/rocket-startup-reference.cjs
python tests/startup-layout.py
node tests/presentation-rom.cjs
python tests/opening-layout.py
python tests/classic-audio.py
node tests/bag-layout.cjs
python tests/test_game_ui.py
node tests/pallet-browser.cjs
node tests/presentation-browser.cjs
```

- 实际 mGBA framebuffer：来源 ROM 与 Omni 的“新的游戏”首行区域 240×32，共 **7,680 像素全部一致**，覆盖边框、字形、位置与调色板。只对这一可比区域作此结论；来源其余选项未照搬。
- ROM 按键测试：封面闪烁、A／B／START、B 返回、持续按键不连选、无存档／有存档／无效存档、取消覆盖不写 SRAM、v2 存档恢复、计时保存、图鉴直达。既有冒险烟雾检查包含 v1 与损坏新槽回退。
- 既有序章、家具碰撞、73 个演出节拍、音乐原速、背包、SRAM 导入导出、浏览器调试链接与窄屏布局回归。

生成证据：`build/pallet/startup-proof.png`、`startup-layout-report.json`、`presentation-test.json`、`emulator-report.json`。验证是在 mGBA 和浏览器中进行，尚无 GBA 真机验收；此次完成启动流程，不代表其余游戏界面或完整关都一周目全部完成。
