# 画册人物像素修正（2026-09-30）

用户指出自制人物尺寸不一致、像素和脸部模糊。审计确认11张旧稿来自两个1536×1024图集：每个512×512插画格被直接最近邻缩为80×80。最近邻不等于原生像素绘制：非整数缩小会丢掉五官、破坏边缘，并把图集中不同占幅的人物变成不同尺寸。此前“构建通过”“画布80×80”不能证明这些立绘合格。

原图集保留为被否决的历史来源，`manifest.json` 的 `rejected_source` 保存原路径、格位及哈希。运行时不再使用这11张缩图。`build_presentation_assets.py` 已移除缩图分支并拒绝 `cell` 图集入口；超过80×80的输入直接报错，不自动缩小。

## 本轮替换

| 人物 | 当前正面来源 | 身份与规格边界 |
|---|---|---|
| 小茂 | Fire Ash 3.7.1 的 RIVAL1 | 专用紫衣动画小茂，训练家635对应Gary；没有用游戏青绿换名 |
| 真司 | Fire Ash 3.7.1 的 RIVAL3 | 训练家1112对应Paul；该游戏另有同名普通NPC，未混用 |
| 小银、阿杏、叶子 | Pokémon Showdown原始像素归档 | 游戏版本素材，不冒称已完成动画参考核验；叶子采用leaf-gen3 |
| 碧蓝、艾岚 | Pokémon Showdown的ZacWeavile像素图 | 碧蓝采用green，保持与Leaf分开；艾岚为专用alain |
| 彼特 | Pokémon Showdown的Brumirage像素图 | bede，不借用其他人物 |
| 阿弘、优藤圣代、小明 | Omni直接编写的原生像素稿 | 80×80、含透明色最多16色；待用户逐张视觉确认 |

其余11位既有来源像素没有重画，包括小智、赤红、青绿、大木等。画册仍为22位，角色记录和翻页顺序保留。SELECT显示当前角色自己的署名。

## Fire Ash来源核查

资源来自[项目维护者发布页](https://www.pokecommunity.com/threads/pok%C3%A9mon-fire-ash-version-3-7-1-out.531791/)的3.7.1无音频ZIP。ZIP内部目录仍写3.7，清单明确区分外部发布版本和内部目录名。只通过HTTP Range读取所需PNG与审计数据，没有执行游戏或压缩包中的程序，未下载完整ZIP，因此不声称有整个归档的SHA256。

读取 `Data/trainers.dat` 的Ruby Marshal数据结构确认角色名／训练家类型绑定，未运行Ruby对象。小茂RIVAL1源PNG为169×169，真司RIVAL3为138×138；它们的可见区域完全由重复的2×2同色块组成。`fireash_cast_art.py` 逐块验证全部RGBA像素相等，才能恢复一个原像素；任何非整数网格或插值都会拒绝。恢复后小茂33×77、真司27×69，只加透明边距进入现有画框。这不是按目标高度任意缩放插画。

来源哈希、ZIP入口、人物绑定和完整边界见 `assets/source/fireash-cast.json`。具体像素作者尚未独立核实，署名Fire Ash制作团队。该资源包的阿弘、圣代、小明分别沿用普通CAMPER／LASS／YOUNGSTER，已排除，不能因名字相同便称作专用形象。

Showdown图像按[资源页规则](https://play.pokemonshowdown.com/sprites/trainers/)保留作者署名和原始像素，不重绘、不缩放。下载图像和源数据均留在忽略目录，Git记录清单和可复现代码。

## 三张专用重绘

用户选择“按最终游戏像素规格重做专用立绘，逐张查看效果”。首次imagegen尝试仍输出放大画布，而且阿弘帽子设计有误，因此没有缩小后接入。该失败输出的哈希登记在 `assets/source/native-cast-redraw.json`。

最终采用 `assets/characters/pixel/{ritchie,giselle,aj}.json` 的原生像素源：80行，每行80个调色板索引。轮廓、眼睛、嘴、衣领、手与鞋直接占据这些像素；编译器只把索引转RGBA和GBA RGB555，不读取生成插画、不自动描摹、不重采样。JSON源文件可直接修改单个像素并重建。

- 阿弘：对照社区保存的初代联盟画面，蓝黄帽、红色圆形标记、深蓝背心、浅色领片和青绿色衣装。旧绿帽生成设计撤下。
- 圣代：对照EP009画面，长棕发、白色短袖、红蝴蝶结、蓝色背心裙和白长袜。姿势为本作像素适配。
- 小明：对照EP008画面，深绿尖发、浅绿高光、橙色上衣和深色立领。裤子及站姿属于本作像素适配，不冒称全身服装已逐帧核实。

参考图的社区出处、哈希和证据边界见 `assets/source/native-cast-redraw.json`；参考图不等于官方游戏资产。三张状态保持 `native_pixel_redraw_in_rom_review_pending`，技术测试不能替用户作美术认可。人物年龄、经历、选角、阵营和剧情日期没有改写；行走、背面、投球和3D套件没有因此完成。

## 重建与验证

```powershell
python tools/import_fireash_cast.py
python tools/build_presentation_assets.py
python tools/build_gba_assets.py
./tools/build_pallet.ps1 -ReuseAssets
python tests/cast-art.py
python tests/initialization-art.py
node tests/initialization-rom.cjs
node tests/pallet-browser.cjs
node tests/story-bible-browser.cjs
python tools/build_story_bible.py
python tools/build_story_bible.py --check
python tests/story_bible.py
```

`cast-art.py` 对22张图逐像素比较原始输入、画框PNG及GBA编码；原生重绘额外检查16色和二值透明，禁止旧插画入口回归。实际ROM测试逐页进入全部画册立绘和署名页面，保存 `build/pallet/cast-review-<actor>.rgba`／`cast-credit-<actor>.rgba`，并继续开场与存档回归。240×160原生帧和整数倍最近邻放大用来核对真实显示；尺寸和像素相等只证明转换路径，不能替代人物比例与脸部视觉审阅。

## 本轮实际结果

- 已构建可运行的32 MiB GBA ROM，SHA256为 `57ef4c02d3f99b890ca1b021de8f2fc701567c0f3e0ac16c98521115395ffd7f`。
- 共用C核心1255轮确定性对战、表现时钟和音频检查通过；22张素材像素检查、初始化美术检查通过。
- 实际ROM回归通过686次按键，逐页核对全部22张立绘的RGB555像素，保存全部署名页；小茂胜负分支、地图行走、道具、存档续玩与坏槽回退继续通过。
- 游戏浏览器检查、设定集浏览器检查、生成文档一致性及53项故事测试通过。设定集浏览器测试原来硬编码23个事件，仓库原有数据已是24个；改为比较实际事件ID全集，没有增删剧情事件。
- 已查看11张替换立绘的实际ROM页面与署名页；三张自绘另外查看3倍最近邻放大图，检查帽子／头发、眼睛、衣领和四肢是否出现缩图杂点、裁断或半透明边缘。全部22张同尺度图与原生小智、赤红、青绿并排查看；来源人物的身高差保留，没有强行等高。
- 本地审阅图：`build/pallet/cast-review-rom-sheet.png`、`cast-credit-rom-sheet.png`，以及 `cast-review-{ritchie,giselle,aj}.png`（240×160）／对应 `-3x.png`（720×480）。这些均来自本轮ROM运行帧，非设计效果图。

待确认范围：三张原生重绘的脸部、体态及画风仍待用户逐张评价。本轮仅修复正面画册立绘，不能当作对应人物四方向行走或全套战斗动画的验收。
