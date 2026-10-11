$ErrorActionPreference = 'Stop'
$env:PYTHONUTF8 = '1'
Set-Location -LiteralPath 'F:\codes\python\CoSMiT'
$campaignProcess = Get-Process -Id 24380 -ErrorAction SilentlyContinue
$campaignStart = if ($campaignProcess) { $campaignProcess.StartTime } else { $null }
do {
    & 'F:\environment\python\miniconda3\envs\tf220\python.exe' 'benchmark/baselines/summarize_expansion_campaign.py' 'artifacts/baselines/expansion-campaign-2026-10-10'
    $campaignProcess = Get-Process -Id 24380 -ErrorAction SilentlyContinue
    if (-not $campaignProcess -or $campaignProcess.StartTime -ne $campaignStart) { break }
    Start-Sleep -Seconds 60
} while ($true)
& 'F:\environment\python\miniconda3\envs\tf220\python.exe' 'benchmark/baselines/summarize_expansion_campaign.py' 'artifacts/baselines/expansion-campaign-2026-10-10'

