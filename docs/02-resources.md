# 素材、工具与获取策略

这里的“可用”分成候选来源、已下载研究样本、完成适配并入库三种状态。当前只有研究样本实际落盘，没有声称整包地图或字体已转换进 ROM。

## 素材来源

| 来源 | 内容与用途 | 接入方式 / 当前状态 |
|---|---|---|
| [RHH graphics](https://github.com/rh-hideout/pokeemerald-expansion/tree/expansion/1.17.0/graphics) | 宝可梦正背面、图标、色板、道具与效果 | 首选同底座资源；已取新叶喵、呆火鳄、润水鸭的样本，保留 CREDITS |
| [RHH CREDITS](https://github.com/rh-hideout/pokeemerald-expansion/blob/expansion/1.17.0/CREDITS.md) | 上游贡献者与美术归属 | 已保存快照；逐物种/文件建立最终署名，不能只署名下载站 |
| [Team Aqua's Asset Repo](https://github.com/TeamAquasHideout/Team-Aquas-Asset-Repo) | 地图块、跟随精灵、人物、UI、音乐等 | 已核实目录与使用约定；按作者子目录选材，逐项检查不可修改例外 |
| [pret pokefirered](https://github.com/pret/pokefirered) | 关都和七之岛地图、碰撞、事件参考 | RHH 自带 FRLG 优先；作为差异核对来源 |
| [pret pokecrystal](https://github.com/pret/pokecrystal) | 城都路线与事件组织参考 | GBC 图块需重绘/重配色，脚本需重写 |
| [pret pokeheartgold](https://github.com/pret/pokeheartgold) | HGSS 城都扩展结构参考 | DS 数据作为参考，不能直接编译进 GBA |
| [pret pokeplatinum](https://github.com/pret/pokeplatinum) | 神奥地图与事件参考 | 提取拓扑意图并重建 GBA 图块/脚本，不宣称一键移植 |
| [Fusion Pixel Font](https://github.com/TakWolf/fusion-pixel-font) | 中文像素字形候选 | 工程记录 OFL 等上游许可；子集化、位图转换及 GBA 渲染仍待实现 |
| [Pokémon Showdown](https://github.com/smogon/pokemon-showdown) | 规则、对战数据和 PC 离线差分测试 | 只用于开发机工具；不把 Node.js 模拟器装入 ROM |

Team Aqua 的仓库总体允许使用/修改并要求追溯作者，但子资源可能有特别条件；聚合仓库不是所有宝可梦资产的统一授权证明。上游代码、官方原作素材和社区原创美术分开记录。为西班牙火箭队原创形态暂时只保存参考出处，新增羁绊形态优先自行设计和绘制。

## 工具链

| 工具 | 用途 | 选择与注意事项 |
|---|---|---|
| [RHH 安装指南](https://github.com/rh-hideout/pokeemerald-expansion/blob/expansion/1.17.0/INSTALL.md) | ARM GCC / make / 图像依赖 | 当前上游采用现代 GCC 构建；不要机械套用旧教程要求 agbcc |
| [Porymap](https://github.com/huderlem/porymap) | 编辑地图、连接、碰撞、事件和地区地图 | 直接操作反编译工程文件，非 ROM 二进制；Windows 可用官方发布包 |
| [Poryscript](https://github.com/huderlem/poryscript) | 更易维护的剧情脚本 | 编译为引擎脚本；接入前验证版本与自定义命令的兼容性 |
| [Porytiles](https://github.com/grunt-lucas/porytiles) | 图块编译与色板整理 | 从图像生成 Porymap 素材；锁定稳定版本，不依赖滚动 snapshot |
| [mGBA](https://mgba.io/) | 模拟器、调试、脚本回归 | 常规客户端与上游专用 `mgba-rom-test` 需求分开；测试通过仍需真机复核 |
| [LibreSprite](https://github.com/LibreSprite/LibreSprite) | 免费像素素材制作 | GPL-2.0 编辑器；输出作品权属另外记录 |
| [Aseprite](https://github.com/aseprite/aseprite) | 动画、CLI 导出和美术源文件 | 可选，有独立 EULA，不当作免费二进制工具打包 |
| [Flips](https://github.com/Sir-Walrus/Flips) | BPS/IPS 差分补丁 | 发布 BPS 时锁定基底版本与哈希；不提供游戏 ROM 下载 |

Windows 构建首选上游推荐的 WSL2；正式引擎工作树放 Linux 文件系统以减少 I/O 开销。现有 Windows 目录保存设计/内容源，通过明确同步步骤生成构建工作树；不要维护两份可任意手改的地图真源。系统安装属于后续环境阶段，此轮没有安装 WSL 或工具包。

## 资产管线规格

1. `assets/source/` 保存原创或已核实来源的素材；按 GBA 与未来 3D 表现分别组织，使用共同语义资产 ID 关联。PNG/ASE/MIDI 不作为核心领域结构；`assets/imported/` 保存候选研究输入，默认不参与构建。
2. 一项素材一条 manifest：作者、来源 URL、固定版本、SHA-256、使用/修改条件、用途、画布、色板、替代关系、审核状态。
3. 验证透明色、索引色、尺寸、朝向、图标、异色、正背面配对；不能把 Essentials 的 96px 素材包直接当作 GBA 规格。
4. 依据实际引擎对象和图块模式校验 palette/OAM/VRAM；常见战斗素材采用 4bpp 方案时每色板 16 项含透明索引，但不武断要求全游戏共用 16 色。
5. 编译/压缩后记录 ROM 字节变化及解压缓冲峰值；源 PNG 文件大小不代表 ROM 成本。
6. 在 mGBA 与真机检查正背面、闪光、进化、切换形态、双打遮挡、中文菜单；通过后才从候选状态转为生产资源。

音乐使用同引擎音序/MIDI 转换流程并尽量共享音色库。后世代长音轨、语音和全屏视频不直接照搬；先保留曲目辨识度与关键主题。

## 地图/美术缺口

合众、卡洛斯、阿罗拉、伽勒尔、洗翠、帕底亚以及 DLC 区域仍需大量 GBA 风格重建。尚未找到并验证覆盖全部地区、具备完整事件和明确逐项署名的统一现成素材包。需要建立每地区图块清单、建筑语言、NPC 清单和特殊地形规范，才能计算实际工作量。

样本下载记录见 `research/evidence/manifest.json`，属于研究归档，不能以下载完成代替适配或许可核对。
