# 开发机合法性参考工具

依赖固定为 pokemon-showdown 0.11.11，锁文件记录内容完整性。首次使用在本目录运行 `pnpm install --frozen-lockfile --ignore-scripts --no-optional`，然后 `node test.cjs`。

用法：`node validate.cjs --format gen9nationaldexag --team team.json`。输入是 Showdown set 对象数组，例如 `[{"species":"Charizard","ability":"Blaze","moves":["Flamethrower"],"nature":"Timid","evs":{"spa":252,"spe":252,"spd":4}}]`。

退出码：0 通过，1 队伍不合法，2 配置/输入文件错误。调用时不会修改原始队伍。参考赛制必须显式指定；National Dex 不代表本项目所有机制共存政策，也不涵盖剧情捕捉门槛或原创形态。不同格式使用各自上游规则；输入前置范围采用本项目现代数值范围。

这是内容开发的参考工具，不在 GBA 上运行。正式内容编译器仍需将本项目采用的来源规则与例外生成紧凑目录，并与参考结果做差分。

## 图鉴源数据

构建器合并固定 npm 数据、research/catalog-sources 的提交／SHA 锁定 CSV、官方图鉴快照、图片元数据以及作者羁绊事实摘录。build-pokedex.cjs 离线生成目录、C 表、覆盖和缺口报告。更新源数据是显式维护工作，不能把上游 master 当作可复现版本。

在线维护工具：tools/fetch_official_dex.py（官方公开事实）、tools/fetch_form_art_metadata.py（仅图片 URL 元数据）、tools/check_art_references.py（HEAD 状态）、tools/import_champions_reference.cjs（固定提交五条特性）、tools/import_rocket_reference.py（本地作者文档事实导入）。维护后需重新构建、对账及更新基线；完整记录见 docs/12-pokedex-implementation.md。
