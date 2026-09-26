# 人物立绘与动作资产

`manifest.json` 是 22 张人物立绘的源清单，按人物 ID 与人物小传、GBA 画册关联。

- `anime-cast-v1.png`：内置 imagegen 生成，小智、小茂、阿弘、优藤圣代、小明、真司。
- `rival-cast-v1.png`：内置 imagegen 生成，小银、阿杏、碧蓝、叶子、艾岚、彼特。
- 其余源图下载到忽略的 `assets/imported/cast/`，以 URL 与 SHA-256 锁定。
- `generation-prompts.json` 保存提示词与失败记录；不需要 API key，也没有使用 CLI API。

现成像素素材取自 [Pokémon Showdown 训练家档案](https://play.pokemonshowdown.com/sprites/trainers/)。**小进：kyledove；步美、小驱：Brumirage**。青绿、阿桔、小椿、赤红、大木、渡、坂木使用清单中列明的游戏源立绘（Game Freak／Nintendo／Creatures）。遵守署名和未经许可不编辑的要求；导入只做透明填边和目标硬件编码，不重绘或缩放源像素。

生成图集是可复查的初版设计，不是官方素材。80×80 GBA 转换文件位于 `build/pallet/cast/`；透明显影以硬件格式转换。生成设计仍需逐角色核对服饰和像素细节，缺少动画依据的身份仍以人物档案为准。

**立绘与动画分别验收**：四向行走、跑步、骑行、冲浪、投球、背面、表情、不同年龄与 3D 模型不能因一张人物立绘而标记完成。清单中的这些未完成项目保留空值。小智的地图行走暂用已登记的赤红占位，新行走图生成被服务拒绝。
