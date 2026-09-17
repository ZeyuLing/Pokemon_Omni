# 平台无关核心

已实现 `include/omni/battle_policy.h` / `src/battle_policy.c`：C99 战斗政策、等级、重赛状态决策、独立机制额度、获得路径合法性、原子入库。完整伤害、剧情状态机、人物关系与 AI 待实现。

另已实现 `include/omni/pokedex.h` / `src/pokedex.c`：查询、筛选、独立形态进度、版本化保存与稳定 ID 迁移；同一份代码用于原生测试、ARM 对象和浏览器 Wasm。运行 `tools/build_pokedex.ps1`。

核心无 RHH/渲染/OS 依赖；宿主提供内存、目录和进度。OmniMon 是验证模型，不是完整存档序列化布局。适配器需保留真实宝可梦全字段并负责持久事务。见 `docs/10-battle-policy-legality.md`。

运行 `./tools/test_core.ps1`。同一 C 实现已在 Windows 测试并交叉编译 ARM7TDMI/Thumb 对象；尚未链接 ROM。
