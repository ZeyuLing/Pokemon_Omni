# GBA 图鉴、网站增强与培养方案

2026-09-20 实现记录。当前交付包含网站增强、可在模拟器启动的独立 GBA 图鉴 ROM，以及供未来主游戏调用的事件与保存接口。**尚未接入地图、战斗结算、背包菜单与剧情系统，不代表完整冒险游戏已经实现。**

## 可运行内容

网站入口 `http://127.0.0.1:4173/`，真实 ROM 浏览器运行入口 `/gba`。本地产物 `build/gba/omni-dex.gba` 为 14 MiB（14,680,064 字节），ARM7TDMI/Thumb 代码、标准 GBA 头、240×160 Mode 3 画面；没有依赖浏览器才能执行的游戏逻辑。mGBA 实测通过，GBA 真机尚未验证。

网站新增收藏与收藏筛选、收藏 JSON 备份、最多四形态对比、种族值排序、条目链接复制、招式属性／分类／学习世代筛选。培养页可切换来源赛制及方案，展示携带道具作用与替代道具、特性、性格、参考等级、六项 EV/IV、四招、太晶属性（来源提供时）、条件说明，并导出 Showdown 配招文本。

GBA 版载入全部 2,384 条当前目录。包括中文与图片、属性／特性／六项种族值、招式列表及威力／命中／PP／跨代来源代码、推荐道具／性格／特性／四招及 EV/IV、同物种形态选择和独立进度。筛选支持全国编号、分类、世代、属性、进度、研究条目，以及英文名称键盘查询。网站的长篇道具解释、替代道具说明、收藏及对比功能目前没有全部移植至 GBA 页面。

GBA 使用 1,563 个输入图片引用，经缩放与内容去重成为 1,532 张 64×64 BGR555 图片，图像占用 12,550,144 字节。图像离线嵌入，缺图为零。当前是参考图适配，仍含普通极巨化复用图、官方截图缩放等；不是全部重新绘制的发行级 GBA 像素素材。输入内容哈希见 `assets/source/gba-reference-images.json`，生成结果与构建报告在忽略目录 `build/gba/`。

## 培养方案来源和边界

`research/competitive-sources/` 保存 [pkmn/smogon 分发的 Smogon 配招数据](https://pkmn.github.io/smogon/data/sets/gen9ou.json)的 11 份固定快照，manifest 记录来源、日期、SHA-256 和大小。包含第九世代 OU/UU/RU/NU/PU/Ubers/Doubles OU、第八世代 OU、第七世代 OU/UU/Ubers。Smogon 是社区对战资料，不能标成宝可梦官方推荐。

`tools/legality-reference/build-training.cjs` 使用锁定的 `pokemon-showdown@0.11.11`、各来源赛制的 TeamValidator 验证完整个体组合。当前保留 **987 套方案，覆盖 324 个精确形态**，另外 633 项因缺少明确特性、必需数据、目录映射或合法组合等原因拒绝导入，原因保存在 `content/training/plans.json`。没有把基础形态的方案自动复制到 Mega、羁绊或极巨化状态。

存在多选时，导入器有限枚举最多 128 个招式组合，选择第一个通过检查的组合。不会穷举全部道具／性格／努力值变体，也没有对这些方案进行胜率优化。替代道具需与同一套四招重新通过检查。当前保存“来源赛制合法参考”，**没有证明它们是 Omni 的最优解或在本项目中已经可以获得**。

培养 JSON 与生成 C 表来自同一批记录，通过内容指纹和数量校验防止新旧页面／Wasm 混用。`core/src/training.c` 执行运行时数值范围、重复招式、世代／单打双打边界、获取门槛检查。完整学习来源相容性由开发机导入器核验；C 运行时不重复执行整个 Showdown 验证器。门槛掩码包含物种、携带道具、招式三项，未知时返回 UNKNOWN_GATES，有已知未解锁项时返回 LOCKED，不能把未知当成允许。

目前所有方案 `story_availability=unconfigured`、`omni_battle_approved=false`。23 条羁绊保持研究只读，其专属招式、进化触发／解除与项目规则仍待审定；没有为它们编造培养方案。图鉴登记权限也不代表战斗准入权限。

## 构建与运行

需要 Node.js、Zig 0.13.0、Python 3 和 Pillow（本次使用 12.3.0）；脚本支持指定 Zig/Python 路径。首次安装参考数据工具按 `tools/legality-reference/README.md` 使用冻结锁文件。

```powershell
# 用本机实际 Python 路径替换 python；不要求安装系统组件。
python tools/fetch_gba_dependencies.py
./tools/build_pokedex.ps1
./tools/build_gba.ps1 -Python python
node tests/gba-smoke.cjs
node tools/serve_pokedex.cjs
```

首次 GBA 构建会下载 manifest 中的参考图片到 `.cache/gba-art/`。羁绊图依赖本机已核验 ROM 的提取结果：`assets/imported/rocket-user/bond-sprites/`；缺少时先按 `research/rocket-rom-extraction.md` 恢复提取，构建器不会替换成猜测图片。克隆 Git 仓库本身不包含这些本地图片、用户 ROM、工具链、模拟器二进制与生成 ROM。

`fetch_gba_dependencies.py` 固定下载并校验 GNU Unifont 16.0.04 与 `@wasm-gaming/mgba-wasm@0.1.1`；脚本内保留 SHA-256。Unifont 使用本次所需的 1,808 个字形子集，原字体及贡献者信息见 [GNU Unifont](https://unifoundry.com/unifont/index.html)，字形采用 GPLv2+ 加字体嵌入例外／SIL OFL 1.1 双授权。mGBA 包及其 shim 的许可为 MPL-2.0，源码见 [mGBA-wasm](https://github.com/wasm-gaming/mGBA-wasm)。依赖均留在缓存，不修改或提交第三方二进制。

Zig 的汇编缓存未跟踪 `.incbin` 输入，构建器因此把图像与字体的 SHA-256 写入汇编源以更新缓存键。最终 ROM 还必须包含当前图像与字库的完整字节，否则构建失败。这项检查防止字形索引更新后仍链接旧字体。

## GBA 操作与保存

| 场景 | 按键 |
|---|---|
| 列表 | 上下选择，A 详情，L/R 快翻，SELECT 筛选，START 帮助，B 关闭 |
| 详情 | 左右切换六页，L/R 前后条目，B 返回 |
| 招式 | 上下选择，A 详情，SELECT 翻阅更多来源代码，B 回招式列表 |
| 培养 | 上下切换方案；下一页查看 EV/IV |
| 同物种形态 | 上下选择，A 切换到该形态 |
| 筛选 | 上下选项，左右调整；编号用 L/R 跳 100，A 应用，START 清空，SELECT 名称键盘 |
| 名称键盘 | 方向选字，A 输入，`<` 退格，START 查询 |
| 独立版事件联调 | 详情 START，A 模拟见过，R 模拟捕捉，L 模拟解锁 |

事件联调仅存在于定义 `OMNI_GBA_STANDALONE` 的独立构建中。研究条目拒绝登记。浏览器键盘：Z/X 对应 A/B，A/S 对应 L/R，Shift 对应 SELECT，Enter 对应 START；也可用屏幕按钮。

独立版使用 32 KiB SRAM，分成两个 16 KiB 槽。每槽含版本标记、递增序号、长度、负载与头部校验；负载仍是共享核心的 ODEX v1。写入非活动槽，最后提交有效标记，再读回验证。启动选最新有效槽，最新槽损坏时回退前一槽。校验用于损坏检测，不是反作弊签名。

浏览器每五秒及离开页面时保存有效 SRAM；空白 SRAM 不覆盖记录。导入先检查槽和 ODEX 结构，无有效槽时保留当前状态；遇到已存储但损坏的数据，禁止自动覆盖，明确提示导出本次进度。`.sav` 为 32 KiB SRAM，网站 `.odex` 是纯 ODEX 进度，收藏 `.json` 是展示偏好，三者不能直接混用。

## 主游戏接入契约

共享目录、查询、进度、保存及培养政策位于 `core/`；GBA 输入、绘制、字库和 SRAM 位于 `adapters/gba/`。3D 前端可以复用相同 C 接口和稳定 ID，无需复用 GBA 画面代码。

嵌入主游戏时，不定义 `OMNI_GBA_STANDALONE`，不链接独立 `start.s`、`rom.ld`，由宿主拥有主循环、VRAM 配置与恢复、输入路由和完整游戏保存事务：

1. `omni_game_dex_bind(state, save_callback, context)` 绑定宿主拥有的状态和保存函数，缺少回调时拒绝绑定。
2. `omni_game_dex_restore(bytes, length)` 从游戏存档中的 ODEX 区块恢复；损坏导入不改变当前状态。
3. 由已确认的遭遇／捕捉／形态解锁事件调用 `omni_game_dex_event(stable_id, event)`，不读取地图坐标或直接推断奖励。
4. 打开时调用 `omni_game_dex_open()`，每帧传入标准 GBA 按键位到 `omni_game_dex_tick(keys)`；`omni_game_dex_is_open()` 返回零后，宿主恢复原菜单／场景。
5. 保存回调收到临时 ODEX 字节，应同步复制到宿主保存事务并返回是否成功。失败返回 `OMNI_GAME_DEX_SAVE_FAILED`，内存仍保留本次事件，可重试同一个事件。嵌入模式不会回退到直接写裸 SRAM。

## 验收与剩余工作

- 原生 C：完整方案数值边界、未知／锁定门槛、赛制差异、重复招式；宿主状态与回调、错误存档原子性、保存失败重试、研究只读。
- Wasm：图鉴全部 ID／数值等既有一致性测试；新增 987 套方案的 JSON 指纹、条数、赛制与门槛返回值一致性。
- 实际 ARM ROM：mGBA 启动、页面切换、喷火龙培养／EV-IV／形态页、捕捉和解锁保存、重启、最新槽损坏回退。最终图像和字库内容匹配，并人工检查中文画面。
- 浏览器：收藏持久化、对比、排序、招式筛选、导出、错误导入、依赖失败重试、实际 ROM 运行器；1440/820/390/320 像素布局与脚本错误检查。

尚未完成：完整游戏外壳及地图／战斗事件实际接线、捕捉地点／剧情门槛、全部形态培养方案、原创羁绊机制审定、发行美术、真机性能和掉电实验。本独立图鉴已经占用 14 MiB，不代表余下 18 MiB 已足够容纳所有地区、剧情和对战系统；正式集成需图块／调色板压缩与整体 ROM 预算评估。
