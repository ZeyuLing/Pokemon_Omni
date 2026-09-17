# 开发环境与可复现步骤

## 本轮实际检查

- 初始工作区为空，不是 Git 仓库；没有既有工程 AGENTS.md。
- Git 命令存在；`make`、`arm-none-eabi-gcc` 未在当前 PowerShell PATH 找到。
- `python.exe` 命中 WindowsApps 路径，未以此证明有可用 Python 解释器。
- `wsl --list --quiet` 返回需要安装 WSL 的提示，未得到可用发行版。
- GitHub 匿名 API 返回限流；Git 远端查询一次连接重置。随后通过发布页取得提交号，并成功从固定提交 raw URL 下载研究材料。没有完整引擎 checkout。
- 未安装系统组件、未运行上游编译、未执行游戏、未真机验证。

## 此刻可运行

在工作区 PowerShell 执行：

```powershell
./tools/fetch_research.ps1
./tools/validate_scaffold.ps1
./tools/test_core.ps1
node tools/legality-reference/test.cjs
```

下载内容是 15 份上游源码/文档证据，以及 3 个御三家每种 5 个美术文件（正面、背面、图标、普通/异色色板）。每个文件记录 URL、固定提交、大小与 SHA-256。校验 JSON、地区 ID 唯一性、公平设计不变量与下载完整性。

这些检查不生成 `.gba`。设计 JSON 尚未直接驱动运行时；C 政策实现与配置共同维护。核心测试使用缓存内 Zig 0.13.0，支持通过 `-Zig` 传入编译器路径；开发机参考工具依赖见其 README。

跨平台修订新增：`core/` 与 `adapters/` 职责约定、共享任务和双平台锚点绑定样例。校验器也检查这两个样例的 JSON、任务关联和锚点覆盖；这不是任务解释器执行测试。当前已有可独立编译的 C99 对战政策核心和无画面测试程序，GBA 游戏适配与主机/ROM 对战一致性仍待实现。

## 下一阶段构建示例（本轮未执行）

依照固定版本[安装指南](https://github.com/rh-hideout/pokeemerald-expansion/blob/expansion/1.17.0/INSTALL.md)准备 Linux/WSL2。上游 Ubuntu 依赖包含 build-essential、binutils-arm-none-eabi、gcc-arm-none-eabi、libnewlib-arm-none-eabi、git、libpng-dev、python3。记录具体工具版本，必要时用固定容器环境；不要一上来依赖 latest 镜像。

以下在 Linux 工作目录中逐步执行，用于验证**未修改上游基线**：

```bash
git clone https://github.com/rh-hideout/pokeemerald-expansion.git
cd pokeemerald-expansion
git checkout -b omni/base e8bd1cd7b03fc032ea37e3ecd38b379b5d01a1e7
git rev-parse HEAD
make -j2
make check -j2
```

`make check` 的专用运行器和依赖应按上游测试说明准备，不把桌面 mGBA 可启动当作已具备测试环境。任务数量 2 是保守示例，之后按机器资源调整。

上游支持 FRLG 独立构建验证：

```bash
make clean
make firered -j2
```

这个命令不会产出本项目设计中的全地区 ROM。切换构建目标需要 clean，以固定版本文档为准。正式接入外层工程时再决定子模块/引擎项目分支，避免把演示克隆误当成双份真源。

## 持续集成计划

轻量数据校验 → 内容引用/资产校验 → ROM 编译 → 上游与自定义战斗测试 → 隐藏信息测试 → 链接预算 → 模拟器脚本回归 → 版本化产物与 SHA-256。

模拟器负责可自动化回归，真机负责性能、色板/音频、flash 保存与连线。未有真机结果的版本应标记为“模拟器通过，真机待验”。最终发布内容优先为补丁、源代码变更与构建记录；完整游戏 ROM 不在本项目资源下载脚本中提供。
