# 开发机合法性参考工具

依赖固定为 pokemon-showdown 0.11.11，锁文件记录内容完整性。首次使用在本目录运行 `pnpm install --frozen-lockfile --ignore-scripts --no-optional`，然后 `node test.cjs`。

用法：`node validate.cjs --format gen9nationaldexag --team team.json`。输入是 Showdown set 对象数组，例如 `[{"species":"Charizard","ability":"Blaze","moves":["Flamethrower"],"nature":"Timid","evs":{"spa":252,"spe":252,"spd":4}}]`。

退出码：0 通过，1 队伍不合法，2 配置/输入文件错误。调用时不会修改原始队伍。参考赛制必须显式指定；National Dex 不代表本项目所有机制共存政策，也不涵盖剧情捕捉门槛或原创形态。不同格式使用各自上游规则；输入前置范围采用本项目现代数值范围。

这是内容开发的参考工具，不在 GBA 上运行。正式内容编译器仍需将本项目采用的来源规则与例外生成紧凑目录，并与参考结果做差分。
