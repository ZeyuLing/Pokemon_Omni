# 极巨化数值与图鉴显示

2026-09-17。种族值与实战能力值必须分别展示。普通极巨化、超极巨化沿用基础形态种族值，不能因为模型变大而提高种族值总和；变化是实际当前 HP、最大 HP、招式及机制交互。Mega 和原始回归等种族值变化属于另一机制，不混用。

[宝可梦官方极巨化对战攻略](https://www.pokemon.com/uk/features/dynamax-pokemon-battle-strategies-for-pokemon-sword-and-pokemon-shield)明确描述当前 HP、最大 HP 翻倍，以及结束时上限恢复。文章以翻倍场景介绍，不能把它当成覆盖所有极巨化等级和例外的完整公式。

细化公式的技术交叉依据为固定 pokemon-showdown 0.11.11，`data/conditions.ts` 第 768–774 行：脱壳忍者跳过 HP 放大；其他宝可梦用 1.5+0.05×极巨化等级，HP 向下取整。该细化依据明确标为社区实现，不冒称官方文档逐项列出。上游页面：https://github.com/smogon/pokemon-showdown/blob/master/data/conditions.ts ，构建使用本地固定版本而非滚动 master。

实现：`core/src/battle_stats.c`，HP 上限计算在共享 C 核心；同源导出 Wasm，并编译 ARM7TDMI。普通 HP 为 floor((2×HP种族值+IV+floor(EV/4))×等级/100)+等级+10；脱壳忍者固定 1。极巨化 HP 上限用整数运算 floor(普通HP×(30+极巨化等级)/20)，不修改种族值。接口校验等级、IV、EV、极巨化等级和溢出，错误返回 0。

UI 在普通极巨化和超极巨化条目展示独立计算区。例：喷火龙 HP 种族值 78，50 级，HP IV31、EV0：153 HP；极巨化等级 0 为 229，等级 10 为 306，HP 种族值仍为 78。计算器只展示上限；不是当前血量变化、回复功能、团体战首领多倍血量或完整战斗结算。

测试覆盖：上述喷火龙例、100级满HP努力值、脱壳忍者、越界/小数输入、溢出，以及普通HP 1–714 × 极巨化等级 0–10 的 C/Wasm 结果；浏览器验证 DMax/GMax、参数变更、错误输入、320px 布局与特殊 HP 例外。各图鉴条目的基础种族值未被改写。
