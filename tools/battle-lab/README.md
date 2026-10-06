# Battle Lab：宿主对战训练基础

固定 `pokemon-showdown@0.11.11 / gen4ou`，包含开发机标准赛制参考后端与下述学习器。**尚未接入 Omni 正式结算或 GBA AI。**没有复制一份 JavaScript Omni 玩法逻辑；后续正式规则仍应由共享可移植 C 核心拥有。

2026-10-06 后续：已新增实际训练的 NumPy 策略／价值网络和自博弈更新。上面所述参考环境仍非 Omni 正式结算；学习器的实现、模型位置、测量与限制见 [训练记录](../../docs/battle-learning-v2.md)。

## 训练入口

训练只使用现有 NumPy 2.3.5 和 Showdown 依赖；入口不会安装依赖、下载数据或调用远程 GPU。当前机器的 `python` 命令是 Windows Store 别名，因此使用已验证的真实解释器：

```powershell
$battlePython = Join-Path $env:USERPROFILE '.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
& $battlePython tools/battle-lab/experiment.py --out build/battle-lab/my-training
```

`--out` 必须不存在。默认运行：冻结三个队伍分区 → 生成 256 局训练数据和 32 局开发数据 → 梯度／1、8、32 样本过拟合／检查点／跨语言一致性门禁 → 两种网络宽度 × 两种数据量 → 16 轮、每轮 64 局的新鲜自博弈和一次参数更新 → 开发评测。每阶段保存命令、退出状态、日志和模型；失败即停止下游，不替换旧输出。`--train-blocks`、`--rounds`、`--selfplay-blocks` 可显式调整有界预算。

主要新文件：

- `features.cjs`：84 维选手观察／候选动作特征，最多 9 个动作，v2 显式区分替身、强化、回复、保护、撒钉、转场等效果。
- `network.cjs`：与 Python 数学结构一致的只读模型加载与对局推理。
- `train.py`：NumPy 前向、解析梯度、Adam、模仿学习和 Monte Carlo actor-critic 更新；终局奖励实际进入 value 和策略梯度。
- `learning.cjs`：冻结组合分区、生成数据、执行神经网络对局、导出真实采样概率和按观察记录的样本。
- `selfplay.py`：每轮重新采样，只对采集该批数据的检查点做一次全批更新；记录并验证模型哈希，保留被隐藏机制拒绝的已采样动作。出现截断批次会明确失败，尚未实现截断 bootstrap。
- `experiment.py`：可复现完整工程训练流程；不会读取 protected 最终评测反馈。

当前目录中训练模型选择了全新初始化的两层小型网络，**不是预训练大模型、Transformer 或 AlphaZero 搜索模型**。已经发生实际参数训练，也不等于已经形成高水平战术。当前数据来自人工配置的模拟器对局，标为 `FIXTURE_NON_EMPIRICAL`；生成数据的教师仍是简单 `power` 策略。特征含显式威力先验，模仿成功不能证明超越教师。

模型 JSON、优化器 NPZ、轨迹和完整运行日志都在忽略的 `build/` 中。`requirements-training.txt` 记录唯一 Python 依赖，每轮 `environment.json` 记录实际解释器哈希、NumPy 与完整已安装包版本。当前精确重跑验证在同一运行环境的新进程中完成，不声称在另一台机器或另一种 BLAS 上逐位一致。

受保护评测还需 `--selection` 收据，固定模型哈希、协议、代码、对手、随机偏移和评测块数。独立 evaluator 执行后只供审计和最终报告，不反馈给训练或选模。这个边界由角色和哈希检查共同维护，不是操作系统访问控制沙箱。

## 运行

在仓库根目录执行。复用 `tools/legality-reference/package.json` 和 `pnpm-lock.yaml`，不新增第二套依赖。已有依赖时不必重新安装；首次安装：

```powershell
pnpm --dir tools/legality-reference install --frozen-lockfile --ignore-scripts --no-optional
node --test tests/battle-lab.test.cjs
node tools/battle-lab/cli.cjs evaluate --blocks 12 --seed 20261006
```

默认将结果写入新的 `build/battle-lab/<时间戳>/`。也可以指定一个**尚不存在**的目录：

```powershell
node tools/battle-lab/cli.cjs evaluate --blocks 12 --agents power,random --out build/battle-lab/my-run
node tools/battle-lab/cli.cjs replay --file build/battle-lab/my-run/b00000-l0.replay.json
node tools/battle-lab/cli.cjs evaluate --blocks 3 --agents power,power --trajectories --out build/battle-lab/my-data
```

Node.js 24.19.0 已验证；CLI、环境与测试仅使用 Node 内置库和现有 Showdown 依赖。输出、训练数据、依赖安装均受现有 `.gitignore` 排除。

## 文件与接口

| 文件 | 职责 |
|---|---|
| `reference.cjs` | 加载、检查锁定模拟器版本；内部消息解码器同样来自这一版本 |
| `environment.cjs` | `BattleEnvironment`、双方观察、动作提交、终止、截断、状态快照与分叉 |
| `agents.cjs` | 独立随机流；随机和基础威力启发式基线 |
| `fixtures.cjs` | 三套人工合成六人队伍；每次开局执行赛制合法性校验 |
| `episode.cjs` | 同时准备双方观察、调用基线、记录轨迹、逐步重放校验 |
| `evaluate.cjs` | 四局交换评测、统计、源文件清单、结果落盘 |
| `serve.cjs` | 无网络 JSONL 标准输入／输出接口，供后续 Python 训练器接入 |
| `cli.cjs` | 命令行入口 |

JavaScript 中直接 `require('./tools/battle-lab/environment.cjs')`，然后：

1. `new BattleEnvironment({teams: [team1, team2], seed: [1,2,3,4], maxTurns: 200})`。
2. 分别调用 `observe('p1')`、`observe('p2')`。观察对象为深拷贝且递归冻结。
3. 两方策略各自选择 `observation.actions` 中的一个 `id`；没有动作的选手等待。
4. `step({p1: 'move 1', p2: 'switch 2'})` 提交本次需要的动作。
5. 检查 `result()`；循环直到 `terminated` 或 `truncated`，最后 `close()`。

`step` 指一次请求处理，不等同于一整个回合。濒死替换、急速折返、被禁止的换人等可能生成额外决策帧。

## 信息与动作契约

- 观察只包含己方请求、分配给该选手的消息历史、公开回合号、己方错误和奖励。上游 `|split|` 消息由锁定版本的渠道解码器处理；敌方 HP 使用上游公开精度。真实队伍、环境种子、未公开后排、全知终局日志不会进入观察。
- 双方观察在调用任意一方策略前全部生成；之后统一提交所需动作。单方替换时另一方没有可选动作。
- `actions` 是**当前告知选手可尝试的动作**，不是用真实隐藏状态试探出来的全知合法集合。隐藏磁力等可能令换人提交失败；环境返回 `accepted: false` 并仅更新该选手的请求。另一方已提交指令保持锁定且不泄露。
- 禁止指令注入或跳过动作集合；全部输入动作先通过公开动作检查，再修改环境。若引擎因正常隐藏机制拒绝动作，则保留真实拒绝结果，不偷偷改选动作。
- agent 的独立 PRNG 不访问环境 PRNG。多调用策略不会改变随后伤害随机数。移除协议墙上时钟时间，保留游戏事件，确保观察摘要可复现。
- 策略的输入不包含 `BattleEnvironment`。这是可信代码的接口隔离，不是对恶意 Node 插件的进程安全沙箱。
- `snapshot()` / `fork()` / `configuration()` 属于可信宿主基础设施。快照含隐藏队伍、待提交动作和 RNG，**禁止把它当作公平搜索的真实已知局面**。未来信息集搜索需要从合法信念分布构造假想状态。
- 胜／负／平奖励为 `+1/-1/0`；非终局奖励为 0。达到步数或回合上限是 `truncated`，不伪装成平局，也不根据血量判胜。训练器应自行定义截断 bootstrap。
- 限定第四世代 OU 单打；拒绝其他格式。队伍预览、双打、多现代特殊机制与 Omni 原创规则都未接入这个适配器。

## Python 等外部训练器接入

启动 `node tools/battle-lab/cli.cjs serve`，每行发送一个 JSON，接收一个带相同 `id` 的 JSON。标准输出只有协议，未启动网络服务。

```json
{"id":1,"op":"reset","config":{"teams":["此处替换为合法队伍数组","另一方合法队伍数组"],"seed":[1,2,3,4]}}
{"id":2,"op":"observe","side":"p1"}
{"id":3,"op":"observe","side":"p2"}
{"id":4,"op":"step","choices":{"p1":"move 1","p2":"move 1"}}
{"id":5,"op":"close"}
```

第一行的队伍字符串是结构说明，必须替换为真实 Showdown set 数组。成功响应为 `{"id":...,"ok":true,"data":...}`；错误为 `ok:false,error`。非法重置不会销毁当前对局。没有快照／全知状态接口。调用方是可信训练编排器，应分别向双方模型转交各自观察，不把两个观察拼接成一方输入。

## 输出与评测含义

- `manifest.json`：版本、赛制、种子、参数、Node 环境和 LF 标准化 UTF-8 源文件 SHA-256；锁文件同样纳入摘要。
- `*.replay.json`：初始队伍、环境种子、双方动作、动作接受状态、每个决策前和终局的观察摘要。是**开发者私有全知重放材料**，不直接用于策略输入。`replay` 重新结算并核对每一步，不仅比较最后胜者。
- `report.json`：逐局结果、已完成对局的胜率／得分、截断数、全部对局得分上下界、四局块 bootstrap 和耗时。
- 可选 `transitions.jsonl`：按选手分别记录 `observation, action, accepted, reward, nextObservation, terminated, truncated`。等待帧的 action/accepted 为 null；被引擎拒绝的动作 accepted 为 false。模仿学习不能把等待或拒绝动作作为成功动作标签。最终奖励也记录给该帧等待的一方。文件同时包含双方记录，训练时必须按选手分离。

每个评测块包含四局：候选策略分别使用两队，并交换 p1/p2 位置。同一块使用共同环境种子，按策略身份分配 agent 种子。三个合成队伍组合轮换；块是置信区间的抽样单位，不能把块内四局视为独立样本。截断块不参与完成块 bootstrap；同时报告全部对局得分上下界以显露完成条件选择偏差。

bootstrap 为 2000 次重采样的近似百分位区间，仅描述此合成测试日程。块数不足或所有块得分相同则区间为 null，避免将全胜输出成“100% 确定的真实胜率”。少量块的区间也可能很不稳定。

`power` 只比较基础威力、标称命中、物种属性克制和 STAB；不计算精确伤害、不处理临时属性、特性免疫、强化价值和主动换人价值，不能代表强搜索基线。`random` 从已告知动作均匀抽样，包含频繁无效战略换人。三套队伍是覆盖集成路径的合成数据，不是高手配队或独立强度测试集。当前吞吐包括合法性检查、独立重放、哈希和磁盘输出，不是纯结算速度。

实际验证与下一阶段：[对战训练基础记录](../../docs/battle-training-foundation.md)。

## 动画回放

将保存的真实对局重新校验并导出为 Showdown 动画播放器：

```powershell
node tools/battle-lab/export-replay.cjs build/battle-lab/reproduce-v2/runs/protected-rl-power/protected-0-0-0.replay.json build/battle-lab/viewer/rl-vs-power.html
```

用浏览器打开输出 HTML，点击 Play；支持逐回合、调速和切换视角。导出前核对每一步观察摘要、动作接受状态和终局；仅把观众频道事件写入 HTML，不包含私有快照。页面记录原文件 SHA-256。播放器及精灵素材依赖 Showdown 在线资源，播放器版本不固定；结算仍由固定版本模拟器重建。不会上传对局到 Showdown 回放服务器。这是开发参考模拟器回放，不是 GBA ROM 画面。
