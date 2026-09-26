# 封面与存档菜单

2026-09-26。启动流程已在真实 GBA adapter 中分成独立封面与存档菜单，浏览器只运行同一份 ROM。根据用户对本作主题封面的要求，已将上一版火红喷火龙封面替换为 Omni 专属环境插画。

## 现在的启动流程

1. `/play` 或默认构建开机显示 Pokémon Omni 封面及闪烁的 `PRESS START`。A、B、START 均进入存档菜单；切换有淡出／淡入，持续按住按键不会顺势选择新游戏。
2. 无有效存档时只显示“新的游戏”；已有存档时默认选择“继续游戏”，下面是“新的游戏”。上下选择，A／START 确认，B 返回封面。当前没有实现完整设置菜单，因此不摆放无法使用的设置选项。
3. 继续游戏直接恢复已有位置与进度。新的游戏进入既有序章；有存档时先提示覆盖，B 可取消。完成序章或确认跳过后才创建新存档。
4. 调试入口独立保留：`/play?dex`、`/play?opening`、`/play?cast`。封面 SELECT 直接开图鉴，L 回放、R 画册；返回来源画面。未领取图鉴也可查看，不自动领取伙伴、不推进剧情。

`tools/build_pallet.ps1` 默认构建封面启动版。`-StoryStart` 作为兼容参数等同默认，`-DebugDex` 构建开机直达图鉴版，输出到 `build/pallet-debug/omni-pallet.gba`，不替换普通 `/play` 使用的 ROM。两个参数不能同时使用。`-ReuseAssets` 仅用于资源编译产物已经更新后的代码迭代。

## 美术与来源边界

- 新封面原画为 `assets/title/omni-cover-v3.png`，1536×1024，由内置 imagegen 生成。近景小镇、精灵球与道路对应旅途起点；远处的联盟与商业高塔暗示制度、权力与资本；彩色金羽呼应既有故事起源。黄昏色调表现不安与希望并存的氛围。画面不出现人物或 AI 身份线索。
- 这是象征性标题构图，不是世界地图、城市实景或新增剧情事件。建筑位置不进入地理设定，羽毛不指定后续赋予小智肉身的神兽。无新增叙事角色或人物生平。来源、精确提示词、修改参考图和生成记录见 `assets/title/README.md` 与 `manifest.json`。
- `tools/build_title_assets.py` 校验原画哈希后，完整缩至 240×160（Pillow LANCZOS），量化为 RGB555。保留高分辨率原画，未裁切画面。它是生成插画的硬件适配，不声称原画是逐像素手绘的原生 GBA 资源。
- 独立闪烁的 `PRESS START` 仍取自锁定 [FireRed 素材版本](https://github.com/pret/pokefirered/tree/c75f352304d529f6ba92d4f74b9cf8b5c3810788/graphics/title_screen)，字形不变，放在新画面预留的底部中央 `(72,144,96,8)`。编译器同时生成 `title.h`，使运行时与验证使用同一布局。封面合计仍为 **78,336 字节**，未增加素材占用。来源 URL、提交、哈希与署名见 `assets/source/title-screen.json`；下载的来源素材、编译二进制及 ROM 保持 Git 忽略。
- 存档页使用用户归档火箭队 ROM 的真实边框和中文字库。选项正文原点 `(16,9)`，外框 `(8,0,224,32)`；有存档时继续框高 64，下一选项从 y=64 开始。布局参照 [main_menu.c](https://github.com/pret/pokeemerald/blob/5eff78649e7170a877b961ef0b3da13b81a16038/src/main_menu.c)。新增文字也来自同一 ROM 字库。
- 继续框显示小智、实际记录的游玩时间、图鉴登记数与徽章数。当前未开放道馆，所以正常存档徽章为零。菜单高亮使用明暗变化；未选项的暗色经过 RGB555 量化，未声称它与来源硬件混色结果逐像素相同。
- 配乐保留已经核实的经典真新镇曲。没有把它标注为火红标题曲；这一轮未新增合成配乐。

## 存档与可复用核心

游玩时长与徽章位于 `OmniAdventure`，仍是 portable C 的进度字段。GBA adapter 从 64 Hz 硬件时钟累计实际游玩时间，与 1／2／4 倍行走步数无关；封面、存档选择、画册、回放及封面直达图鉴不计时。计时上限为 999:59:59。

OADV 写入 v3、140 字节；读取兼容 v1／v2 的 132 字节。新增字段为第 128 字节起的时长、132 字节的徽章数，136 字节起为校验和。旧版本无历史计时数据，读取时从零开始累计。OPAL 外层写入 v2，图鉴数据起点由 148 变为 156，兼容读取旧 v1。仍采用两个事务存档槽，旧槽／新槽独立校验，浏览器导入器同步支持两种格式。没有清空现有浏览器存档。

封面、菜单、按键、淡入淡出和素材都属于 GBA adapter；没有把平台绘图逻辑塞进剧情或战斗核心。浏览器直达参数仅模拟 ROM 里的真实按键，并逐帧排空音频队列，不修改模拟器 RAM。

## 启动流程原始验收

以下是启动流程改造时已完成的验证记录，非封面插画替换时全部重跑的声明。

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

## 专属封面替换验证

```powershell
python tools/build_title_assets.py
./tools/build_pallet.ps1 -ReuseAssets
node tests/startup-rom.cjs
node tests/pallet-browser.cjs
python tests/startup-layout.py
./tools/build_pallet.ps1 -ReuseAssets -DebugDex
node tests/startup-rom.cjs --debug
python tests/startup-layout.py
```

- 普通版与图鉴调试版均重新构建为真实 32 MiB GBA ROM，头部校验及标题素材内嵌检查通过；构建同时运行共享冒险、演出与音频核心检查。
- 实际 mGBA 输出连续 130 帧与编译后的 RGB555 封面及闪烁提示两种预期画面逐像素比较，确认画面完整显示、仅开始提示闪烁。另导出 37,632 个非提示区域像素的零差异报告。
- A／B／START、长按保护、无效／新旧存档、取消覆盖、调试图鉴往返通过；既有 Rocket 存档菜单首行 7,680 像素仍与此前采集的参考帧完全一致。
- 浏览器运行同一份新 ROM，启动、存档导入导出保护、音频控制以及 320／390／820 宽度布局检查通过。已目视检查实际 ROM 封面和浏览器截图中的标题、金羽、精灵球与开始提示。
