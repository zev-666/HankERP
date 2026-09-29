"""
重新產生開條引擎的回歸基準（`tests/fixtures/nesting_strip_regression.json`）。

基準由 **JS 引擎**產生——`tools/cutting-calculator/engine_cli.js`，
它是從使用者確認的 `cutplan.html` 逐字抽出的。Python 版是移植品，來對答案。

**不可以反過來**：拿 Python 的輸出去覆蓋這份 fixture，等於讓被測物自己出考題。
只有在 `cutplan.html` 本身改動、且該改動是刻意的規格變更時，才重新產生。

需要 Node（本檔不進 CI，CI 只跑比對結果）：

    cd backend && python scripts/regen_nesting_fixture.py
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ENGINE = ROOT.parent / "tools" / "cutting-calculator" / "engine_cli.js"
FIXTURE = ROOT / "tests" / "fixtures" / "nesting_strip_regression.json"


def main():
    if not ENGINE.exists():
        print(f"✗ 找不到 {ENGINE}")
        return 1
    cases = json.loads(FIXTURE.read_text(encoding="utf-8"))
    out = []
    for c in cases:
        proc = subprocess.run(["node", str(ENGINE)], input=json.dumps(c["input"]),
                              capture_output=True, text=True, check=True)
        js = json.loads(proc.stdout)
        rec = {"name": c["name"], "input": c["input"]}
        if "error" in js:
            rec["expect"] = {"error": js["error"]}
        else:
            e = {"sheetsUsed": js["sheetsUsed"], "placed": js["placed"], "util": js["util"],
                 "cutCount": js["cutCount"], "scraps": js["scraps"], "bandArea": js["bandArea"],
                 "axis": js["axis"], "strategy": js["strategy"], "unplaced": js["unplaced"],
                 "totalCuts": sum(len(x) for x in js["cuts"])}
            # 大量案例只留摘要，避免 fixture 肥大；幾何正確性由測試的重疊／越界檢查涵蓋
            if js["placed"] <= 60:
                e.update({"sheets": js["sheets"], "cuts": js["cuts"], "remnants": js["remnants"]})
                e["detail"] = True
            else:
                e["detail"] = False
            rec["expect"] = e
        out.append(rec)
    FIXTURE.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    full = sum(1 for r in out if r["expect"].get("detail"))
    print(f"✅ 已重新產生 {len(out)} 個案例"
          f"（完整座標 {full}、僅摘要 {len(out) - full}），{FIXTURE.stat().st_size} bytes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
