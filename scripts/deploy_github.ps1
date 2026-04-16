# GitHub Pages 部署脚本
# 用浏览器自动化创建仓库，然后 git push

$env:CATPAW_CONVERSATION_ID = "deploy-lex-kb-$(Get-Date -Format 'HHmmss')"
$env:ELECTRON_RUN_AS_NODE = "1"
$catdesk = "D:\program\CatPaw Desk\CatPaw Desk.exe"
$cli = "D:\program\CatPaw Desk\resources\cli\catpaw-cli.js"

function Run-Browser {
    param([string]$json)
    $result = & $catdesk $cli browser-action $json 2>&1
    $result | Out-String
}

Write-Host "=== 步骤1: 打开 GitHub 创建仓库页面 ===" -ForegroundColor Cyan
$r = Run-Browser '{\"action\":\"navigate\",\"url\":\"https://github.com/new\"}'
Write-Host $r

Start-Sleep -Seconds 2

Write-Host "=== 步骤2: 获取页面快照 ===" -ForegroundColor Cyan
$r = Run-Browser '{\"action\":\"snapshot\",\"interactive\":true}'
Write-Host $r

Start-Sleep -Seconds 1

Write-Host "=== 步骤3: 填写仓库名 ===" -ForegroundColor Cyan
$r = Run-Browser '{\"action\":\"fill\",\"selector\":\"@e41\",\"value\":\"lex-fridman-knowledge-graph\"}'
Write-Host $r

Start-Sleep -Seconds 1

Write-Host "=== 步骤4: 截图确认 ===" -ForegroundColor Cyan
$r = Run-Browser '{\"action\":\"screenshot\"}'
Write-Host $r
