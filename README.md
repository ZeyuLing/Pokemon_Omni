# Pokémon Omni

多地区、跨表现平台的宝可梦游戏项目。**GBA 是首个交付平台；剧情、人物、战斗与世界进度由可复用游戏核心定义，后续接入 3D 开放世界前端。**当前已有可玩的真新镇 GBA 开场、嵌入游戏的图鉴、网站图鉴及跨平台战斗政策／合法性核心；全地区与完整战斗系统尚未实现。

## 现在开始游戏

运行本地服务后打开 **`http://127.0.0.1:4173/play`**。当前调试版启动即打开游戏内图鉴，无需先领取。图鉴列表按 B 返回标题，再开始或继续冒险；仍可探索真新镇、选择初始伙伴、进行练习战，并使用队伍、背包和保存。原生 ROM 为 `build/pallet/omni-pallet.gba`（24 MiB），已经通过实际 mGBA 按键流程；操作、构建、共享核心和边界见 [真新镇游戏基础版](docs/14-pallet-town-game.md)。

```powershell
./tools/build_pallet.ps1
node tests/pallet-smoke.cjs
node tools/serve_pokedex.cjs
```

用户已确认：首个版本必须生成真实 `.gba`，但整个项目不能绑定 GBA 引擎。以西班牙火箭队 Dragonsden 2.1 的羁绊概念、究极绿宝石系列的对战与难度体验为参考。究极绿宝石 5.6–5.8 的后续创作者分支独立记录，不与原团队版本混同。

游戏内图鉴当前有 15 个资料页面，仍有中文化、培养覆盖与羁绊规则等未完成项；逐项状态见 [游戏内图鉴验收](docs/15-in-game-pokedex-status.md)。

用户提供的究极绿宝石 5.8 神战永久超进化版已本地归档。35 个来源形态及 140 张原始像素图已接入网站与实际 GBA 图鉴，包含 10 个神兽形态记录；数据提取依据、原版进化条件和未完成的战斗规则见 [5.8 形态接入](docs/18-ultra-emerald-source-forms.md)。

剧情进入独立改编世界线的设计阶段：优先以小智等熟悉角色为主角，组织与跨地区政治冲突贯穿旅程。已形成 [剧情方向 v0.1](docs/19-narrative-direction.md)、[人物与真新镇开场](docs/20-cast-and-opening.md) 和 [第一轮来源研究](research/narrative/2026-09-20-source-review.md)。这些是研究与创作提案，尚未实现到当前 ROM；没有声称已通关全部参考改版或看完全部动画。

## 阅读入口

1. [调研结论与证据边界](docs/01-research.md)：引擎选型、硬件限制、版本核实。
2. [素材与工具目录](docs/02-resources.md)：来源、用途、适配成本和署名要求。
3. [工程架构](docs/03-architecture.md)：引擎、世界、数据、存档、中文和容量设计。
4. [公平对战、AI 与难度](docs/04-battle-ai.md)：信息隔离、AI 研究和验收方案。
5. [羁绊进化设计](docs/05-bond.md)：火箭队名单核对状态和后续设计边界。
6. [地区与剧情覆盖](docs/06-world.md)：独立世界线改编、经典素材覆盖与开放世界降维。
7. [里程碑与验收](docs/07-roadmap.md)：先做可验证的双地区垂直切片，再扩大内容。
8. [开发环境与当前状态](docs/08-development.md)：可复现步骤、未完成事项。
9. [来源索引](research/sources.md)、[待核实问题](research/open-questions.md)。
10. [跨平台核心契约](docs/09-portable-core.md)：状态所有权、剧情/人物/战斗复用、GBA 迁移与 3D 接入。

## 已落地的目录

```text
config/                 项目约束、规则、难度、羁绊的 JSON 设计样例
core/                   平台无关 C99 政策与合法性运行时
adapters/               GBA、无画面宿主和未来 3D 平台接入约定
content/regions/        地区注册表；没有伪装成完成地图的空数据
content/                地区、剧情、训练师和物种数据的组织约定
assets/                 素材导入规约及已下载的研究样本
engine/                 GBA 平台候选引擎接入；不是共享游戏核心
research/               来源清单、证据快照、下载哈希和未决问题
docs/                   中文调研与实现规格
tools/                  资源抓取与骨架校验 PowerShell 脚本
tests/                  核心运行测试与后续真实 ROM 验收约定
```

`config/*.json` 是设计数据，当前没有 ROM 运行时代码读取这些文件。`content/regions/index.json` 的优先级是交付顺序，不是裁剪最终地区目标。

## 当前可执行的检查

```powershell
./tools/fetch_research.ps1
./tools/validate_scaffold.ps1
./tools/test_core.ps1
node tools/legality-reference/test.cjs
```

下载器只取固定上游提交的少量文档、配置源码和第九世代御三家美术样本，记录 SHA-256；不会安装工具、下载游戏 ROM 或执行上游代码。校验只验证骨架与样本完整性，不代表游戏已构建或公平 AI 已实现。

GBA 适配候选底座：`rh-hideout/pokeemerald-expansion`，`expansion/1.17.0`，提交 `e8bd1cd7b03fc032ea37e3ecd38b379b5d01a1e7`。依据发布页对应提交链接和该提交的源码核实。它不是现成的跨平台游戏核心；需逐域抽离和一致性验证，正式接入保留 Git 历史并锁定工具链。

## 项目原则

- 共享核心拥有剧情、人物关系、对战和世界进度；平台负责输入、画面、音频、物理与存储设备。禁止核心依赖 GBA 全局变量、地图坐标或未来 3D 引擎对象。
- 全地区、全图鉴是最终内容目标；32 MiB 是 GBA 平台预算，不是整个内容库或 3D 平台上限。尚未证明 GBA 全内容可同时装下。
- 困难以上禁战斗背包与免费提示换人，各机制独立次数；疯子允许公开的永久 Mega 首领特权，AI 信息权限不随难度扩大。
- 官方赛制严格禁用原创羁绊形态；自定义 Omni 赛制允许羁绊，但不宣称是官方 VGC。
- 第一至第九世代内容作为基线，另行清点 Z-A 等已发布内容。2027 年新作只预留，不编造未公布地图、数值或剧情。
- 每项素材记录来源与署名；借鉴其他改版的设计，不把其成品 ROM 当成可直接合并的源码库。

最新规则和已实现边界见 [对战政策与合法性](docs/10-battle-policy-legality.md)。本地验证使用 Zig 0.13.0，运行脚本支持 `-Zig` 指定路径。

## 可运行的图鉴

图鉴核心、中文内容编译和交互预览已实现。特殊形态独立展示与登记；预览调用与 GBA 同源的 C 核心。当前参考目录覆盖 2,419 个物种／形态／状态条目，正常列表显示 1,598 条，隐藏 821 条普通极巨化状态参考。含 1,025 个全国编号物种、97 条 Mega、34 条超极巨化、63 个霜奶仙组合、23 条作者资料支持的羁绊参考和 35 条究极绿宝石改版形态。官方参考部分已与 1,579 条 PokeAPI 形态记录、1,302 条日本官方图鉴记录全部对账。23 条羁绊已核对用户与作者 ROM 的物种记录并提取正背面图，精确版本、招式及项目规则缺口仍保留；详见 [实现与验收](docs/12-pokedex-implementation.md)。

```powershell
./tools/build_pokedex.ps1
node tests/pokedex-wasm.cjs
node tools/serve_pokedex.cjs
```

在浏览器打开 `http://127.0.0.1:4173`。网站支持收藏、最多四形态对比、排序、招式筛选，以及 987 套有来源并通过个体组合检查的培养方案，覆盖 324 个精确形态。图鉴与培养方案仍保留来源、剧情获取和正式规则的缺口提示。

独立 GBA 图鉴已经链接为真实的 24 MiB ROM，包含中文界面、1,598 条可见目录、离线图片、招式与培养页、形态筛选和双槽 SRAM 保存，已在 mGBA 验证。生成后可从网站 `/gba` 直接运行或下载，完整冒险游戏和真机验证仍待完成。

```powershell
python tools/fetch_gba_dependencies.py
./tools/build_gba.ps1 -Python python
node tests/gba-smoke.cjs
```

构建依赖、操作、主游戏事件接口、保存契约及已知边界见 [GBA 图鉴与培养方案](docs/13-gba-dex-training.md)。内容与旧版验证记录见 [图鉴实现](docs/12-pokedex-implementation.md)。

用户实际游玩版的羁绊原图与数值核对见 [ROM 提取记录](research/rocket-rom-extraction.md)。ROM 与 92 个变体 PNG 均只保存在本地；Git 中保留可复现提取脚本、哈希清单与差异记录。
