# Download selected upstream evidence and tiny Gen IX art samples, not an engine checkout.
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$config = Get-Content -Raw -LiteralPath (Join-Path $projectRoot 'config/project.json') | ConvertFrom-Json
$commit = $config.engine.commit
$baseUrl = "https://raw.githubusercontent.com/rh-hideout/pokeemerald-expansion/$commit"
$requests = @()
foreach ($path in @('README.md','FEATURES.md','CREDITS.md','INSTALL.md','Makefile','include/config/ai.h','include/constants/battle_ai.h','include/config/battle.h','include/config/pokemon.h','include/constants/species.h','docs/tutorials/how_to_frlg.md','docs/tutorials/how_to_testing_system.md','docs/install/windows/WSL.md','docs/install/linux/UBUNTU.md','docs/install/linux/DEBIAN.md')) {
    $requests += [pscustomobject]@{ source = "$baseUrl/$path"; relative_path = "research/evidence/rhh/$path"; kind = 'source_evidence' }
}
foreach ($species in @('sprigatito','fuecoco','quaxly')) {
    foreach ($file in @('front.png','back.png','icon.png','normal.pal','shiny.pal')) {
        $requests += [pscustomobject]@{ source = "$baseUrl/graphics/pokemon/$species/$file"; relative_path = "assets/imported/research_samples/$species/$file"; kind = 'art_sample_pending_individual_credit_review' }
    }
}
$records = @()
foreach ($request in $requests) {
    $dest = Join-Path $projectRoot $request.relative_path
    $null = New-Item -ItemType Directory -Force -Path (Split-Path -Parent $dest)
    try {
        # Repeated runs preserve the fixed-commit download and its checksum.
        if (-not (Test-Path -LiteralPath $dest)) {
            Invoke-WebRequest -Uri $request.source -OutFile "$dest.partial" -TimeoutSec 30
            Move-Item -LiteralPath "$dest.partial" -Destination $dest
        }
        $records += [pscustomobject]@{
            source = $request.source; relative_path = $request.relative_path; kind = $request.kind
            upstream_commit = $commit; accessed_at_utc = [DateTime]::UtcNow.ToString('o')
            status = 'downloaded'; bytes = (Get-Item -LiteralPath $dest).Length
            sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $dest).Hash.ToLowerInvariant()
        }
    } catch {
        $records += [pscustomobject]@{ source = $request.source; relative_path = $request.relative_path; kind = $request.kind; status = 'failed'; error = $_.Exception.Message }
    }
}
$manifest = Join-Path $projectRoot 'research/evidence/manifest.json'
$records | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $manifest -Encoding utf8
$failed = @($records | Where-Object status -eq 'failed')
Write-Output "Downloaded: $(@($records | Where-Object status -eq 'downloaded').Count); failed: $($failed.Count)"
if ($failed.Count) { $failed | Select-Object relative_path,error | Format-Table; exit 1 }
