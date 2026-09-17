# 极巨化资格纠正（2026-09-17）

问题：旧生成器对除了少数机制禁用者以外的所有基础物种创建极巨化状态。1,022 条里有 361 条只有推测资格，虽然标为研究候选，仍不应出现在实际图鉴中作为既有状态。用户指出铁壳蛹后，移除整个推测分支。

官方依据：

- [剑盾极巨化说明](https://swordshield.pokemon.com/en-us/gameplay/dynamaxing-max-moves/)解释该作极巨化机制，不能推出全国图鉴所有宝可梦都可用。
- [剑盾超极巨化说明](https://swordshield.pokemon.com/en-us/gameplay/gigantamax/)明确只有特定种类中的特定个体能够超极巨化，与普通极巨化不同。
- [HOME 官方兼容性说明](https://support.pokemon.com/hc/en-us/articles/360039592832-How-can-I-tell-which-games-I-can-transfer-my-Pok%C3%A9mon-to-in-Pok%C3%A9mon-HOME)提供按软件可传入范围查看的方法；该帮助页没有逐物种清单，不伪称已从中查到铁壳蛹条目。

本次逐物种交叉检查使用固定 pokemon-showdown 0.11.11 gen8 数据：weedle、kakuna、beedrill 是 Past；苍响、藏玛然特、无极汰那有 cannotDynamax。它是社区参考，不是官方直接证据。保留的 661 个基础物种状态都附 official_rule 和 availability_reference，official_species_specific_verification=false。它不是所有形态总数，也不能说这 661 条已逐条官方核实。

普通极巨化不要求宝可梦已经最终进化；不能因为用户指出铁壳蛹就反向推断所有蛹或未进化宝可梦均不可用。没有找到直接官方依据的条目不凭猜测建立；跨作品的 GO、动画、卡牌证据也不自动等价于剑盾资格。

新图鉴为 2,153 条档案（原 2,514 条中去掉 361 条），2,080 条参考内容、73 条待审内容。原有历史运行报告保留为当时结果，以本修订和 coverage.json 为现状。基础物种、已核定的形态身份和玩家现有登记不因数组索引变化丢失，稳定 ID 保存负责迁移。
