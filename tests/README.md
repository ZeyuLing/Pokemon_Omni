# 验证入口

- `tools/test_core.ps1`：Windows 本机 60,392 检查（含等级全矩阵），同源 C 编译 ARM7TDMI/Thumb 对象；需要 Zig 0.13.0。
- `node tools/legality-reference/test.cjs`：12 个真实 Showdown 参考检查，涵盖喷火龙非法神速、非法特性、EV/IV/等级、赛制禁限及无输入修改。
- `tools/validate_scaffold.ps1`：JSON、三档难度、独立额度、信息隔离、双平台剧情锚点及资源哈希。

核心测试使用合成物种/获得路径，不能替代全图鉴数据审核。实际 ROM 联接、真机性能、战斗效果差分、AI 信息隔离与掉电恢复尚待接入阶段验证。

图鉴：`tools/build_pokedex.ps1` 运行 C 原生测试并编译 ARM/Wasm；`node tests/pokedex-wasm.cjs` 对照整个生成目录；预览服务启动后 `node tests/pokedex-preview.cjs` 验证实际浏览器行为和响应式布局。Playwright 路径可通过 OMNI_PLAYWRIGHT_PATH 指定，浏览器测试使用本机 Edge。
