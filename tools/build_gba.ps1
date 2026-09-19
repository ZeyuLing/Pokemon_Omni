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
 & $Zig cc -std=c99 -O1 -fno-builtin -Icore/include -Icontent/pokedex/generated -Icontent/training/generated -Ibuild/gba -Iadapters/gba adapters/gba/pokedex_game.c core/src/pokedex.c content/pokedex/generated/catalog.c content/training/generated/plans.c tests/core/test_gba_host.c -o build/gba/test_host.exe
 if ($LASTEXITCODE) { throw 'GBA host adapter test build failed' }
 & ./build/gba/test_host.exe
 if ($LASTEXITCODE) { throw 'GBA host adapter contract failed' }
 & $Zig cc -target arm-freestanding-eabi -mcpu=arm7tdmi -mthumb -std=c99 -DOMNI_GBA_STANDALONE -O2 -ffreestanding -fno-builtin -fno-unwind-tables -fno-asynchronous-unwind-tables -nostdlib -Icore/include -Icontent/pokedex/generated -Icontent/training/generated -Ibuild/gba -Iadapters/gba adapters/gba/start.s adapters/gba/pokedex_game.c core/src/pokedex.c core/src/training.c content/pokedex/generated/catalog.c content/training/generated/plans.c build/gba/gba_data.c build/gba/blobs.s '-Wl,-T,adapters/gba/rom.ld' -o build/gba/omni-dex.elf
 if ($LASTEXITCODE) { throw 'GBA link failed' }
 & $Zig objcopy -O binary build/gba/omni-dex.elf build/gba/omni-dex.gba
 if ($LASTEXITCODE) { throw 'GBA objcopy failed' }
 & $Python tools/finalize_gba.py
 if ($LASTEXITCODE) { throw 'GBA header failed' }
} finally { Pop-Location }
