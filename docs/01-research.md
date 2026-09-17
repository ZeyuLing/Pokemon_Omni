# 调研结论（2026-09-17）

## 结论与范围

更新：用户要求未来接入 3D 开放世界。推荐以平台无关核心承载世界、人物、剧情、战斗/AI 和羁绊；RHH 固定版本用于首个 GBA 宿主与 legacy 迁移参考。不能用拼接多个成品改版 ROM 实现这一目标。下文的引擎比较与容量结论限定于 GBA 平台，最新架构见 03 和 09 文档。

用户确认真实 GBA ROM 为硬约束。当前目录原为空，无旧代码或存档需要迁移。本轮不以桌面引擎替代 GBA、不宣称已完成可玩版本。

## 引擎比较

| 路线 | 适合之处 | 本项目判断 |
|---|---|---|
| [RHH pokeemerald-expansion](https://github.com/rh-hideout/pokeemerald-expansion/releases/tag/expansion/1.17.0) | 已有现代机制、扩展数据、测试框架与 Gen IX 美术；可审查 C 源码 | 首选；仍需容量和公平 AI 改造 |
| [pret pokeemerald](https://github.com/pret/pokeemerald) | 绿宝石原版反编译基础 | 适合研究原版；从这里重做所有现代系统成本高 |
| [pret pokefirered](https://github.com/pret/pokefirered) | 关都、七之岛脚本和地图参考 | 作为内容参考；不另起第二个运行时 |
| [CFRU](https://github.com/Skeli789/Complete-Fire-Red-Upgrade) | 火红升级引擎，已有改版生态 | 可对比战斗实现，但与 RHH 不是直接可互换的插件 |
| 桌面/3D/Web 宿主 | 可承载其他表现形式 | 不替代首发真实 GBA；未来 3D 引擎另行选型，复用同一核心 |

### 上游版本与关键新发现

本轮发布页返回 `expansion/1.17.0`，对应提交 `e8bd1cd7b03fc032ea37e3ecd38b379b5d01a1e7`。本地样本均取该提交，避免 `master` 漂移。

该版本提供 `make firered` / `make leafgreen`，并有 FRLG 地图和布局过滤规则。这减少了关都素材接入工作，但**不同构建目标不等于关都与丰缘已在同一 ROM 无缝联通**。上游明确说明跨原版 map group 的 warp/connection 存在限制。跨区 map group、layout、metatile behavior、飞行与复活点必须作为第一阶段技术验证。[上游 FRLG 说明](https://raw.githubusercontent.com/rh-hideout/pokeemerald-expansion/expansion/1.17.0/docs/tutorials/how_to_frlg.md)

现代战斗机制与图鉴支持依据 FEATURES 和源码配置，而非论坛宣传。此轮核对到 `SPECIES_PECHARUNT`、太乐巴戈斯形态常量；并不等于每个物种的所有招式、美术与最新追加形态都已逐项验收。[功能表](https://github.com/rh-hideout/pokeemerald-expansion/blob/expansion/1.17.0/FEATURES.md)

## “最新世代”的冻结策略

官方已公布 Winds / Waves 于 2027 年推出；不能把已公布的新作当成现在可完整复现的内容。[官方公告](https://asia-press.portal-pokemon.com/press-release/announcing-two-all-new-entries-in-the-pokemon-series-pokemon-winds-and-pokemon-waves_20260227/)

Z-A 的官方发行日为 2025-10-16，因此已发布内容清单不能仅写成“朱紫及 DLC”。其新增形态、剧情和独特战斗表达应单列差异清单，逐项核实，不假定 RHH 已全部包含。[官方发行信息](https://legends.pokemon.com/en-us/news/release-date)

冻结清单分别管理：物种、形态、区域形态、Mega 等特殊形态、招式、特性、道具、机制规则、地图和剧情。全国图鉴编号不直接作为引擎内部 form ID；禁止为了凑“全世代”数字添加猜测数据。

## 参考改版证据

### 西班牙火箭队 2.1

确认对象为 Dragonsden 的 Pokémon Edición Team Rocket，不是 colonelsalt 的另一款 Rocket Edition。原始发布帖和项目页可核实作者、四个地区和强力羁绊主题。[作者发布帖](https://whackahack.com/foro/threads/31-12-2024-pokemon-edicion-team-rocket-4-regiones-kanto-archi7-johto-y-hoenn.65493/)、[项目页](https://whackahack.com/juegos/pokemon-edicion-team-rocket/)

Dragonsden 在 2022 年本人回复中强调强力羁绊来自特定训练师与特定宝可梦的独特关系，当时部分首领形态不可获得。该历史说明支持“伙伴身份”这个设计方向，但不能作为 2.1 所有触发条件、玩家可得范围与数值的证据。[作者回复](https://whackahack.com/foro/members/dragonsden.41883/page-3)

本轮未获得可验证的 2.1 完整羁绊规格或源码；不据攻略评论断言当前版本只支持哪一只宝可梦。`teamrocketedition.com` 等同名站点未作为作者身份已验证的一手技术依据。拟议新机制详见 05 文档。

### 究极绿宝石

按用户补充，研究线分为 5.1–5.5 原团队和 5.6–5.8 后续创作者版本。**这是用户提供的版本关系，尚未独立完成每个分支作者与发布包的归属验证。**

搜索到的攻略与视频不足以证明某版 AI 完全不读指令、全部首领合法或等同某个 PvP 赛制。本项目将“公平、接近真人、不同难度”转成可测试的新规格，而不将这些性质当作已经证实的究极绿宝石实现。后续用作者发布说明、固定版本实测及获授权源码补齐。

## 硬件与容量

[gbadoc 内存布局](https://gbadev.net/gbadoc/memory.html) 描述常规 GBA ROM 可寻址窗口至 32 MiB、EWRAM 256 KiB 和 IWRAM 32 KiB。标准兼容性目标采用这些约束，不依赖特殊卡带分银行或模拟器扩容。

上游 INSTALL 展示过 ROM 26,072,244 B、EWRAM 243,354 B、IWRAM 30,492 B 的示例。这仅是文档示例，**不是本轮实测、不是当前配置的保证，也不是所有余量都可安全使用**。[安装文档](https://raw.githubusercontent.com/rh-hideout/pokeemerald-expansion/expansion/1.17.0/INSTALL.md)

因此必须同时测量静态段、堆峰值、栈水位、双打临时缓冲、解压缓冲和音频负载。保存全图鉴收藏还受到存档容量制约，不能只看 ROM。

## 尚不能承诺的内容

- 全部世代所有地区、完整对白和全部音轨能塞入单个 32 MiB ROM。
- RHH 默认高难度 AI 已符合本项目公平要求。
- 原版 DS/3DS/Switch 地图可直接导入 GBA。
- 所有世代特殊机制同时叠加仍然平衡或符合官方 PvP。
- 普通 GBA 真机可无需额外设备接入互联网匹配。

这些分别转化为容量、AI、资产适配、规则和联机验收项；不阻止当前进行设计和素材整理。
