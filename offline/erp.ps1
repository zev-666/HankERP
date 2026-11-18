# ═══════════════════════════════════════════════════════════════════
# EVEREVO ERP 離線版管理腳本（v2.3.11）
#
# 平常不用直接執行這支：點兩下同資料夾的 Start-ERP.bat／Stop-ERP.bat 等即可。
# 進階用法（PowerShell，在 offline 資料夾）：
#   powershell -ExecutionPolicy Bypass -File erp.ps1 <指令> [參數]
#   指令：start | stop | status | backup | restore <檔案> | update |
#         lan-on | lan-off | export-images | import-images
#
# 相容 Windows PowerShell 5.1。這個檔案必須存成「UTF-8 with BOM」＋CRLF，
# 否則 5.1 會把中文讀成亂碼（.gitattributes 已設定，不要用會去掉 BOM 的編輯器另存）。
# 不會在畫面上顯示任何密碼或密鑰。
# ═══════════════════════════════════════════════════════════════════
param(
    [Parameter(Position = 0)][string]$Command = "start",
    [Parameter(Position = 1)][string]$Arg1 = ""
)

$ErrorActionPreference = "Continue"

$OfflineDir  = $PSScriptRoot
$Root        = Split-Path -Parent $OfflineDir
$ComposeFile = Join-Path $Root "docker-compose.offline.yml"
$EnvFile     = Join-Path $OfflineDir "offline.env"
$BackupDir   = Join-Path $Root "backups"
$ImagesTar   = Join-Path $OfflineDir "everevo-erp-images.tar"
$Images      = @("everevo-erp-backend:offline", "everevo-erp-frontend:offline", "postgres:15-alpine", "redis:7-alpine")

function Say($text)  { Write-Host $text }
function Ok($text)   { Write-Host ("  [OK] " + $text) -ForegroundColor Green }
function Warn($text) { Write-Host ("  [注意] " + $text) -ForegroundColor Yellow }
function Step($text) { Write-Host ""; Write-Host ("== " + $text + " ==") -ForegroundColor Cyan }
function Die($text) {
    Write-Host ("  [失敗] " + $text) -ForegroundColor Red
    Write-Host ""
    Write-Host "已停止。請把這個視窗的內容截圖或複製給 Claude。"
    exit 1
}

# docker compose 的共同前綴；用法：DC up -d
function DC {
    & docker compose -f $ComposeFile --env-file $EnvFile @args
}

# ── 環境檢查 ────────────────────────────────────────────────────────
function Test-DockerRunning {
    & docker info *> $null
    return ($LASTEXITCODE -eq 0)
}

function Assert-Docker {
    if (-not (Test-Path $ComposeFile)) { Die ("找不到 " + $ComposeFile + "（offline 資料夾要放在 HankERP 資料夾裡面）") }
    $cmd = Get-Command docker -ErrorAction SilentlyContinue
    if ($null -eq $cmd) {
        Say "  這台電腦還沒安裝 Docker Desktop。"
        Say "  1. 到 https://www.docker.com/products/docker-desktop/ 下載 Windows 版並安裝（需要網路，只要做一次）"
        Say "  2. 安裝後重新開機，開啟 Docker Desktop，等左下角顯示 Engine running"
        Say "  3. 再點一次 Start-ERP.bat"
        Die "尚未安裝 Docker Desktop"
    }
    if (Test-DockerRunning) { Ok "Docker 已在執行"; return }
    $exe = Join-Path $env:ProgramFiles "Docker\Docker\Docker Desktop.exe"
    if (Test-Path $exe) {
        Say "  Docker Desktop 沒有開，正在幫你開啟（約 1 分鐘）..."
        Start-Process -FilePath $exe
    } else {
        Warn "Docker 沒有在執行，請手動開啟 Docker Desktop"
    }
    for ($i = 0; $i -lt 60; $i++) {
        Start-Sleep -Seconds 3
        if (Test-DockerRunning) { Ok "Docker 已啟動"; return }
    }
    Die "等了 3 分鐘 Docker 還是沒有啟動。請手動開啟 Docker Desktop，等它顯示 Engine running 後再試一次"
}

# ── offline.env（密鑰、資料庫密碼、連接埠）────────────────────────────
function New-HexSecret($byteCount) {
    $bytes = New-Object byte[] $byteCount
    $rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
    $rng.GetBytes($bytes)
    $rng.Dispose()
    return (-join ($bytes | ForEach-Object { $_.ToString("x2") }))
}

function Read-EnvValue($key) {
    if (-not (Test-Path $EnvFile)) { return "" }
    foreach ($line in [System.IO.File]::ReadAllLines($EnvFile)) {
        if ($line.StartsWith($key + "=")) { return $line.Substring($key.Length + 1).Trim("'") }
    }
    return ""
}

function Set-EnvValue($key, $value) {
    $lines = New-Object System.Collections.Generic.List[string]
    $found = $false
    foreach ($line in [System.IO.File]::ReadAllLines($EnvFile)) {
        if ($line.StartsWith($key + "=")) { $lines.Add($key + "=" + $value); $found = $true }
        else { $lines.Add($line) }
    }
    if (-not $found) { $lines.Add($key + "=" + $value) }
    [System.IO.File]::WriteAllLines($EnvFile, $lines, (New-Object System.Text.UTF8Encoding($false)))
}

function Read-NewAdminPassword {
    # 測試用：設了環境變數 ERP_ADMIN_PASSWORD 就不詢問
    if ($env:ERP_ADMIN_PASSWORD) { return $env:ERP_ADMIN_PASSWORD }
    Say ""
    Say "  第一次使用：請設定「系統管理員」的登入密碼。"
    Say "  規則：至少 8 個字、要有數字，只能用英文、數字和符號（不能有空白和單引號）。"
    Say "  輸入時畫面不會顯示任何字，這是正常的。"
    while ($true) {
        $s1 = Read-Host -AsSecureString "  請輸入密碼"
        $s2 = Read-Host -AsSecureString "  再輸入一次"
        $p1 = (New-Object System.Net.NetworkCredential("", $s1)).Password
        $p2 = (New-Object System.Net.NetworkCredential("", $s2)).Password
        if ($p1 -cne $p2)                 { Warn "兩次輸入不一樣，請重來"; continue }
        if ($p1.Length -lt 8)             { Warn "至少要 8 個字"; continue }
        if ($p1 -notmatch "[0-9]")        { Warn "要包含至少一個數字"; continue }
        if ($p1 -notmatch '^[\x21-\x7e]+$') { Warn "只能用英文、數字和符號，不能有空白或中文"; continue }
        if ($p1.Contains("'"))            { Warn "不能包含單引號"; continue }
        return $p1
    }
}

function Initialize-EnvFile {
    if (Test-Path $EnvFile) { Ok "設定檔 offline.env 已存在（沿用）"; return }
    $adminPw = Read-NewAdminPassword
    $lines = @(
        "# 離線版設定（由 erp.ps1 產生）。內含密鑰與資料庫密碼：不要傳給別人、不要上傳。",
        "# 這個檔案遺失的話，資料庫就打不開了——備份資料時請連同這個檔案一起保存。",
        ("SECRET_KEY=" + (New-HexSecret 32)),
        ("DB_PASSWORD=" + (New-HexSecret 16)),
        ("SEED_ADMIN_PASSWORD='" + $adminPw + "'"),
        "ERP_BIND=127.0.0.1",
        "ERP_PORT=3000"
    )
    [System.IO.File]::WriteAllLines($EnvFile, $lines, (New-Object System.Text.UTF8Encoding($false)))
    Ok "已產生設定檔 offline.env（密鑰與資料庫密碼為隨機值，不顯示）"
}

function Get-Port {
    $p = Read-EnvValue "ERP_PORT"
    if ($p -eq "") { return 3000 }
    return [int]$p
}

function Test-PortBusy($port) {
    $client = New-Object System.Net.Sockets.TcpClient
    try {
        $client.Connect("127.0.0.1", $port)
        return $true
    } catch {
        return $false
    } finally {
        $client.Close()
    }
}

function Test-OurFrontendRunning {
    $id = (DC ps -q frontend) | Out-String
    return ($id.Trim() -ne "")
}

# 3000 被別的程式佔用（例如開發版）時，自動換一個連接埠。API 走同源，換埠不必重新建置。
function Resolve-Port {
    if (Test-OurFrontendRunning) { return }
    $port = Get-Port
    if (-not (Test-PortBusy $port)) { return }
    foreach ($candidate in @(3100, 3200, 3300, 3400)) {
        if (-not (Test-PortBusy $candidate)) {
            Set-EnvValue "ERP_PORT" $candidate
            Warn ("連接埠 " + $port + " 已被其他程式使用，改用 " + $candidate)
            return
        }
    }
    Die ("連接埠 " + $port + " 被佔用，而且找不到其他可用的連接埠")
}

# Windows 上 git 若把 .sh 轉成 CRLF，容器裡的 sh 會執行失敗；這裡直接修正成 LF。
function Repair-ShellScripts {
    $dir = Join-Path $Root "infra\backup"
    if (-not (Test-Path $dir)) { Die ("找不到 " + $dir) }
    foreach ($f in Get-ChildItem -Path $dir -Filter "*.sh") {
        $text = [System.IO.File]::ReadAllText($f.FullName)
        if ($text.Contains("`r`n")) {
            [System.IO.File]::WriteAllText($f.FullName, $text.Replace("`r`n", "`n"), (New-Object System.Text.UTF8Encoding($false)))
            Ok ("已修正換行格式：" + $f.Name)
        }
    }
}

# ── 等待服務 ────────────────────────────────────────────────────────
function Wait-Backend {
    for ($i = 0; $i -lt 60; $i++) {
        DC exec -T backend python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health', timeout=3)" *> $null
        if ($LASTEXITCODE -eq 0) { Ok "後端已就緒"; return }
        Start-Sleep -Seconds 3
    }
    Say ""
    DC logs --tail 40 backend
    Die "後端 3 分鐘內沒有啟動（上面是最後 40 行紀錄）"
}

function Wait-Frontend {
    $url = "http://localhost:" + (Get-Port) + "/login"
    for ($i = 0; $i -lt 40; $i++) {
        try {
            $r = Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 5
            if ($r.StatusCode -eq 200) { Ok "網頁已就緒"; return }
        } catch { }
        Start-Sleep -Seconds 3
    }
    Say ""
    DC logs --tail 40 frontend
    Die ("網頁 2 分鐘內沒有回應：" + $url)
}

function Sync-Database {
    DC exec -T backend alembic upgrade head
    if ($LASTEXITCODE -ne 0) { Die "資料庫結構更新失敗（alembic upgrade head）" }
    Ok "資料庫結構已是最新"
    DC exec -T backend python scripts/seed_data.py
    if ($LASTEXITCODE -ne 0) { Die "建立角色與管理員帳號失敗（seed_data.py）" }
    Ok "角色權限與管理員帳號已就緒"
}

function Show-Urls {
    $port = Get-Port
    Say ""
    Say "=================================================================="
    Say (" 這台電腦使用：  http://localhost:" + $port + "/login")
    if ((Read-EnvValue "ERP_BIND") -eq "0.0.0.0") {
        try {
            $ips = Get-NetIPAddress -AddressFamily IPv4 -ErrorAction Stop |
                Where-Object { $_.IPAddress -notlike "127.*" -and $_.IPAddress -notlike "169.254.*" -and $_.InterfaceAlias -notlike "vEthernet*" }
            foreach ($ip in $ips) { Say (" 其他電腦使用：  http://" + $ip.IPAddress + ":" + $port + "/login") }
        } catch {
            Say " 其他電腦使用：  http://<這台電腦的IP>:$port/login"
        }
    } else {
        Say " 目前只有這台電腦連得到。要讓同一個網路的其他電腦使用：點兩下 LAN-On.bat"
    }
    Say " 管理員帳號：    admin@guishan-acrylic.com（密碼是你第一次啟動時設定的那組）"
    Say "=================================================================="
}

# ── 指令 ────────────────────────────────────────────────────────────
function Invoke-Start {
    Step "1. 檢查環境"
    Assert-Docker
    Initialize-EnvFile
    Repair-ShellScripts
    Resolve-Port

    Step "2. 準備程式"
    & docker image inspect "everevo-erp-frontend:offline" *> $null
    $hasFrontend = ($LASTEXITCODE -eq 0)
    & docker image inspect "everevo-erp-backend:offline" *> $null
    $hasBackend = ($LASTEXITCODE -eq 0)
    if ($hasFrontend -and $hasBackend) {
        Ok "程式已安裝（不需要網路）"
    } else {
        Say "  第一次安裝：要下載並建置程式，需要網路，約 10 到 20 分鐘。之後啟動就不需要網路。"
        DC build
        if ($LASTEXITCODE -ne 0) { Die "建置失敗。第一次安裝需要網路；請確認網路正常後再點一次 Start-ERP.bat" }
        Ok "程式建置完成"
    }

    Step "3. 啟動"
    DC up -d
    if ($LASTEXITCODE -ne 0) { Die "啟動失敗（docker compose up）" }
    Wait-Backend
    Sync-Database
    Wait-Frontend

    Show-Urls
    if (-not $env:ERP_NO_BROWSER) { Start-Process ("http://localhost:" + (Get-Port) + "/login") }
    Say " 關閉這個視窗不會停止系統。要停止請點 Stop-ERP.bat。"
    Say " 電腦重開機後，只要 Docker Desktop 有開，系統會自動啟動。"
}

function Invoke-Stop {
    Assert-Docker
    if (-not (Test-Path $EnvFile)) { Die "還沒有啟動過（找不到 offline.env）" }
    DC stop
    if ($LASTEXITCODE -ne 0) { Die "停止失敗" }
    Ok "系統已停止。資料都還在，下次點 Start-ERP.bat 就會回來。"
}

function Invoke-Status {
    Assert-Docker
    if (-not (Test-Path $EnvFile)) { Die "還沒有啟動過（找不到 offline.env）" }
    DC ps
    Show-Urls
}

function Invoke-Backup {
    Assert-Docker
    if (-not (Test-Path $EnvFile)) { Die "還沒有啟動過（找不到 offline.env）" }
    Repair-ShellScripts
    Step "備份資料庫"
    DC run --rm -e BACKUP_ONCE=1 db-backup
    if ($LASTEXITCODE -ne 0) { Die "備份失敗（系統要先啟動才能備份）" }
    $latest = Get-ChildItem -Path $BackupDir -Filter "*.dump" | Sort-Object LastWriteTime -Descending | Select-Object -First 1
    if ($null -eq $latest) { Die ("備份指令成功但在 " + $BackupDir + " 找不到檔案") }
    Ok ("備份完成：" + $latest.FullName + "（" + [math]::Round($latest.Length / 1KB) + " KB）")
    Say "  請把這個檔案和 offline\offline.env 一起複製到隨身碟或另一台電腦。"
    Say "  系統每天也會自動備份一次到同一個資料夾，保留 30 天。"
}

function Resolve-DumpFile($path) {
    if ($path -eq "") { Die "請指定備份檔：把 .dump 或 hankerp-archive.tar.gz 拖到 Restore-ERP.bat 上面" }
    if (-not (Test-Path $path)) { Die ("找不到檔案：" + $path) }
    $full = (Resolve-Path $path).Path
    if ($full.EndsWith(".tar.gz") -or $full.EndsWith(".tgz")) {
        $tmp = Join-Path $env:TEMP ("erp-restore-" + [System.Guid]::NewGuid().ToString("N"))
        New-Item -ItemType Directory -Path $tmp | Out-Null
        # 指定 Windows 內建的 tar（bsdtar）；Git 附的 GNU tar 會把 C:\ 開頭的路徑當成遠端主機
        $tarExe = Join-Path $env:SystemRoot "System32\tar.exe"
        if (-not (Test-Path $tarExe)) { Die "找不到 Windows 內建的 tar.exe（需要 Windows 10 以上）。請先自行解壓縮，再把裡面的 .dump 檔拖到 Restore-ERP.bat" }
        & $tarExe -xzf $full -C $tmp | Out-Null
        if ($LASTEXITCODE -ne 0) { Die "解壓縮失敗" }
        $dump = Get-ChildItem -Path $tmp -Recurse -Filter "hankerp-*.dump" | Select-Object -First 1
        if ($null -eq $dump) { Die "壓縮檔裡找不到 hankerp-*.dump" }
        Ok ("從封存檔取出：" + $dump.Name)
        return $dump.FullName
    }
    return $full
}

function Invoke-Restore($path) {
    Assert-Docker
    if (-not (Test-Path $EnvFile)) { Die "請先點 Start-ERP.bat 啟動一次，再還原資料" }
    $dump = Resolve-DumpFile $path
    $stream = [System.IO.File]::OpenRead($dump)
    $head = New-Object byte[] 5
    $read = $stream.Read($head, 0, 5)
    $stream.Close()
    if ($read -lt 5 -or [System.Text.Encoding]::ASCII.GetString($head) -ne "PGDMP") { Die "這不是資料庫備份檔（開頭不是 PGDMP）" }

    Step "還原資料庫"
    Say ("  備份檔：" + $dump)
    Warn "這會用備份檔的內容「取代」目前離線版資料庫裡的所有資料。"
    if (-not $env:ERP_ASSUME_YES) {
        $answer = Read-Host "  確定要還原請輸入大寫 YES"
        if ($answer -cne "YES") { Say "  已取消，沒有做任何變更。"; return }
    }

    DC up -d db
    if ($LASTEXITCODE -ne 0) { Die "資料庫啟動失敗" }
    for ($i = 0; $i -lt 30; $i++) {
        DC exec -T db pg_isready -U erp_user -d acrylic_erp *> $null
        if ($LASTEXITCODE -eq 0) { break }
        Start-Sleep -Seconds 2
    }

    Repair-ShellScripts
    Say "  先備份目前的資料（還原出問題時可以救回來）..."
    DC run --rm -e BACKUP_ONCE=1 db-backup
    if ($LASTEXITCODE -ne 0) { Warn "目前的資料庫是空的或備份失敗，略過這一步" }

    DC stop backend celery
    DC cp $dump db:/tmp/restore.dump
    if ($LASTEXITCODE -ne 0) { Die "無法把備份檔複製進資料庫容器" }
    DC exec -T db psql -U erp_user -d acrylic_erp -v ON_ERROR_STOP=1 -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
    if ($LASTEXITCODE -ne 0) { Die "清空資料庫失敗" }
    DC exec -T db pg_restore -U erp_user -d acrylic_erp --no-owner --no-privileges --exit-on-error /tmp/restore.dump
    if ($LASTEXITCODE -ne 0) { Die "還原失敗。剛才的備份在 backups 資料夾，可以用它再還原回來" }
    DC exec -T db rm -f /tmp/restore.dump
    Ok "資料已還原"

    DC up -d
    if ($LASTEXITCODE -ne 0) { Die "啟動失敗" }
    Wait-Backend
    Sync-Database
    $users = (DC exec -T db psql -U erp_user -d acrylic_erp -tAc "select count(*) from users") | Out-String
    $customers = (DC exec -T db psql -U erp_user -d acrylic_erp -tAc "select count(*) from customers") | Out-String
    Ok ("帳號 " + $users.Trim() + " 個、客戶 " + $customers.Trim() + " 筆")
    Say "  還原後，登入密碼是備份當時的密碼（不是第一次啟動離線版時設定的那組）。"
    Show-Urls
}

function Invoke-Update {
    Step "重新建置（需要網路）"
    Assert-Docker
    if (-not (Test-Path $EnvFile)) { Die "還沒有啟動過，請直接點 Start-ERP.bat" }
    DC build
    if ($LASTEXITCODE -ne 0) { Die "建置失敗" }
    DC up -d
    if ($LASTEXITCODE -ne 0) { Die "啟動失敗" }
    Wait-Backend
    Sync-Database
    Wait-Frontend
    Ok "已更新到這個資料夾裡的程式版本"
    Show-Urls
}

function Set-Lan($bind) {
    Assert-Docker
    if (-not (Test-Path $EnvFile)) { Die "請先點 Start-ERP.bat 啟動一次" }
    Set-EnvValue "ERP_BIND" $bind
    DC up -d
    if ($LASTEXITCODE -ne 0) { Die "套用失敗" }
    Wait-Frontend
    if ($bind -eq "0.0.0.0") {
        Ok "已開放區域網路使用"
        Say "  其他電腦連不上時，通常是 Windows 防火牆擋住。請用「系統管理員身分」開啟 PowerShell，執行這一行："
        Say ("    netsh advfirewall firewall add rule name=""EVEREVO ERP"" dir=in action=allow protocol=TCP localport=" + (Get-Port))
        Say "  注意：區域網路內的連線沒有加密，請只在公司內部網路使用，不要把這個連接埠開放到網際網路。"
    } else {
        Ok "已關閉區域網路使用，只有這台電腦連得到"
    }
    Show-Urls
}

function Invoke-ExportImages {
    Assert-Docker
    Step "匯出程式映像（給沒有網路的電腦安裝用）"
    & docker save -o $ImagesTar $Images
    if ($LASTEXITCODE -ne 0) { Die "匯出失敗（要先在這台電腦成功啟動過一次）" }
    $f = Get-Item $ImagesTar
    Ok ("已匯出：" + $f.FullName + "（" + [math]::Round($f.Length / 1MB) + " MB）")
    Say "  把整個 HankERP 資料夾（含這個檔案）複製到另一台電腦，在那台執行 import-images，再點 Start-ERP.bat。"
}

function Invoke-ImportImages {
    Assert-Docker
    if (-not (Test-Path $ImagesTar)) { Die ("找不到 " + $ImagesTar) }
    & docker load -i $ImagesTar
    if ($LASTEXITCODE -ne 0) { Die "載入失敗" }
    Ok "程式映像已載入，現在可以點 Start-ERP.bat（不需要網路）"
}

Say ""
Say "EVEREVO ERP 離線版"
switch ($Command.ToLower()) {
    "start"         { Invoke-Start }
    "stop"          { Invoke-Stop }
    "status"        { Invoke-Status }
    "backup"        { Invoke-Backup }
    "restore"       { Invoke-Restore $Arg1 }
    "update"        { Invoke-Update }
    "lan-on"        { Set-Lan "0.0.0.0" }
    "lan-off"       { Set-Lan "127.0.0.1" }
    "export-images" { Invoke-ExportImages }
    "import-images" { Invoke-ImportImages }
    default         { Die ("不認得的指令：" + $Command + "（可用：start stop status backup restore update lan-on lan-off export-images import-images）") }
}
