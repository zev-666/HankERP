# EVEREVO ERP 離線版（v2.3.11）

在一台 Windows 電腦上自己跑整套 ERP。**第一次安裝需要網路，之後完全不需要。**
資料都存在這台電腦裡，不會傳到任何地方。

## 需要什麼

- Windows 10 或 11（64 位元），記憶體 8GB 以上，硬碟可用空間 15GB 以上
- [Docker Desktop](https://www.docker.com/products/docker-desktop/)（免費安裝；安裝後要重新開機）
  - 授權：員工少於 250 人且年營收低於 1,000 萬美元的公司可免費使用，超過就要付費訂閱（Docker 官方條款）。

## 第一次使用

1. 安裝 Docker Desktop，重新開機，開啟它，等左下角顯示 **Engine running**。
2. 打開 `HankERP\offline` 資料夾，點兩下 **`Start-ERP.bat`**。
3. 第一次會請你設定**管理員密碼**（至少 8 個字、要有數字；輸入時畫面不顯示字是正常的）。
4. 第一次要下載並建置程式，約 10～20 分鐘。完成後瀏覽器會自動打開登入頁。
5. 用 `admin@guishan-acrylic.com` 和剛剛設定的密碼登入。

之後每次只要點 `Start-ERP.bat`，約 1 分鐘就會開好，**不需要網路**。
電腦重開機後，只要 Docker Desktop 有開（可在它的設定勾選「開機時啟動」），系統會自己起來。

## 每個檔案做什麼

| 點兩下 | 作用 |
|---|---|
| `Start-ERP.bat` | 啟動系統並打開登入頁 |
| `Stop-ERP.bat` | 停止系統（資料不會消失） |
| `Status-ERP.bat` | 看系統有沒有在跑、網址是什麼 |
| `Backup-ERP.bat` | 立刻備份資料庫到 `HankERP\backups` |
| `Restore-ERP.bat` | **把備份檔拖到它上面**：用備份取代目前的資料（會先自動備份現況，並要你輸入 YES 確認） |
| `LAN-On.bat` | 讓同一個區域網路的其他電腦、手機也能用（畫面會顯示網址） |
| `LAN-Off.bat` | 改回只有這台電腦能用 |

`Restore-ERP.bat` 接受 `.dump` 檔，也接受 2026-10-27 從舊主機下載的 `hankerp-archive.tar.gz`（會自動取出裡面的資料庫）。
還原後，登入密碼是「備份當時」的密碼。

## 備份（很重要）

- 系統每天自動備份一次到 `HankERP\backups`，保留 30 天。
- **這些備份和資料庫在同一台電腦上，硬碟壞掉會一起消失。** 請每週把最新的 `.dump` 檔和
  `offline\offline.env` 一起複製到隨身碟或另一台電腦。
- `offline.env` 裡有資料庫密碼和密鑰：不要傳給別人。弄丟它，現有的資料庫就打不開，只能用備份檔還原。

## 給多台電腦使用

1. 在主機那台點 `LAN-On.bat`，畫面會列出像 `http://192.168.1.20:3000/login` 的網址。
2. 其他電腦、手機連同一個 Wi-Fi／網路，用瀏覽器開那個網址。
3. 連不上時通常是 Windows 防火牆擋住，照畫面顯示的那一行指令處理（要用系統管理員身分執行）。
4. 主機那台要保持開機。建議在路由器把它的 IP 設成固定。

注意：區域網路內的連線沒有加密，只適合公司內部網路；不要把這個連接埠開放到網際網路。
要從外面連進來，請改用正式站的做法（網域＋Cloudflare，見 `DEPLOYMENT.md`）。

## 裝到一台完全沒有網路的電腦

1. 在有網路的電腦先成功啟動一次。
2. 在 `offline` 資料夾開 PowerShell，執行：
   `powershell -ExecutionPolicy Bypass -File erp.ps1 export-images`
3. 把整個 `HankERP` 資料夾（含產生的 `everevo-erp-images.tar`，但**不要**帶 `offline.env`，除非要連資料一起搬）複製到那台電腦。
4. 那台電腦要先裝好 Docker Desktop（安裝檔可在別處下載後用隨身碟帶過去）。
5. 執行 `powershell -ExecutionPolicy Bypass -File erp.ps1 import-images`，再點 `Start-ERP.bat`。

## 更新程式

拿到新版程式（`git pull` 或新的資料夾）後，在 `offline` 資料夾執行（需要網路）：
`powershell -ExecutionPolicy Bypass -File erp.ps1 update`
資料庫會保留，結構自動升級。更新前先點一次 `Backup-ERP.bat`。

## 和正式站、開發版的差別

- 資料庫與開發版（`docker compose up`）分開，互不影響。
- 預設網址 `http://localhost:3000`；3000 被佔用時會自動改用 3100 等並顯示在畫面上。
- 登入失敗的限制是「全部電腦合計每分鐘 30 次」（Docker Desktop 分不出是哪一台電腦）。
- 沒有官網用的網域、HTTPS 與 Cloudflare。

## 出問題時

把黑色視窗裡的內容截圖或複製給 Claude。常見情況：

| 畫面訊息 | 處理 |
|---|---|
| 尚未安裝 Docker Desktop | 照上面「需要什麼」安裝後重新開機 |
| 等了 3 分鐘 Docker 還是沒有啟動 | 手動開 Docker Desktop，等 Engine running 再試 |
| 建置失敗 | 第一次安裝需要網路；確認網路後再點一次 |
| 後端 3 分鐘內沒有啟動 | 把視窗內容給 Claude（裡面有最後 40 行紀錄） |
