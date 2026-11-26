$ErrorActionPreference = 'Stop'
$projectDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$botProcess = Get-Process -Name 'ChinaStoreBot' -ErrorAction SilentlyContinue
if ($botProcess) {
    Write-Host 'Close ChinaStoreBot before updating, then run UpdateBot.bat again.' -ForegroundColor Yellow
    exit 1
}

$tempDir = Join-Path $env:TEMP ('ChinaStoreBot-update-' + [guid]::NewGuid().ToString('N'))
$archive = Join-Path $tempDir 'ChinaStoreBot-windows.zip'
$extractDir = Join-Path $tempDir 'files'
$downloadUrl = 'https://github.com/Halypka/china-store/releases/download/windows-latest/ChinaStoreBot-windows.zip'

try {
    New-Item -ItemType Directory -Path $extractDir -Force | Out-Null
    Write-Host 'Downloading the latest bot version...'
    Invoke-WebRequest -Uri $downloadUrl -OutFile $archive -UseBasicParsing
    Expand-Archive -Path $archive -DestinationPath $extractDir -Force

    $newExe = Get-ChildItem -Path $extractDir -Filter 'ChinaStoreBot.exe' -File -Recurse | Select-Object -First 1
    if (-not $newExe) { throw 'The downloaded update does not contain ChinaStoreBot.exe.' }
    Copy-Item -Path $newExe.FullName -Destination (Join-Path $projectDir 'ChinaStoreBot.exe') -Force

    $newEnvExample = Get-ChildItem -Path $extractDir -Filter '.env.example' -File -Recurse | Select-Object -First 1
    if ($newEnvExample) {
        Copy-Item -Path $newEnvExample.FullName -Destination (Join-Path $projectDir '.env.example') -Force
        $envFile = Join-Path $projectDir '.env'
        if (-not (Test-Path $envFile)) { Copy-Item $newEnvExample.FullName $envFile }
    }

    Write-Host 'Bot updated successfully. Your .env and order database were preserved.' -ForegroundColor Green
}
catch {
    Write-Host ('Update failed: ' + $_.Exception.Message) -ForegroundColor Red
    exit 1
}
finally {
    if (Test-Path $tempDir) { Remove-Item -Path $tempDir -Recurse -Force -ErrorAction SilentlyContinue }
}

