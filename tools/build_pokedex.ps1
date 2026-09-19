param([string]$Zig = (Join-Path $PSScriptRoot '../.cache/toolchains/ziglang/zig.exe'))
$ErrorActionPreference='Stop'
$root=Split-Path -Parent $PSScriptRoot
Push-Location $root
try {
    node tools/legality-reference/import-localization.cjs
    if ($LASTEXITCODE) { throw 'Localization source validation failed' }
    node tools/legality-reference/export-dex.cjs
    if ($LASTEXITCODE) { throw 'National species export failed' }
    node tools/legality-reference/export-dex-entries.cjs
    if ($LASTEXITCODE) { throw 'Form identity export failed' }
    node tools/legality-reference/build-pokedex.cjs
    if ($LASTEXITCODE) { throw 'Catalog build failed' }
    node tools/legality-reference/build-training.cjs
    if ($LASTEXITCODE) { throw 'Training reference validation failed' }
    node tests/pokedex-content.cjs
    if ($LASTEXITCODE) { throw 'Content evidence checks failed' }
    $null=New-Item -ItemType Directory -Force -Path build/pokedex
    & $Zig cc -std=c99 -Wall -Wextra -Werror -pedantic -O1 -Icore/include core/src/pokedex.c core/src/battle_stats.c tests/core/test_pokedex.c -o build/pokedex/test_pokedex.exe
    if ($LASTEXITCODE) { throw 'Native Pokedex build failed' }
    & ./build/pokedex/test_pokedex.exe
    if ($LASTEXITCODE) { throw 'Native Pokedex tests failed' }
    & $Zig cc -std=c99 -Wall -Wextra -Werror -pedantic -O1 -Icore/include -Icontent/training/generated core/src/training.c content/training/generated/plans.c tests/core/test_training.c -o build/pokedex/test_training.exe
    if ($LASTEXITCODE) { throw 'Training core build failed' }
    & ./build/pokedex/test_training.exe
    if ($LASTEXITCODE) { throw 'Training tests failed' }
    & $Zig cc -target arm-freestanding-eabi -mcpu=arm7tdmi -mthumb -std=c99 -Wall -Wextra -Werror -pedantic -Os -ffreestanding -Icore/include -c core/src/pokedex.c -o build/pokedex/pokedex_arm.o
    if ($LASTEXITCODE) { throw 'ARM core build failed' }
    & $Zig cc -target arm-freestanding-eabi -mcpu=arm7tdmi -mthumb -std=c99 -Wall -Wextra -Werror -pedantic -Os -ffreestanding -Icore/include -c core/src/battle_stats.c -o build/pokedex/battle_stats_arm.o
    if ($LASTEXITCODE) { throw 'ARM HP rules build failed' }
    & $Zig cc -target arm-freestanding-eabi -mcpu=arm7tdmi -mthumb -std=c99 -Os -ffreestanding -Icore/include -Icontent/pokedex/generated -c content/pokedex/generated/catalog.c -o build/pokedex/catalog_arm.o
    if ($LASTEXITCODE) { throw 'ARM catalog build failed' }
    $exports=@('training_hash','training_count','training_status','dex_query_all','dex_ability','dex_stat','dex_parent','dex_hp','dex_max_hp','dex_count','dex_input_ptr','dex_result_ptr','dex_id','dex_flags','dex_total','dex_query','dex_record','dex_save','dex_load') | ForEach-Object { '-Wl,--export=' + $_ }
    & $Zig cc -target wasm32-freestanding -std=c99 -Oz -ffreestanding -fno-builtin -nostdlib -Icore/include -Icontent/pokedex/generated -Icontent/training/generated core/src/pokedex.c core/src/battle_stats.c core/src/training.c content/training/generated/plans.c content/pokedex/generated/catalog.c adapters/headless/pokedex_wasm.c '-Wl,--no-entry' @exports '-Wl,--export-memory' -o build/pokedex/pokedex.wasm
    if ($LASTEXITCODE) { throw 'Wasm core build failed' }
    Copy-Item -LiteralPath content/pokedex/catalog.json -Destination build/pokedex/catalog.json
    node tests/pokedex-wasm.cjs
    if ($LASTEXITCODE) { throw 'Wasm/catalog parity tests failed' }
    node tests/training-wasm.cjs
    if ($LASTEXITCODE) { throw 'Training Wasm parity failed' }
    Write-Output 'PASS: Pokedex native tests, ARM7TDMI core + catalog objects, browser Wasm built from same C core.'
} finally { Pop-Location }
