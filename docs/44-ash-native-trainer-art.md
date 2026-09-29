# 小智原生训练家素材接入（2026-09-30）

训练家卡与人物画册中的小智已由旧生成立绘改为用户提供的究极绿宝石IV小智版原生正面图，设定集网页复用同一构建肖像。地图九帧行走沿用此前接入，不改变人物比例、脚下碰撞或动画。衣装是动画XY参考的改版像素设计；本作仍为转变前少年阶段，不据此推定年龄、年代或新增经历。

## 来源与解码

- ROM：`assets/imported/ultra-emerald-4-ash-user/ultra-emerald-4-ash-user.gba`。
- SHA256：`30a54ca97fe653dee226d004b1b9b36cc2065116089d9a8c7c96be99bbc0c8bb`。用户文件名不能独立证明上游修订号。
- 提取器：`tools/ash_source_art.py` 的 `ash_trainer_art()`；清单：`assets/source/ash-iv-trainer.json`。
- 正面表 `0x101be90`，ID 71，LZ10图块 `0x36be40`；正面调色板表 `0x101c660`，调色板 `0x305b60`。解压得到2048字节图块和32字节调色板，按原生4bpp解码为64×64。
- 源ROM代码中的表引用也已校验：`0x5df78`／`0x5df80`。同一小智图块亦出现在扩展训练家记录中，不把它误标成赤红。
- 背面帧表 `0x2ff428`，四帧从 `0xd66480` 起，每帧2048字节；重定位背面表 `0x1d4c7c8`，调色板表 `0x1d4c788`。后者经代码引用 `0x5dfdc` 校验。旧表 `0x305d8c` 的男女主入口已指向占位调色板，不能据旧偏移直接取色。
- 具体像素作者未独立核实，署名保持“究极绿宝石小智版制作组”。ROM和解码PNG仅本地保存；Git仅记录提取代码、哈希和清单。

## 运行时使用

`assets/characters/manifest.json` 选择 `ash_iv_trainer_front` 解码器，`tools/build_presentation_assets.py` 在构建时从锁定ROM生成源PNG。正面仅在80×80透明画框内平移到 `(8,16)`，保留全部原像素。训练家卡和画册共用这一份 `cast.bin` 记录；没有调整面板位置或信息布局。这两个页面仍是本作现有原型界面，不能因替换立绘就称为已忠实对齐火箭队ROM的训练家卡布局。

生成设定集由 `tools/build_story_bible.py` 复制同一 `build/pallet/cast/ash.png`。人物档案、世界线外观备注与正文一起更新；没有填写未写的生平字段。

## 已核查但未接入

四帧背面可见相同的帽子、蓝白衣服和手套，已保存逐帧像素哈希。它们目前只供研究核查；源游戏的播放次序、时长和投球轨迹尚未完整验证。Omni当前战斗直接展示宝可梦，没有训练家入场或投球动画，本轮没有添加这类流程。`battle_back` 运行时绑定仍为空。骑行、冲浪、游泳和3D套件也未实现。

## 验证与复现

```powershell
python tools/build_presentation_assets.py
python tools/build_gba_assets.py
./tools/build_pallet.ps1 -ReuseAssets
python tests/initialization-art.py
node tests/initialization-rom.cjs
node tests/pallet-browser.cjs
python tools/build_story_bible.py
python tools/build_story_bible.py --check
python tests/story_bible.py
```

`initialization-art.py` 校验源正面及四帧背面黄金像素哈希，并逐像素核对生成画框只增加透明边距。`initialization-rom.cjs` 使用正常按键进入实际画册与训练家卡，将每个不透明像素与编译素材比较，并继续完整开场回归。

本轮实际结果：

- 真正32 MiB GBA ROM构建成功，头校验正确。SHA256：`90a02ae0b569ab177e1295ec1e1cbb24aeabb556999bc1f8e5ba90b14b5d330b`。
- 621次正常按键通过，含画册、训练家卡像素核对、小茂胜负、捕捉教学、存档与坏槽回退；共享C核心1255个确定性战斗回合通过。
- 浏览器实际加载ROM、SRAM隔离／导入／导出、音频开关、输入及320／390／820宽度布局通过。
- 故事生成与一致性检查通过，53项故事测试通过。
- 已查看 `build/pallet/init-ash-gallery.png`、`init-ash-trainer.png`、`init-ash-credits.png`，均为240×160实机帧；对应 `-review.png` 为三倍最近邻放大。正面完整显示，无文字遮挡或拉伸。训练家卡的位置名称来自当前地图，仍保持既有布局。
- `build/pallet/ash-trainer-comparison.png` 将小智与同一源ROM中的赤红、青绿正面放在相同原生尺度和画布底线，检查帽子、头部、肩宽及腿长。`ash-front-back-probe.png` 已检查四个背面姿势的衣装一致性；这不代表已验证源游戏完整投球时序。运行 `python tools/ash_source_art.py` 可重建九帧行走及正面／背面原生图集。
