"""
開條裁板引擎的回歸測試（v2.3）。

基準從哪裡來
------------
`fixtures/nesting_strip_regression.json` 的預期值**不是人工填的，也不是拿
Python 版自己的輸出當答案**——是用 Node 直接執行 `tools/cutting-calculator/cutplan.html`
（使用者確認的正確版，SHA-256 `ff66c946…923fd3672`）抽出的 JS 引擎產生的。

這就是 `CUTTING_STRIP_PLAN.md` 第七節指定的回歸方法：
「兩套引擎同輸入交叉比對」。Python 版是移植品，JS 版是規格。

要更新基準時，先改 `cutplan.html`，再重新產生 fixture，不可以反過來
拿 Python 的輸出去覆蓋 fixture——那等於讓被測物自己出考題。

涵蓋範圍
--------
25 個案例：文件記載的三組回歸基準、刀縫 0／小數、修邊、強制開條方向、
`minRem` 邊界、固定板數模式、不可旋轉長件、整板件、超出板面、
1000 件大量、多尺寸混合、9 種板型中的數種。

除了比對數值，另外獨立驗證幾何正確性（零重疊、零越界、刀序與排版一致），
這部分不依賴 fixture——就算 JS 版有 bug 也會被抓出來。
"""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.ai.nesting_strip import (  # noqa: E402
    SHEET_PRESETS,
    _round1,
    cut_list,
    map_rect,
    nest,
    remnants_of,
)

FIXTURE = json.loads(
    (Path(__file__).parent / "fixtures" / "nesting_strip_regression.json")
    .read_text(encoding="utf-8")
)
IDS = [c["name"] for c in FIXTURE]


def run(case_input):
    return nest(case_input["parts"], case_input["sheetL"], case_input["sheetW"],
                case_input["kerf"], case_input["trim"], case_input.get("maxSheets", 0),
                case_input.get("remPref", "any"), case_input.get("minRem", 50))


# ── 1. 與 JS 版交叉比對 ───────────────────────────────────────────────

@pytest.mark.parametrize("case", FIXTURE, ids=IDS)
def test_摘要與_js_引擎一致(case):
    res = run(case["input"])
    exp = case["expect"]
    if "error" in exp:
        assert res.get("error") == exp["error"]
        return
    assert res["sheetsUsed"] == exp["sheetsUsed"]
    assert res["placed"] == exp["placed"]
    assert res["util"] == pytest.approx(exp["util"], abs=1e-9)
    assert res["cutCount"] == exp["cutCount"]
    assert res["scraps"] == exp["scraps"]
    assert res["bandArea"] == pytest.approx(exp["bandArea"], abs=0.05)
    assert res["axis"] == exp["axis"]
    assert res["strategy"] == exp["strategy"]
    assert len(res["unplaced"]) == exp["unplaced"]
    assert sum(len(cut_list(sh, res)) for sh in res["sheets"]) == exp["totalCuts"]


@pytest.mark.parametrize("case", [c for c in FIXTURE if c["expect"].get("detail")],
                         ids=[c["name"] for c in FIXTURE if c["expect"].get("detail")])
def test_每件座標與每刀位置與_js_引擎一致(case):
    """逐件、逐刀、逐塊剩料比對。板數對不代表排法一樣。"""
    res = run(case["input"])
    exp = case["expect"]

    got_sheets = [{
        "usedH": _round1(sh["usedH"]),
        "strips": [{
            "y": _round1(st["y"]), "h": _round1(st["h"]), "x": _round1(st["x"]),
            "items": [{"id": it["id"], "x": _round1(it["x"]), "y": _round1(it["y"]),
                       "w": _round1(it["w"]), "h": _round1(it["h"]),
                       "rotated": it["rotated"]} for it in st["items"]],
        } for st in sh["strips"]],
    } for sh in res["sheets"]]
    assert got_sheets == exp["sheets"]

    got_cuts = [[{"n": c["n"], "phase": c["phase"], "dir": c["dir"], "pos": c["pos"],
                  "from": c["from"], "to": c["to"], "len": c["len"]}
                 for c in cut_list(sh, res)] for sh in res["sheets"]]
    assert got_cuts == exp["cuts"]

    min_rem = case["input"].get("minRem", 50)
    got_rem = [[{"x": _round1(r["x"]), "y": _round1(r["y"]),
                 "w": _round1(r["w"]), "h": _round1(r["h"]),
                 "long": _round1(r["long"]), "short": _round1(r["short"]),
                 "band": r["band"], "usable": r["usable"], "grade": r["grade"]}
                for r in remnants_of(sh, res, min_rem)] for sh in res["sheets"]]
    assert got_rem == exp["remnants"]


# ── 2. 幾何正確性（不依賴 fixture）────────────────────────────────────

@pytest.mark.parametrize("case", FIXTURE, ids=IDS)
def test_零重疊與零越界(case):
    """
    任兩件不得重疊（含刀縫），且全部必須落在可用區域內。

    這一項刻意不看 fixture：就算 JS 版本身排錯，這裡也會失敗。
    """
    res = run(case["input"])
    if res is None or "error" in res:
        return
    kerf = case["input"]["kerf"]
    trim = case["input"]["trim"]
    sheet_l, sheet_w = case["input"]["sheetL"], case["input"]["sheetW"]

    for sh in res["sheets"]:
        rects = []
        for st in sh["strips"]:
            for it in st["items"]:
                m = map_rect(res, it["x"], it["y"], it["w"], it["h"])
                rects.append(m)
                # 越界：必須落在修邊後的可用區域內
                assert m["x"] >= trim - 1e-6, f"越界 x={m['x']} < trim={trim}"
                assert m["y"] >= trim - 1e-6, f"越界 y={m['y']} < trim={trim}"
                assert m["x"] + m["w"] <= sheet_l - trim + 1e-6, f"越界右緣 {m}"
                assert m["y"] + m["h"] <= sheet_w - trim + 1e-6, f"越界下緣 {m}"

        for i in range(len(rects)):
            for j in range(i + 1, len(rects)):
                a, b = rects[i], rects[j]
                # 兩件之間的間隙至少要有一個刀縫。
                # kerf=0 時「剛好相接」是合法的，所以比的是間隙 >= kerf，
                # 不是「必須分開」——用 1e-6 吸收浮點誤差。
                gaps = (
                    b["x"] - (a["x"] + a["w"]),
                    a["x"] - (b["x"] + b["w"]),
                    b["y"] - (a["y"] + a["h"]),
                    a["y"] - (b["y"] + b["h"]),
                )
                assert max(gaps) >= kerf - 1e-6, f"重疊或刀縫不足：{a} vs {b}"


@pytest.mark.parametrize("case", FIXTURE, ids=IDS)
def test_評分刀數等於刀序表刀數(case):
    """
    2026-09-23 發現過的落差：評分用 22 刀、刀序表畫 23 刀，
    當條尾剩 3.5～6.5 mm 時評分會少算一刀，排序可能選錯方案。
    09-24 已把兩處統一，這裡把它釘住。
    """
    res = run(case["input"])
    if res is None or "error" in res:
        return
    assert res["cutCount"] == sum(len(cut_list(sh, res)) for sh in res["sheets"])


@pytest.mark.parametrize("case", FIXTURE, ids=IDS)
def test_排入件數不超過需求且未排入數吻合(case):
    res = run(case["input"])
    if res is None or "error" in res:
        return
    requested = sum(p["qty"] for p in case["input"]["parts"])
    assert res["placed"] + len(res["unplaced"]) == requested
    assert res["placed"] <= requested


# ── 3. 與舊 BFD 引擎的品質對照 ───────────────────────────────────────

@pytest.mark.parametrize("parts,sheet,expect_old,expect_new", [
    ([("A", 460, 160, 100)], (1915, 1315), 9, 4),
    ([("A", 160, 460, 100)], (1915, 1315), 10, 4),
    ([("A", 460, 160, 32)], (1915, 1315), 3, 1),
    ([("A", 600, 400, 4)], (2000, 1000), 2, 1),
])
def test_開條引擎用的板數不多於舊引擎(parts, sheet, expect_old, expect_new):
    """
    這些數字是 `CUTTING_ENGINE_CURRENT_STATE.md` 記錄的實測差距。
    釘住它們，避免日後有人「優化」開條引擎卻退回舊引擎的水準。
    """
    from app.ai.nesting_bfd import BFDNestingEngine, Part

    old_engine = BFDNestingEngine(sheet_length=sheet[0], sheet_width=sheet[1], kerf=3)
    old = old_engine.nest([Part(id=n, label=n, length=l, width=w, quantity=q)
                           for n, l, w, q in parts])
    new = nest([{"id": "P1", "name": n, "l": l, "w": w, "qty": q, "rot": True}
                for n, l, w, q in parts], sheet[0], sheet[1], 3, 0, 0, "any", 50)

    assert old["sheets_used"] == expect_old, "舊引擎的行為變了，對照基準需更新"
    assert new["sheetsUsed"] == expect_new
    assert new["sheetsUsed"] < old["sheets_used"]


def test_旋轉不變性_長寬對調用板數相同():
    """
    舊引擎的已知缺陷：同一零件長寬對調，9 張 vs 10 張。
    開條引擎兩個方向都會試，結果必須一致。
    """
    def sheets(l, w):
        return nest([{"id": "P1", "name": "A", "l": l, "w": w, "qty": 100, "rot": True}],
                    1915, 1315, 3, 0, 0, "any", 50)["sheetsUsed"]

    assert sheets(460, 160) == sheets(160, 460)


# ── 4. 板型常數 ──────────────────────────────────────────────────────

def test_九種板型且標準板為_S():
    assert len(SHEET_PRESETS) == 9
    assert SHEET_PRESETS[0]["length_mm"] == 1915
    assert SHEET_PRESETS[0]["width_mm"] == 1315
    assert "標準板" in SHEET_PRESETS[0]["name"]
    sizes = {(p["length_mm"], p["width_mm"]) for p in SHEET_PRESETS}
    for expected in [(1915, 1315), (2000, 1000), (2365, 1415), (1905, 1005),
                     (2045, 1045), (2205, 1105), (1855, 1245), (2565, 1315), (3095, 1585)]:
        assert expected in sizes, f"缺少板型 {expected}"
