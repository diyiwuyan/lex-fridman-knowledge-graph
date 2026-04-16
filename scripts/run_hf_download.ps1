# 自动守护：HuggingFace 下载脚本崩了自动重启，直到完成
$scriptDir = "M:\cat分身\代理\lex-knowledge-base"
$logFile = "$scriptDir\logs\hf_download.log"
$progressFile = "$scriptDir\data\hf_download_progress.json"
$maxRestarts = 50
$restartCount = 0

Write-Host "=== HF Download Guardian ===" -ForegroundColor Cyan

while ($restartCount -lt $maxRestarts) {
    # 检查是否已完成（进度文件不存在 = 完成并清理了）
    $transcriptCount = (Get-ChildItem "$scriptDir\data\transcripts" -Filter "*.json" | Measure-Object).Count
    Write-Host "[$(Get-Date -Format 'HH:mm:ss')] Restart #$restartCount | Transcripts: $transcriptCount" -ForegroundColor Yellow

    # 读取当前进度
    if (Test-Path $progressFile) {
        $prog = Get-Content $progressFile | ConvertFrom-Json
        $offset = $prog.next_offset
        $total = 803239
        $pct = [math]::Round($offset / $total * 100, 1)
        Write-Host "  Resuming from offset $offset / $total ($pct%)" -ForegroundColor Gray
    }

    # 运行脚本
    $proc = Start-Process python -ArgumentList "-u", "scripts/05_fetch_hf_dataset.py" `
        -WorkingDirectory $scriptDir `
        -RedirectStandardOutput $logFile `
        -RedirectStandardError "$scriptDir\logs\hf_download_err.log" `
        -PassThru -NoNewWindow
    
    $proc.WaitForExit()
    $exitCode = $proc.ExitCode
    Write-Host "  Process exited with code $exitCode" -ForegroundColor Gray

    # 检查是否真正完成（进度文件被删除）
    if (-not (Test-Path $progressFile)) {
        Write-Host "[DONE] Download completed!" -ForegroundColor Green
        break
    }

    $restartCount++
    Write-Host "  Restarting in 5s..." -ForegroundColor DarkYellow
    Start-Sleep 5
}

Write-Host "Final transcript count: $((Get-ChildItem "$scriptDir\data\transcripts" -Filter "*.json" | Measure-Object).Count)"
