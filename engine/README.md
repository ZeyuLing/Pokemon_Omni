# GBA 引擎接入点

推荐 RHH pokeemerald-expansion 1.17.0，固定提交见 `config/project.json`。当前这里未放入引擎源码；研究证据位于 `research/evidence/rhh/`，不能将那些摘选文件视为可编译引擎。

正式接入保留 Git 历史，建立项目分支并锁定提交。先验证未改基线，再通过 `adapters/gba` 接入独立 `core/`。RHH 是 GBA 宿主及 legacy 行为参考，不是未来所有前端必须依赖的核心。尚未抽离的战斗域明确标注 legacy；抽离后展示层仅消费共享核心的结果，不能双写状态。迁移细节见 `docs/09-portable-core.md`。
