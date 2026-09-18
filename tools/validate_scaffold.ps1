# Structural and provenance checks only; this does not test a ROM or battle engine.
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$jsonFiles = @(Get-ChildItem -LiteralPath (Join-Path $projectRoot 'config') -Filter '*.json')
$jsonFiles += Get-Item -LiteralPath (Join-Path $projectRoot 'content/regions/index.json')
$jsonFiles += Get-Item -LiteralPath (Join-Path $projectRoot 'content/examples/partner-introduction.json')
$jsonFiles += Get-Item -LiteralPath (Join-Path $projectRoot 'adapters/examples/partner-introduction.bindings.json')
$jsonFiles += Get-Item -LiteralPath (Join-Path $projectRoot 'content/species/national-index.json')
$jsonFiles += Get-Item -LiteralPath (Join-Path $projectRoot 'content/pokedex/entries.json')
foreach ($file in $jsonFiles) { $null = Get-Content -Encoding UTF8 -Raw -LiteralPath $file.FullName | ConvertFrom-Json }
$project = Get-Content -Encoding UTF8 -Raw -LiteralPath (Join-Path $projectRoot 'config/project.json') | ConvertFrom-Json
if ($project.target -ne 'portable_game_core' -or $project.primary_platform -ne 'gba_hardware') { throw 'Portable core / first GBA target contract changed.' }
if ($project.platforms.gba_hardware.rom_limit_bytes -ne 33554432) { throw 'GBA platform budget changed.' }
if ($project.architecture.platform_dependencies_in_core -ne $false) { throw 'Core must remain platform independent.' }
if ($project.engine.commit -notmatch '^[0-9a-f]{40}$') { throw 'Engine commit must be pinned.' }
$rules = Get-Content -Encoding UTF8 -Raw -LiteralPath (Join-Path $projectRoot 'config/rulesets.json') | ConvertFrom-Json
foreach ($flag in @('read_opponent_committed_action','read_hidden_opponent_state','affection_battle_bonuses','badge_stat_boosts','free_switch_after_opponent_faints')) {
    if ($rules.common.$flag -ne $false) { throw "Fairness invariant failed: $flag" }
}
$difficulty = Get-Content -Encoding UTF8 -Raw -LiteralPath (Join-Path $projectRoot 'config/difficulty.json') | ConvertFrom-Json
if (($difficulty.profiles.id -join ',') -ne 'easy,hard,insane') { throw 'Expected exactly three ordered difficulty profiles.' }
if ($rules.rulesets[0].independent_quotas -ne $true) { throw 'Mechanic quotas must be independent.' }
if ($rules.rulesets[0].permanent_mega.player_obtainable -ne $false) { throw 'Permanent Mega is NPC only.' }
$roster = Get-Content -Encoding UTF8 -Raw -LiteralPath (Join-Path $projectRoot 'content/bond/rocket-2.1-roster.json') | ConvertFrom-Json
if ($roster.forms.Count -ne 23 -or $roster.complete_version_verified) { throw 'Bond research provenance changed; review required.' }
$dexConfig = Get-Content -Encoding UTF8 -Raw -LiteralPath (Join-Path $projectRoot 'config/pokedex.json') | ConvertFrom-Json
if ($dexConfig.special_forms_are_standalone_entries -ne $true) { throw 'Special forms must be full Pokedex entries.' }
$dex = Get-Content -Encoding UTF8 -Raw -LiteralPath (Join-Path $projectRoot 'content/pokedex/entries.json') | ConvertFrom-Json
if (@($dex.entries.entry_id | Select-Object -Unique).Count -ne $dex.entries.Count) { throw 'Duplicate Pokedex entry IDs.' }
foreach ($id in @('charizardmegax','charizardmegay','charizardgmax','groudonprimal','necrozmaultra')) {
    if ($dex.entries.source_form_id -notcontains $id) { throw "Missing special form entry: $id" }
}
foreach ($rule in $rules.rulesets) {
    if ($rule.classification -eq 'official_format_reserved' -and ($rule.custom_bond_forms -or $rule.enabled)) { throw 'Unverified official rules must remain disabled and disallow custom forms.' }
}
$regions = (Get-Content -Encoding UTF8 -Raw -LiteralPath (Join-Path $projectRoot 'content/regions/index.json') | ConvertFrom-Json).regions
if (@($regions.id | Select-Object -Unique).Count -ne $regions.Count) { throw 'Duplicate region IDs.' }
$quest = Get-Content -Encoding UTF8 -Raw -LiteralPath (Join-Path $projectRoot 'content/examples/partner-introduction.json') | ConvertFrom-Json
$bindings = Get-Content -Encoding UTF8 -Raw -LiteralPath (Join-Path $projectRoot 'adapters/examples/partner-introduction.bindings.json') | ConvertFrom-Json
if ($quest.quest_id -ne $bindings.quest_id) { throw 'Example quest binding mismatch.' }
foreach ($platform in @('gba','open_world_3d')) {
    foreach ($anchor in $quest.required_anchor_ids) {
        if ($bindings.platforms.$platform.PSObject.Properties.Name -notcontains $anchor) { throw "Missing $platform anchor: $anchor" }
    }
}
$manifestPath = Join-Path $projectRoot 'research/evidence/manifest.json'
if (-not (Test-Path -LiteralPath $manifestPath)) { throw 'Run tools/fetch_research.ps1 to collect evidence first.' }
$manifest = Get-Content -Encoding UTF8 -Raw -LiteralPath $manifestPath | ConvertFrom-Json
foreach ($entry in $manifest) {
    if ($entry.status -ne 'downloaded') { throw "Missing evidence: $($entry.relative_path)" }
    $path = Join-Path $projectRoot $entry.relative_path
    if ((Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant() -ne $entry.sha256) { throw "Checksum mismatch: $path" }
}
Write-Output "PASS: $($jsonFiles.Count) config/example JSON files plus bond roster, $($regions.Count) unique regions, three difficulty profiles, independent quotas, information boundaries, two-platform anchors, $($manifest.Count) downloaded file hashes. Run test_core.ps1 separately for runtime checks."
