param(
 [string]$Zig=(Join-Path $PSScriptRoot '../.cache/toolchains/ziglang/zig.exe'),
 [string]$Python='C:/Users/13758/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe',
 [switch]$StoryStart,
 [switch]$ReuseAssets
)
$ErrorActionPreference='Stop'
$root=Split-Path -Parent $PSScriptRoot
Push-Location $root
try {
 [string[]]$debugFlags = @()
 if (!$StoryStart) { $debugFlags += '-DOMNI_DEBUG_DEX' }
 if (!$ReuseAssets) {
 & $Python tools/build_pallet_assets.py
 if ($LASTEXITCODE) { throw 'Pallet map compilation failed' }
 & $Python tools/build_game_ui_assets.py
 if ($LASTEXITCODE) { throw 'Source ROM interface compilation failed' }
 & $Python tools/build_presentation_assets.py
 if ($LASTEXITCODE) { throw 'Presentation asset compilation failed' }
 & $Python tools/build_gba_assets.py
 if ($LASTEXITCODE) { throw 'Pokedex assets failed' }
 }
 & $Zig cc -target wasm32-freestanding -std=c99 -Wall -Wextra -Werror -O1 -DOMNI_TEST_WASM -ffreestanding -fno-builtin -nostdlib -Icore/include core/src/adventure.c core/src/pokedex.c adapters/headless/byte_ops.c tests/core/test_adventure.c '-Wl,--no-entry' '-Wl,--export=omni_adventure_test' '-Wl,--export=test_failure_line' '-Wl,--export=test_rounds_checked' -o build/pallet/test_adventure.wasm
 if ($LASTEXITCODE) { throw 'Adventure core test build failed' }
 node tests/adventure-wasm.cjs
 if ($LASTEXITCODE) { throw 'Adventure core tests failed' }
 & $Zig cc -target wasm32-freestanding -std=c99 -Wall -Wextra -Werror -O1 -ffreestanding -fno-builtin -nostdlib -Icore/include core/src/presentation.c tests/core/test_presentation.c '-Wl,--no-entry' '-Wl,--export=presentation_test' '-Wl,--export=presentation_failure_line' -o build/pallet/test_presentation.wasm
 if ($LASTEXITCODE) { throw 'Presentation core test build failed' }
 node tests/presentation-wasm.cjs
 if ($LASTEXITCODE) { throw 'Presentation core tests failed' }
 & $Zig cc @debugFlags -target arm-freestanding-eabi -mcpu=arm7tdmi -mthumb -std=c99 -O2 -ffreestanding -fno-builtin -fno-unwind-tables -fno-asynchronous-unwind-tables -nostdlib -Icore/include -Icontent/pokedex/generated -Icontent/training/generated -Ibuild/gba -Ibuild/pallet -Iadapters/gba adapters/gba/start.s adapters/gba/pallet_game.c adapters/gba/music.c adapters/gba/pokedex_game.c core/src/presentation.c build/pallet/presentation_data.c build/pallet/cast.s core/src/adventure.c core/src/pokedex.c core/src/training.c core/src/battle_stats.c content/pokedex/generated/catalog.c content/training/generated/plans.c build/gba/gba_data.c build/gba/blobs.s build/pallet/world_data.c build/pallet/world_blobs.s build/pallet/game_ui.s '-Wl,-T,adapters/gba/rom.ld' -o build/pallet/omni-pallet.elf
 if ($LASTEXITCODE) { throw 'Pallet GBA link failed' }
 & $Zig objcopy -O binary build/pallet/omni-pallet.elf build/pallet/omni-pallet.gba
 if ($LASTEXITCODE) { throw 'Pallet ROM export failed' }
 & $Python tools/finalize_gba.py --rom build/pallet/omni-pallet.gba --title 'OMNI PALLET' --code OMPL --scope 'Kanto opening: Pallet, Route 1, Viridian Center and Mart, Pikachu, early encounters and parcel quest. Full first journey not yet complete.' --asset build/pallet/world.bin
 if ($LASTEXITCODE) { throw 'Pallet header verification failed' }
} finally { Pop-Location }
