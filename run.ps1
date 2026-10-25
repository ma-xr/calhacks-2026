# CommonGround: one command to set up and run everything locally on Windows (PowerShell).
#
#   .\run.ps1            set up on first run, start the engine (:8787), SpacetimeDB (:3000) and the web app (:8765), open the browser
#   .\run.ps1 -NoOpen    same, without opening a browser
#   .\run.ps1 -Fresh     also wipe the live database (workspaces, plans, members)
#
# Ports: $env:HP_PORT (engine, default 8787), $env:WEB_PORT (web app, default 8765). SpacetimeDB uses 3000.
# Stop with Ctrl-C; the servers started here shut down together.
param([switch]$NoOpen, [switch]$Fresh)
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
$HpPort = if ($env:HP_PORT) { $env:HP_PORT } else { '8787' }
$WebPort = if ($env:WEB_PORT) { $env:WEB_PORT } else { '8765' }
New-Item -ItemType Directory -Force .run | Out-Null
function Say($m) { Write-Host "> $m" -ForegroundColor Cyan }
function Die($m) { Write-Host "x $m" -ForegroundColor Red; exit 1 }
function Up($url) { try { Invoke-WebRequest $url -UseBasicParsing -TimeoutSec 2 | Out-Null; $true } catch { $false } }

# 1 - Python 3.9-3.12 (the engine pins numpy<2.1, which has no wheels for newer Pythons)
$Py = $null
foreach ($v in '3.12', '3.11', '3.10', '3.9') { try { $p = (& py "-$v" -c 'import sys;print(sys.executable)' 2>$null); if ($p) { $Py = $p.Trim(); break } } catch {} }
if (-not $Py) { Die 'Python 3.9-3.12 is required (try: py install 3.12, or uv python install 3.12).' }

# 2 - Engine environment (first run only)
if (-not (Test-Path backend\.venv\Scripts\uvicorn.exe)) {
  Say 'First run: creating backend\.venv and installing dependencies (about a minute)...'
  & $Py -m venv backend\.venv
  & backend\.venv\Scripts\python.exe -m pip install --quiet --upgrade pip
  & backend\.venv\Scripts\python.exe -m pip install --quiet -r backend\requirements.txt
}
if (-not (Test-Path .env)) { Say 'No .env found: the engine runs fully; AI features (planner text, Ask the city) stay off. See .env.example.' }

# 3 - The website (the 3D simulator pages are Max's and are used as committed)
if (-not (Test-Path mockup\site\shared\city.json)) { & backend\.venv\Scripts\python.exe -X utf8 scripts\build_site_map.py | Out-Null }
Copy-Item backend\workspaces\client\dist\live.mjs mockup\site\live.mjs -Force

$Procs = @()
try {
  # 4 - Engine
  if (Up "http://127.0.0.1:$HpPort/health") { Say "Engine already running on :$HpPort" }
  else {
    Say "Starting the simulation engine on port $HpPort..."
    $Procs += Start-Process -PassThru -WindowStyle Hidden -WorkingDirectory "$PSScriptRoot\backend" -FilePath "$PSScriptRoot\backend\.venv\Scripts\uvicorn.exe" `
      -ArgumentList 'hp.api:app', '--host', '0.0.0.0', '--port', $HpPort -RedirectStandardOutput .run\engine.log -RedirectStandardError .run\engine.err.log
  }

  # 5 - SpacetimeDB: the website's workspaces, invites and plans (database "commonground"; the 3D app's Go live uses "human-live", see run.sh --live). Optional: without it the site shows an offline banner.
  $St = (Get-Command spacetime -ErrorAction SilentlyContinue).Source
  if (-not $St -and (Test-Path "$env:LOCALAPPDATA\SpacetimeDB\spacetime.exe")) { $St = "$env:LOCALAPPDATA\SpacetimeDB\spacetime.exe" }
  if ($St) {
    if (Up 'http://127.0.0.1:3000/v1/ping') { Say 'SpacetimeDB already running on :3000' }
    else {
      Say 'Starting SpacetimeDB on :3000...'
      $Procs += Start-Process -PassThru -WindowStyle Hidden -FilePath $St -ArgumentList 'start' -RedirectStandardOutput .run\spacetime.log -RedirectStandardError .run\spacetime.err.log
      for ($i = 0; $i -lt 30 -and -not (Up 'http://127.0.0.1:3000/v1/ping'); $i++) { Start-Sleep -Milliseconds 500 }
    }
    if (-not (Test-Path backend\workspaces\node_modules)) { Say 'Installing the website module''s npm packages...'; Push-Location backend\workspaces; npm install --silent | Out-Null; Pop-Location }
    Say 'Publishing the website''s live module (commonground)...'
    Push-Location backend\workspaces
    $args_ = @('publish', 'commonground', '--server', 'local', '--yes'); if ($Fresh) { $args_ += '--delete-data=always' }
    & $St @args_ 2>&1 | Out-File ..\..\.run\publish.log
    if ($LASTEXITCODE -ne 0) { Pop-Location; Die 'Publishing failed. See .run\publish.log (after a schema change, rerun with -Fresh).' }
    Pop-Location
  } else { Say 'SpacetimeDB CLI not found: workspaces stay offline. Install it from https://spacetimedb.com/install' }

  # 6 - Web app
  if (Up "http://127.0.0.1:$WebPort/") { Say "Web server already running on :$WebPort" }
  else { $Procs += Start-Process -PassThru -WindowStyle Hidden -FilePath $Py -ArgumentList 'scripts\serve.py', $WebPort, 'mockup' -RedirectStandardOutput .run\web.log -RedirectStandardError .run\web.err.log }

  # 7 - Wait for the engine to calibrate its baseline
  Say 'Calibrating the baseline weekday...'
  for ($i = 0; $i -lt 180; $i++) {
    try { if ((Invoke-RestMethod "http://127.0.0.1:$HpPort/health" -TimeoutSec 2).baseline_ready) { break } } catch {}
    Start-Sleep 1
    if ($i -eq 179) { Die "The engine didn't become ready in 3 minutes. See .run\engine.err.log" }
  }
  $Url = "http://localhost:$WebPort/site/"
  if ($HpPort -ne '8787') { $Url = "$Url`?api=http://127.0.0.1:$HpPort" }
  Say "Ready -> $Url   (simulator only: http://localhost:$WebPort/variants/a1-skyline-clean/index.html)"
  Say 'Ctrl-C to stop. Logs are in .run\'
  if (-not $NoOpen) { Start-Process $Url }
  while ($true) { Start-Sleep 3600 }
} finally {
  foreach ($p in $Procs) { try { Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue } catch {} }
}
