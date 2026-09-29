"""
裁切排版服務層（v2.3）。

把 `app/ai/nesting_strip.py` 的開條引擎接成 ERP 要的輸出格式。
引擎本身刻意保持純粹（只認 dict、不認 Pydantic、不碰資料庫），
所有格式轉換、相容性處理都放在這一層。

回傳格式的相容性
----------------
`placements` 沿用舊引擎的欄位名（`part_label` / `sheet_index` / `x` / `y` /
`placed_length` / `placed_width` / `rotated`），舊前端不改也能跑。
新增的 `sheets`（含條帶、刀序、剩料）、`axis`、`strategy`、`total_cuts`
是開條引擎才有的東西，舊引擎沒有對應物。

`engine` 欄位標記演算法版本：舊紀錄沒有這個鍵就是 v2.2 以前的 BFD 引擎，
要比較新舊排版品質時分得出來。
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any, Iterable

from app.ai.nesting_strip import (
    CAI,
    SHEET_PRESETS,
    cut_list,
    map_rect,
    nest,
    remnants_of,
)

ENGINE_VERSION = "strip-v1"


def _to_pieces(parts: Iterable[Any]) -> list[dict]:
    """Pydantic 的 PartInput → 引擎吃的 dict。Decimal 一律轉 float，引擎只做浮點運算。"""
    out = []
    for i, p in enumerate(parts):
        out.append({
            "id": f"P{i + 1}",
            "name": p.label,
            "l": float(p.length_mm),
            "w": float(p.width_mm),
            "qty": int(p.quantity),
            "rot": bool(p.can_rotate),
        })
    return out


def _sheet_signature(sheet: dict) -> str:
    """
    整張板的排版內容指紋，四捨五入到 1mm。

    用途是把排法完全相同的板合併顯示（10000 件可能排出 59 張板但只有 7 種排法）。
    **比的是實際排版內容，不是只比件數**——件數相同但擺法不同的板必須分開。
    """
    parts = []
    for st in sorted(sheet["strips"], key=lambda s: s["y"]):
        items = [(round(it["x"]), round(it["w"]), round(it["h"]), it["id"])
                 for it in sorted(st["items"], key=lambda i: i["x"])]
        parts.append((round(st["y"]), round(st["h"]), tuple(items)))
    return repr(parts)


def run_nesting(parts: Iterable[Any], sheet_length_mm, sheet_width_mm, kerf_mm,
                trim_mm=0, rem_pref: str = "any", min_remnant_mm=50,
                max_sheets: int = 0) -> dict:
    """
    執行排版，回傳 ERP 格式的結果。輸入不合法時回傳 {"error": ...}。
    """
    sheet_l, sheet_w = float(sheet_length_mm), float(sheet_width_mm)
    kerf, trim = float(kerf_mm), float(trim_mm)
    min_rem = float(min_remnant_mm)

    pieces = _to_pieces(parts)
    requested = sum(p["qty"] for p in pieces)

    res = nest(pieces, sheet_l, sheet_w, kerf, trim, max_sheets, rem_pref, min_rem)
    if res is None:
        return {"error": "排版失敗：沒有任何可行方案"}
    if "error" in res:
        return {"error": res["error"]}

    placements: list[dict] = []
    sheets_out: list[dict] = []
    total_cuts = 0
    band_remnants: list[dict] = []
    all_remnants: list[dict] = []

    for si, sh in enumerate(res["sheets"]):
        cuts = cut_list(sh, res)
        total_cuts += len(cuts)
        rems = remnants_of(sh, res, min_rem)

        strips_out = []
        sheet_area_used = 0.0
        for st in sorted(sh["strips"], key=lambda s: s["y"]):
            items_out = []
            for it in sorted(st["items"], key=lambda i: i["x"]):
                m = map_rect(res, it["x"], it["y"], it["w"], it["h"])
                sheet_area_used += it["w"] * it["h"]
                items_out.append({
                    "part_id": it["id"], "part_label": it["name"],
                    "x": round(m["x"], 2), "y": round(m["y"], 2),
                    "length": round(m["w"], 2), "width": round(m["h"], 2),
                    "rotated": it["rotated"],
                })
                # 舊格式相容：扁平的 placements 清單
                placements.append({
                    "part_id": it["id"], "part_label": it["name"], "sheet_index": si,
                    "x": round(m["x"], 2), "y": round(m["y"], 2),
                    "placed_length": round(m["w"], 2), "placed_width": round(m["h"], 2),
                    "rotated": it["rotated"],
                })
            strips_out.append({
                "y": round(st["y"], 2), "thickness": round(st["h"], 2),
                "items": items_out,
            })

        for r in rems:
            rec = {
                "sheet_index": si,
                "x": round(r["x"], 2), "y": round(r["y"], 2),
                # w_mm/h_mm 是真實板材座標的寬高，畫排版圖直接用這兩個；
                # length_mm/width_mm 是長短邊（給人看的尺寸標示），兩者不可混用。
                "w_mm": round(r["w"], 2), "h_mm": round(r["h"], 2),
                "length_mm": round(r["long"], 2), "width_mm": round(r["short"], 2),
                "area_mm2": round(r["area"], 2), "area_cai": round(r["cai"], 4),
                "grade": r["grade"], "band": r["band"], "usable": r["usable"],
                "source": r["from"],
            }
            all_remnants.append(rec)
            if r["band"] and r["usable"]:
                band_remnants.append(rec)

        sheets_out.append({
            "index": si,
            "signature": _sheet_signature(sh),
            "strips": strips_out,
            "cuts": [{"seq": c["n"], "phase": c["phase"], "direction": c["dir"],
                      "position_mm": c["pos"], "from_mm": c["from"], "to_mm": c["to"],
                      "length_mm": c["len"], "note": c["note"]} for c in cuts],
            "remnants": [r for r in all_remnants if r["sheet_index"] == si],
            "utilization_rate": round(sheet_area_used / (sheet_l * sheet_w), 6),
            "items_count": sum(len(s["items"]) for s in strips_out),
            "strips_count": len(strips_out),
            "cuts_count": len(cuts),
        })

    unplaced = [{"label": u["name"], "length": u["l"], "width": u["w"],
                 "reason": u.get("why", "")} for u in res["unplaced"]]

    sheets_used = res["sheetsUsed"]
    total_sheet_area = sheets_used * sheet_l * sheet_w
    waste = round(total_sheet_area - res["area"], 2) if sheets_used else 0.0

    return {
        "engine": ENGINE_VERSION,
        "axis": res["axis"],
        "axis_label": "縱切（沿短邊開條）" if res["axis"] == "W" else "橫切（沿長邊開條）",
        "strategy": res["strategy"],
        "sheet_length_mm": sheet_l,
        "sheet_width_mm": sheet_w,
        "kerf_mm": kerf,
        "trim_mm": trim,
        "min_remnant_mm": min_rem,
        "sheets_used": sheets_used,
        # 利用率＝實際放上板的面積 ÷（用板數 × 板面積），與 v2.1 的定義一致
        "utilization_rate": round(res["util"], 6),
        "placed_count": res["placed"],
        "requested_count": requested,
        "placed_area_mm2": round(res["area"], 2),
        "placed_area_cai": round(res["area"] / CAI, 4),
        "waste_area_mm2": waste,
        "total_cuts": total_cuts,
        "band_remnant_count": len(band_remnants),
        "band_remnants": band_remnants,
        "scrap_count": res["scraps"],
        "unplaced": unplaced,
        "placements": placements,
        "remnants": all_remnants,
        "sheets": sheets_out,
    }


def compare_presets(parts: Iterable[Any], kerf_mm, trim_mm=0,
                    rem_pref: str = "any", min_remnant_mm=50) -> dict:
    """
    用開條引擎跑遍 9 種板型，挑出材料成本最低的。

    ⚠ **這裡刻意偏離 `cutplan.html` 的 `compare()`。**

    參考版的挑選邏輯是「先取板數最少者，同板數時比整條剩料總才數」
    （`sort((a,b)=> b.bandCai - a.bandCai || b.util - a.util)`）。
    實測 6 種尺寸那組零件時，它會推薦 M 板（3095×1585）為「最省」——
    1 張、54.51 才；但 S 板同樣 1 張，只要 27.98 才。**材料成本差了將近一倍。**

    這與 `cutplan.html` 自己的註腳互相矛盾，那句話是：
    「總才數＝張數 × 單張才數，是實際要買的材料量，比利用率更能反映成本」。
    參考版寫了這句，卻沒有拿總才數來排序。

    因此本實作改以「總才數」為第一排序鍵——這才是工廠真正付出去的錢。
    板數、整條剩料、利用率依序作為同分時的取捨。
    **`cutplan.html` 也應該做同樣的修正**，否則兩邊的「最省」推薦會不一致。
    """
    pieces = _to_pieces(parts)
    requested = sum(p["qty"] for p in pieces)
    items = []

    for preset in SHEET_PRESETS:
        r = run_nesting(parts, preset["length_mm"], preset["width_mm"], kerf_mm,
                        trim_mm, rem_pref, min_remnant_mm)
        if "error" in r or r["placed_count"] < requested:
            items.append({
                "name": preset["name"],
                "sheet_length": float(preset["length_mm"]),
                "sheet_width": float(preset["width_mm"]),
                "sheets_used": None, "utilization_rate": 0.0,
                "total_cai": None, "band_remnant_cai": 0.0,
                "unplaced_count": requested - (0 if "error" in r else r["placed_count"]),
                "impossible": True,
            })
            continue
        band_cai = sum(b["area_cai"] for b in r["band_remnants"])
        items.append({
            "name": preset["name"],
            "sheet_length": float(preset["length_mm"]),
            "sheet_width": float(preset["width_mm"]),
            "sheets_used": r["sheets_used"],
            "utilization_rate": r["utilization_rate"],
            "total_cai": round(r["sheets_used"] * preset["length_mm"] * preset["width_mm"] / CAI, 2),
            "band_remnant_cai": round(band_cai, 4),
            "total_cuts": r["total_cuts"],
            "unplaced_count": 0,
            "impossible": False,
        })

    ok = [i for i in items if not i["impossible"]]
    best = None
    if ok:
        best = sorted(ok, key=lambda i: (
            i["total_cai"],            # 1. 實際要買的材料量（才）——這是錢
            i["sheets_used"],          # 2. 張數（搬運與換板的工）
            -i["band_remnant_cai"],    # 3. 整條剩料多者勝
            -i["utilization_rate"],    # 4. 利用率高者勝
        ))[0]

    return {
        "engine": ENGINE_VERSION,
        "items": items,
        "best_preset": best["name"] if best else None,
        "best_sheets_used": best["sheets_used"] if best else None,
        "best_utilization_rate": best["utilization_rate"] if best else None,
        "best_total_cai": best["total_cai"] if best else None,
    }
