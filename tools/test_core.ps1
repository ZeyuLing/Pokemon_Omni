param([string]$Zig = (Join-Path $PSScriptRoot '../.cache/toolchains/ziglang/zig.exe'))
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
if (-not (Test-Path -LiteralPath $Zig)) { throw 'Provide -Zig path/to/zig.exe (tested with Zig 0.13.0), or install ziglang==0.13.0 into .cache/toolchains using Python pip.' }
Push-Location $root
try {
    $null = New-Item -ItemType Directory -Force -Path build
    & $Zig cc -std=c99 -Wall -Wextra -Werror -pedantic -O1 -Icore/include core/src/battle_policy.c tests/core/test_battle_policy.c -o build/test_battle_policy.exe
    if ($LASTEXITCODE) { throw 'Native compilation failed.' }
    & ./build/test_battle_policy.exe
    if ($LASTEXITCODE) { throw 'Native tests failed.' }
    & $Zig cc -target arm-freestanding-eabi -mcpu=arm7tdmi -mthumb -std=c99 -Wall -Wextra -Werror -pedantic -Os -ffreestanding -Icore/include -c core/src/battle_policy.c -o build/battle_policy_arm.o
    if ($LASTEXITCODE) { throw 'ARM7TDMI cross compilation failed.' }
    Write-Output 'PASS: same core compiled for ARM7TDMI/Thumb. Object compilation only; not a linked ROM or hardware test.'
} finally { Pop-Location }
