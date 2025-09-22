param([string]$BaseUrl = "http://localhost:5000")

function Get-Code($Path) {
  try {
    $resp = Invoke-WebRequest -Uri "$BaseUrl$Path" -Method GET -UseBasicParsing -ErrorAction Stop
    return $resp.StatusCode
  } catch {
    if ($_.Exception.Response) { return $_.Exception.Response.StatusCode.Value__ }
    return 0
  }
}

function Get-Json($Path) {
  try { (Invoke-RestMethod -Uri "$BaseUrl$Path" -Method GET -ErrorAction Stop) } catch { $null }
}

function Check-Code($Path, $Expected) {
  $code = Get-Code $Path
  if ($code -eq $Expected) { Write-Host "✅ $Path → $code" }
  else { Write-Error "❌ $Path → $code (expected $Expected)"; exit 1 }
}

function Check-Json($Path, $TestScriptBlock, $Desc) {
  $json = Get-Json $Path
  if (& $TestScriptBlock $json) { Write-Host "✅ $Desc" }
  else { Write-Host ($json | ConvertTo-Json -Depth 6); Write-Error "❌ $Desc"; exit 1 }
}

Write-Host "🔍 Smoke tests → $BaseUrl"

Check-Code "/health" 200
Check-Code "/api/word-finder/_ping" 200
Check-Code "/api/word-finder/puzzle?mode=easy" 200
Check-Code "/game/api/quota?game=mini_word_finder" 401

Check-Json "/api/word-finder/_ping" { param($j) $j.ok -eq $true } "Ping ok:true"
Check-Json "/api/word-finder/puzzle?mode=easy" { param($j) $j.ok -eq $true -and $j.mode -eq "easy" } "Puzzle mode=easy"
Check-Json "/game/api/quota?game=mini_word_finder" { param($j) $j.ok -eq $false -and ($j.error -eq "unauthorized" -or $j.error -eq "degraded_mode") } "Quota protected"

Write-Host "🎉 All smoke tests passed\!"
