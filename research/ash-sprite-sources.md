# 小智行走素材核查（2026-09-28）

当前 ash-kanto-walk-v1 的头身比例被用户否决，不能当作验收模板。固定规范见 README「人物像素素材与比例」。用户随后提供合集，已接入究极绿宝石IV小智版原生九帧。

2026-09-30 接续：同一用户ROM的64×64原生XY小智正面已接入训练家卡、人物画册和生成设定集肖像；四帧背面完成解码核查，尚未接入入场或投球动画。源表重定位、调色板及实际ROM验证见 [接入记录](../docs/44-ash-native-trainer-art.md) 与 `assets/source/ash-iv-trainer.json`。下方“现有立绘衣装尚未统一”为此前增量的历史状态。

## 用户指定：究极绿宝石 IV 小智版

- 2019-10-15 转载帖：https://apk.tw/thread-923156-1-1.html
- 附件名称：〖小智版〗究極綠寶石IV小智版（通常版 ）.zip，页面标注约 9.2 MB；另有逆属性版和 VGC2019 版，不可混用版本名称。
- 页面称男主替换为小智、女主替换为瑟蕾娜；小智参考 XY 服装。该信息为转载说明，尚未对文件内容作验证，也未认定该帖是作者首发。
- 页面明确要求登录下载并列出碎钻积分；本次未取得附件，无 ROM 哈希与实机验证。
- 优先获取通常版原始 .gba 或含它的压缩包，归档到 assets/imported 后登记哈希，再解码各方向和动作，核查是否适配本作初代动画服装。不可把 XY 服装直接标作初代关都服装。
- 安卓聚合站多提供带模拟器 APK，页面版本号不能直接当作 ROM 版本号。

## 对照候选：Ash Gray

- 原改版作者 metapod23；补丁维护库：https://github.com/patrickfcarey/pokemon-ashgray-bugfix
- 本地研究补丁：.cache/ashgray.ips；SHA256 379e7ed2539ebd6956c32510f622ea2a86aeaf1e0e12d8862647b387c6742422。
- 补丁网址：https://raw.githubusercontent.com/patrickfcarey/pokemon-ashgray-bugfix/1.1/patches/ashgray-fork.ips
- 从补丁修改区域与固定版本 pret 火红原生 Red 图块／调色板重建了原位置候选九帧，可见红白帽、黑发、蓝衣与绿背包。原生 16×32 画布，未缩放人物。
- 本地候选预览 build/pallet/ashgray-inspect.png；仅作研究，不是已完成运行时替换。还需验证重定向指针、原游戏实际帧选取及完整动作，不能单凭原偏移解码断言全部原作运行效果。
- 补丁工具 MIT 不代表改版图像获 MIT 授权；素材署名与分发条件单独维护。

## 用户文件归档与实际接入

已收到 Myboy模拟器和游戏文件.zip，八个ROM逐文件安全写入 assets/imported 下的独立目录，未执行APK或文档；每个来源名称、大小、哈希见 assets/source/myboy-user-archive.json。指定小智文件为32MiB，SHA256 30a54ca97fe653dee226d004b1b9b36cc2065116089d9a8c7c96be99bbc0c8bb。来源文件名不能独立证明上游确切修订号。

原生行走图已按源ROM的图形结构、帧指针与调色板表提取并接入；完整提取偏移与逐帧哈希见 assets/source/ash-iv-overworld.json。与火红小茂、大木、赤红原生帧同尺度对照；静止可见身高19～20像素，源动画部分步幅21像素，保留原帧起伏。脚下格位碰撞不变。

验证：真实32MiB Omni GBA构建通过，611次按键开场自动测试通过，包括小茂胜负、服务器房间、捕捉教学、奖励一次性和存档；53项故事测试通过。九帧像素黄金哈希和源边界测试通过。已查看 build/pallet/ash-native-comparison.png 与 init-oak-review.png 实机截图。地图衣装是来源XY设计；现有立绘衣装尚未统一，骑行／冲浪／投球动作不在本次接入范围内。
