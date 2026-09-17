# 内容真源约定

当前包含 `regions/index.json` 规划表与 `examples/partner-introduction.json` 平台无关任务契约样例（尚不可执行）。`species/national-index.json` 是基础物种身份表；`pokedex/entries.json` 是包含独立特殊形态条目的研究目录，不能当作已放行的完整战斗数据。后续按地区添加剧情、人物、遇敌、训练师、文本和获取路线；使用稳定符号 ID，不依赖文件顺序。

预定分区：`quests/`、`characters/`、`dialogue/`、`world/`、`trainers/`、`species/`、`text/zh-Hans/`。无需在无数据时创建大量空文件。Porymap 的 `data/maps/` 仅是 GBA 空间布局真源；剧情条件、人物关系与奖励必须在本层定义。3D 场景使用同一语义地点/人物 ID 的另一组绑定。

每地区清单须包含关键事件覆盖、map/warp 引用、版本分支、可获取宝可梦、难度阵容和里程碑奖励。JSON 是构建输入；GBA 不解析 JSON。
