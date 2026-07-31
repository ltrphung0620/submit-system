$ErrorActionPreference = "Stop"

$pythonPath = "C:\apps\submit-system\current\.venv\Scripts\python.exe"
$backendPath = "C:\apps\submit-system\current\backend"
$stdoutLogPath = "C:\apps\submit-system\shared\logs\backend.stdout.log"
$stderrLogPath = "C:\apps\submit-system\shared\logs\backend.stderr.log"
$launcherLogPath = "C:\apps\submit-system\shared\logs\backend-launcher.log"

try {
    $process = Start-Process `
        -FilePath $pythonPath `
        -ArgumentList @(
            "-m",
            "uvicorn",
            "app.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            "18112",
            "--workers",
            "1",
            "--proxy-headers",
            "--forwarded-allow-ips",
            "127.0.0.1"
        ) `
        -WorkingDirectory $backendPath `
        -RedirectStandardOutput $stdoutLogPath `
        -RedirectStandardError $stderrLogPath `
        -NoNewWindow `
        -Wait `
        -PassThru

    exit $process.ExitCode
}
catch {
    $message = "[{0:u}] Backend launcher failed: {1}" -f `
        (Get-Date).ToUniversalTime(), `
        ($_ | Out-String)
    $message | Out-File -FilePath $launcherLogPath -Append -Encoding utf8
    exit 1
}
