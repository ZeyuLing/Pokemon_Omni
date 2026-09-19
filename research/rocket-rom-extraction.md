# 用户实际游玩版本：羁绊数据与图像核对

核验日期：2026-09-20。此次解决 23 个已收录羁绊条目的原始像素图缺口，并将只依赖文档的数值升级为 ROM 交叉核对；不宣称已移植羁绊战斗机制。

## 输入与身份

| 输入 | SHA-256 |
|---|---|
| 用户提供的“西班牙火箭队内置修改器版 .gba” | `033235cdd389c4c8cb1aa6d68a93954a55fd681c92a1a554ebc63431117b4eaf` |
| 已取得的作者发布包内 PkmnTeamRocket.gba | `008c256ca16c46d81f7417edfc2ec40ab9e3d2932e67bf5317e48d15b206ff9e` |

作者包来源、ZIP 与原文哈希见 `content/bond/author-reference.json`。用户文件登记见 `assets/source/rocket-user-rom.json`。两份 ROM 整体不同；本次不能由局部一致推断修改器未改变其他内容，也不能由 Emerald 文件头推断精确 2.1/2.1.1 版本。

## 定位与验证

以 [pret/pokeemerald 的 GFRomHeader 定义](https://github.com/pret/pokeemerald/blob/master/src/rom_header_gf.c) 为结构线索，读取 ROM 0x128/0x12C 的前后像表、0x130/0x134 的普通／异色调色板表、0x144 的名称表、0x1B8 的物种表。该改版物种记录长 36 字节；特性为偏移 24/26/28 的三个 uint16。结构不能直接套用其他版本。

22 条作者文档六项数值在两份 ROM 中各自只有一个完整匹配，且均落在同一张物种表。火神蛾通过作者 ROM 的 `Volcarona&` 名称以及相邻表记录定位，发现文档两项数值互换。按作者 ROM 拉丁字符表独立读出全部 23 个形态名称，再核对用户 ROM 相同内部编号的完整 36 字节记录及四份解压图像／调色板内容。名称解码参照 [pret 字符表](https://github.com/pret/pokeemerald/blob/master/charmap.txt)；用户汉化名称仅保留原始字节，不错误套用拉丁编码。

23 条的完整物种记录、前后像解压数据、普通／异色调色板均在两份 ROM 间完全一致。主特性编号也与作者文档所述特性逐条对应；这里验证的是编号与数据，不是特性战斗实现。

每个形态保存四个 64×64 PNG：正面、异色正面、背面、异色背面，共 92 个变体文件。美纳斯前像含两帧，本轮 PNG 展示首帧；其余对应图像为一帧，完整解压数据的哈希和帧数均保留，尚未重建动画时序。23 组普通／异色调色板完全相同，19 个形态前后像也复用相同内容，因此按 PNG 哈希去重只有 **27 张不同图像**。不得把 92 个文件称为 92 种不同外观，或凭空生成不同异色／背面替换它们。

## 文档差异与取值

| 形态 | 作者文档 | 两份 ROM 一致值 |
|---|---|---|
| 羁绊巴大蝶 | 超能力／飞行 | 虫／超能力 |
| 羁绊火神蛾 | 特防 130、速度 135 | 特防 135、速度 130 |

图鉴采用两份 ROM 一致值，保留作者原文摘录与差异。超甲狂犀与蚊香泳士原文总和算术错误仍保留；其六项数值已与 ROM 一致。部分双属性的先后顺序与文档不同，展示按 ROM 顺序，属性集合未变的不算实质矛盾。

原来的 11 份署名画师参考和 5 张 Omni 概念稿保留在来源清单及目录的 `alternative_art_references`，不再担当羁绊主图。当前 2,384 个目录条目均有主图引用，`missing_artwork` 为 0；这包含极巨化复用图、网络参考和本地提取图，不代表 2,384 张独立图片或发行素材全部完成。

## 复现与保存

```powershell
python tools/extract_rocket_rom.py --rom assets/imported/rocket-user/rocket-user-modifier.gba --author-archive .cache/rocket-author.zip
python tests/test_rocket_rom.py
./tools/build_pokedex.ps1
node tools/serve_pokedex.cjs
node tests/pokedex-preview.cjs
```

提取器仅接受上述两个 SHA-256，避免错版本静默生成错误素材；先验证全部记录再写出文件。产物位于 `assets/imported/rocket-user/bond-sprites/`，与 ROM 一样被 Git 忽略。`content/bond/rom-reference.json` 保存每条物种 ID、表项偏移、解压内容哈希、PNG 哈希和差异，可提交。换机器需要准备对应本地输入重新提取；普通内容构建不要求持有 ROM，页面遇到缺少本地图片会明确提示。

## 实际验证与剩余范围

- 五项解码测试：LZ 重叠回拷贝、非法／截断输入、ROM 指针边界、字符表、像素位置／通道／透明度与 PNG CRC。
- 全部 23 条目录记录与 92 个图片引用验证；原生 C、ARM7TDMI 对象编译、Wasm 与 JSON 数值一致性通过。
- 浏览器实际加载全部 92 个变体，核对 64×64 尺寸、正背面／异色切换、320px 无横向溢出与只读限制；联系表逐项视觉检查。
- 原始羁绊激活／解除逻辑、专属招式学习表、具体发布版本、实际战斗执行、Omni 剧情获取和正式 GBA ROM 集成仍未完成。当前只读标记与 `battle_data_approved=false` 保持到对应工作完成。
