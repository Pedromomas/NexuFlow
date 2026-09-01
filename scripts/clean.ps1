$Root = Resolve-Path "$PSScriptRoot\.."; Set-Location $Root
Remove-Item -Recurse -Force node_modules, dist, .angular, .\src-tauri\target, .\engine\build, .\engine\dist, .\engine\.pytest_cache, .\.pytest-tmp -ErrorAction SilentlyContinue
Get-ChildItem -Recurse -Directory -Filter __pycache__ -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item .\src-tauri\binaries\nexus-engine-*.exe -ErrorAction SilentlyContinue
Write-Host "NexuFlow limpo."
