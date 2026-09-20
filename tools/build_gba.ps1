param(
 [string]$Zig=(Join-Path $PSScriptRoot '../.cache/toolchains/ziglang/zig.exe'),
 [string]$Python='C:/Users/13758/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
)
$ErrorActionPreference='Stop'
$root=Split-Path -Parent $PSScriptRoot
Push-Location $root
try {
 & $Python tools/build_gba_assets.py
 if ($LASTEXITCODE) { throw 'GBA assets failed' }
 & $Zig cc -target wasm32-freestanding -std=c99 -O1 -DOMNI_TEST_WASM -ffreestanding -fno-builtin -nostdlib -Icore/include -Icontent/pokedex/generated -Icontent/training/generated -Ibuild/gba -Iadapters/gba adapters/gba/pokedex_game.c core/src/pokedex.c content/pokedex/generated/catalog.c content/training/generated/plans.c core/src/battle_stats.c adapters/headless/byte_ops.c tests/core/test_gba_host.c '-Wl,--no-entry' '-Wl,--export=omni_gba_host_test' '-Wl,--export=test_failure_line' -o build/gba/test_host.wasm
 if ($LASTEXITCODE) { throw 'GBA host adapter test build failed' }
 node tests/gba-host-wasm.cjs
 if ($LASTEXITCODE) { throw 'GBA host adapter contract failed' }
 & $Zig cc -target arm-freestanding-eabi -mcpu=arm7tdmi -mthumb -std=c99 -DOMNI_GBA_STANDALONE -O2 -ffreestanding -fno-builtin -fno-unwind-tables -fno-asynchronous-unwind-tables -nostdlib -Icore/include -Icontent/pokedex/generated -Icontent/training/generated -Ibuild/gba -Iadapters/gba adapters/gba/start.s adapters/gba/pokedex_game.c core/src/pokedex.c core/src/training.c core/src/battle_stats.c content/pokedex/generated/catalog.c content/training/generated/plans.c build/gba/gba_data.c build/gba/blobs.s '-Wl,-T,adapters/gba/rom.ld' -o build/gba/omni-dex.elf
 if ($LASTEXITCODE) { throw 'GBA link failed' }
 & $Zig objcopy -O binary build/gba/omni-dex.elf build/gba/omni-dex.gba
 if ($LASTEXITCODE) { throw 'GBA objcopy failed' }
 & $Python tools/finalize_gba.py
 if ($LASTEXITCODE) { throw 'GBA header failed' }
} finally { Pop-Location }
