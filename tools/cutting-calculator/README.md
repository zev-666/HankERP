# 開條裁板計畫（cutplan.html）

- **使用者 2026-09-29 重新確認的正確版本（2026-09-24 修正版）**，後端裁切引擎的移植基準
- 單檔 HTML，瀏覽器直接開啟即可使用（字型從 Google Fonts 載入，離線時退回系統字型）
- 檔案指紋：55,318 bytes，SHA-256 `ff66c946dbcb99274bb40e64a523f52e22e577d69b88a4552fa7309923fd3672`
  （與使用者上傳的原檔逐位元組一致；改檔後請更新這一行）
- v2.3 相對於先前 repo 內 09-23 版（`6de7ffa7…`）的兩處修正：
  1. 評分刀數改用與 `cutList()` 相同的判斷邏輯（原本評分 22 刀、刀序表 23 刀，條尾剩 3.5～6.5mm 時會選錯方案）
  2. `numVal()` 的 S 板 fallback（原本讀取失敗會退回 2000×1000）

## 回歸基準（S 板 1915×1315、刀縫 3、修邊 0、剩料門檻 50 mm）

2026-09-23 以 Node 22 直接執行本檔 `nest()`／`cutList()`／`remnantsOf()` 重現：

| 案例 | 板數 | 利用率 | 刀數 | 整條剩餘料 | 碎料 |
|---|---|---|---|---|---|
| 範例 6 種尺寸（`loadDemo()`） | 1 | 92.2% | 23 | 1315×87 | 2 |
| 460×160 ×32 | 1 | 93.5% | 36 | 1315×63 | 0 |
| 460×160 ×100 | 4 | 73.1% | 114 | 1915×63 ×3（第 4 張空白是尾板，不計分） | 14 |

Python 版引擎必須對同樣輸入產生同樣結果（兩套引擎交叉比對）。


## v2.3.4 起：比對基準改為 cutplan 10-15 版

**本資料夾的 `cutplan.html` 仍是 09-24 版**（歷史對照）。v2.3.4 起 `engine_cli.js` 改抽自 Project 知識庫的
`claude/cutplan_2026-10-15.html`（138,434 bytes，SHA-256 `cc7058b5…`；這版有越南文介面與 Excel 匯出，
沒有放進 repo）。抽取範圍：

- `packOnce()`／`packByGroup()`：與 09-24 版相同
- `nest()`：多了沿短邊開條時不可轉件長寬對調（`piecesIn`）
- 刀序與剩料：`oldToResult()` → `mxCutList()`／`mxRemnants()`（cutplan「固定張數」模式那條路），
  多了「修窄」刀與修窄邊料
- **沒有** `mxOptimize()`（樣板法、補位、`REPEAT_TRY`）——那是 v2.4 的移植範圍

## 與後端 Python 引擎的交叉比對

`backend/app/ai/nesting_strip.py` 是本檔引擎的 Python 移植版。
兩者必須對同樣輸入產生**完全相同**的結果——不只板數，是逐件座標、逐刀位置與長度、
逐塊剩料尺寸與等級。

`engine_cli.js` 是從本檔抽出的引擎（去掉 DOM／UI，加上 stdin/stdout 介面），
供比對使用。它是**逐字複製**，不得自行修改邏輯；本檔改了就要同步抽一次。

```bash
# 單次執行
echo '{"sheetL":1915,"sheetW":1315,"kerf":3,"trim":0,"minRem":50,"remPref":"any",
       "parts":[{"id":"P1","name":"A","l":460,"w":160,"qty":32,"rot":true}]}' \
  | node tools/cutting-calculator/engine_cli.js

# 重新產生 Python 版的回歸基準（改了 cutplan.html 之後才需要）
cd backend && python scripts/regen_nesting_fixture.py
```

**基準的方向不可以反過來**：fixture 由 JS 引擎產生，Python 版來對答案。
拿 Python 的輸出去覆蓋 fixture，等於讓被測物自己出考題。

## 已知：本檔仍待修正的一處

`compare()`（比較 9 種板型）在板數相同時以「整條剩料大者勝」排序，
實測 6 種尺寸那組零件會推薦 M 板（1 張、54.51 才）為最省，
但 S 板同樣 1 張只要 27.98 才——材料成本差將近一倍。
這與本檔自己「總才數才是實際要買的材料量」的註腳矛盾。

後端 `nesting/service.py` 的 `compare_presets()` 已改以總才數為第一排序鍵；
本檔尚未同步修正，因此**兩邊的「最省」推薦目前會不一致**。
