$ErrorActionPreference = "Stop"

$pythonPath = "C:\apps\submit-system\current\.venv\Scripts\python.exe"
$backendPath = "C:\apps\submit-system\current\backend"
$logPath = "C:\apps\submit-system\shared\logs\backend-startup.log"

try {
    Set-Location -LiteralPath $backendPath

    & $pythonPath -m uvicorn app.main:app `
        --host 127.0.0.1 `
        --port 18111 `
        --workers 1 `
        --proxy-headers `
        --forwarded-allow-ips 127.0.0.1 *> $logPath

    exit $LASTEXITCODE
}
catch {
    $message = "[{0:u}] Backend launcher failed: {1}" -f `
        (Get-Date).ToUniversalTime(), `
        ($_ | Out-String)
    $message | Out-File -FilePath $logPath -Append -Encoding utf8
    exit 1
}
