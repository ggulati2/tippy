# Starts a built Tippy.exe without opening a browser window and checks that it really serves the app.
# Usage:  powershell -File windows\smoke-test.ps1 -Exe dist\Tippy\Tippy.exe
param([Parameter(Mandatory = $true)][string]$Exe)
$ErrorActionPreference = "Stop"
$port = 8791
$home_dir = Join-Path $env:RUNNER_TEMP ("tippy-smoke-" + [guid]::NewGuid())
if (-not $env:RUNNER_TEMP) { $home_dir = Join-Path $env:TEMP ("tippy-smoke-" + [guid]::NewGuid()) }
New-Item -ItemType Directory -Force $home_dir | Out-Null

# Test settings go in the environment of the child process only (a real family's data is never touched).
$env:TIPPY_HOME = $home_dir; $env:TIPPY_PORT = "$port"; $env:TIPPY_NO_BROWSER = "1"; $env:LLM_MODE = "off"
$process = Start-Process -FilePath $Exe -PassThru -WindowStyle Hidden
try {
    $page = $null
    foreach ($i in 1..40) {
        try { $page = Invoke-WebRequest -UseBasicParsing "http://127.0.0.1:$port/" -TimeoutSec 2; break } catch { Start-Sleep -Milliseconds 750 }
    }
    if (-not $page) { throw "Tippy did not answer within 30 seconds." }
    if ($page.Content -notmatch "Tippy|tippy") { throw "The start page does not look like Tippy." }
    if (-not $page.Headers["Content-Security-Policy"]) { throw "The protective headers are missing." }
    $settings = Invoke-RestMethod "http://127.0.0.1:$port/api/settings"
    if (-not $settings.PSObject.Properties.Name.Contains("language")) { throw "/api/settings gave an unexpected answer." }
    foreach ($file in @("js/app.js", "js/i18n-es.js", "css/style.css")) {
        $r = Invoke-WebRequest -UseBasicParsing "http://127.0.0.1:$port/$file"
        if ($r.StatusCode -ne 200) { throw "$file is missing from the app." }
    }
    $words = Invoke-RestMethod "http://127.0.0.1:$port/api/content/words?count=5&max_len=4"
    if ($words.items.Count -lt 1) { throw "The built-in content is missing." }
    if (-not (Test-Path (Join-Path $home_dir "data"))) { throw "The data folder was not created in TIPPY_HOME." }
    Write-Host "Smoke test passed for $Exe"
}
finally {
    if (-not $process.HasExited) { Stop-Process -Id $process.Id -Force }
    Get-Process -Name Tippy -ErrorAction SilentlyContinue | Stop-Process -Force
}
