"""
開條裁板引擎（二階段 Guillotine）—— 由 `cutplan.html` 的 JavaScript 引擎逐函式移植。

- v2.3（2026-09-24 版）：packOnce／packByGroup／nest／cutList／remnantsOf
- v2.3.4（2026-10-15 版，Project `claude/cutplan_2026-10-15.html`）：
  刀序與剩料改照 `mxCutList()`／`mxRemnants()`，補上「修窄」刀與修窄邊料；
  `nest()` 修正沿短邊開條時不可轉件被轉 90°。
  比對用的 JS 抽取版是 `tools/cutting-calculator/engine_cli.js`。

為什麼要重寫排版核心
--------------------
舊的 `nesting_bfd.py`（Guillotine Best-Fit Decreasing）排版品質明顯不足：
同一組輸入，460×160×100 它要 9 張板（利用率 32.5%），開條引擎只要 4 張（73.1%）；
460×160×32 它要 3 張，開條引擎 1 張。根因是 `_guillotine_split()` 產生下方剩餘
空間時寬度用了零件的長而非原矩形的寬，加上「最小剩餘面積」的 best-fit 評分，
會把板切成一條條窄直條。詳見 `CUTTING_ENGINE_CURRENT_STATE.md`。

為什麼是「開條」
----------------
真實裁板機只能整刀切穿，所以版面一律是「先開條、再條內分件」。這樣排出來的
結果天生帶有刀序，可以往 Level 3（裁切順序）→ Level 6（機台可執行 Cutting Plan）推進。

移植原則
--------
**逐行對照，刻意不做「改良」。** 這支的正確性來自與 JS 版交叉比對，
任何自作主張的優化都會讓兩邊對不起來，也就失去了回歸基準。
若要改演算法，請先改 `cutplan.html` 並更新回歸案例，再同步這裡。

已知需要特別處理的語言差異：
- JS 的 `Math.round` 是「.5 進位到 +∞」，Python 的 `round()` 是 banker's rounding。
  本檔一律用 `_round1()`，不使用內建 `round()`。
- JS 的 `Array.prototype.sort` 與 Python 的 `list.sort` 都是穩定排序，
  但比較子語意不同，因此用 `cmp_to_key` 保留原本的比較函式寫法。

座標系
------
所有排版都在「pack frame」計算：x 沿條帶跑、y 是條帶疊起來的方向。
`axis` 決定 pack frame 怎麼貼回真實板材：
  axis "L" → 條帶沿板長跑（開條刀是橫切），剩料是沿長邊的整條
  axis "W" → 條帶沿板寬跑（開條刀是縱切），剩料是沿短邊的整條
"""
from __future__ import annotations

import math
from functools import cmp_to_key
from typing import Any, Iterable

# 1 才 = 300×300 mm = 90,000 mm²
CAI = 300 * 300

EPS = 1e-9

# 工廠實際使用的 9 種原板。
# ⚠ S 板 1915×1315 才是本廠的「標準板」；2000×1000 是舊文件的錯誤值。
SHEET_PRESETS: list[dict[str, Any]] = [
    {"name": "S（標準板）", "length_mm": 1915, "width_mm": 1315},
    {"name": "T", "length_mm": 1905, "width_mm": 1005},
    {"name": "B", "length_mm": 2045, "width_mm": 1045},
    {"name": "H", "length_mm": 2205, "width_mm": 1105},
    {"name": "a", "length_mm": 1855, "width_mm": 1245},
    {"name": "A2", "length_mm": 2365, "width_mm": 1415},
    {"name": "L", "length_mm": 2565, "width_mm": 1315},
    {"name": "M", "length_mm": 3095, "width_mm": 1585},
    {"name": "2000×1000", "length_mm": 2000, "width_mm": 1000},
]


def _round1(v: float) -> float:
    """等同 JS 的 `Math.round(v*10)/10`（.5 一律進位到 +∞），不是 Python 的 banker's rounding。"""
    return math.floor(v * 10 + 0.5) / 10


def _sign(v: float) -> int:
    """把 JS 比較子回傳的數值轉成 -1/0/1，供 cmp_to_key 使用。"""
    if v < 0:
        return -1
    if v > 0:
        return 1
    return 0


# ── 第一階段：把零件排進條帶 ──────────────────────────────────────────

def _pack_once(pieces, pack_l, pack_w, kerf, sort_key, orient, max_sheets, fit_mode):
    """
    單一策略的排版。對應 JS 的 `packOnce()`。

    fit_mode "existing"：只要既有條帶塞得下就塞（傳統 FFDH）
    fit_mode "waste"   ：比較「塞進既有條帶浪費的高度面積」與「另開一條的代價」，取便宜的。
                         薄件（骨仔之類）因此會自己另開一條細條帶，
                         而不是佔掉一整條的高度。
    """
    lst = [dict(p) for p in pieces]

    def _long(p):
        return max(p["l"], p["w"])

    def _short(p):
        return min(p["l"], p["w"])

    sorters = {
        "height": lambda a, b: _sign((b["h"] - a["h"]) or (b["w2"] - a["w2"])),
        "area": lambda a, b: _sign((b["l"] * b["w"] - a["l"] * a["w"]) or (b["h"] - a["h"])),
        "long": lambda a, b: _sign((_long(b) - _long(a)) or (_short(b) - _short(a))),
    }

    for p in lst:
        if not p["rot"]:
            p["h"], p["w2"], p["free"] = p["w"], p["l"], False
        elif orient == "cross":
            p["h"], p["w2"], p["free"] = _short(p), _long(p), False
        elif orient == "along":
            p["h"], p["w2"], p["free"] = _long(p), _short(p), False
        else:
            p["h"], p["w2"], p["free"] = p["w"], p["l"], True

    lst.sort(key=cmp_to_key(sorters[sort_key]))

    sheets: list[dict] = []
    unplaced: list[dict] = []

    def orientations_of(p):
        if not p["rot"]:
            ors = [{"h": p["w"], "w": p["l"], "rotated": False}]
        elif p["free"]:
            ors = [
                {"h": p["w"], "w": p["l"], "rotated": False},
                {"h": p["l"], "w": p["w"], "rotated": True},
            ]
        else:
            ors = [{"h": p["h"], "w": p["w2"], "rotated": not (p["h"] == p["w"])}]
        return [o for o in ors if o["h"] <= pack_w + EPS and o["w"] <= pack_l + EPS]

    for p in lst:
        ors = orientations_of(p)
        if not ors:
            unplaced.append({**p, "why": "尺寸超出原板"})
            continue

        best = None
        new_best = None

        # 候選 1：塞進既有條帶
        for si, sh in enumerate(sheets):
            for ti, st in enumerate(sh["strips"]):
                for o in ors:
                    if o["h"] > st["h"] + EPS:
                        continue
                    x = st["x"] + (kerf if st["items"] else 0)
                    if x + o["w"] > pack_l + EPS:
                        continue
                    if fit_mode == "waste":
                        cost = (st["h"] - o["h"]) * o["w"]          # 條帶高度用不到的那塊
                    else:
                        cost = (st["h"] - o["h"]) * 1e6 + (pack_l - x - o["w"])
                    if best is None or cost < best["cost"]:
                        best = {"cost": cost, "kind": "strip", "si": si, "ti": ti, "x": x, "o": o}

        # 候選 2：在既有板上另開一條
        for si, sh in enumerate(sheets):
            for o in ors:
                y = sh["usedH"] + (kerf if sh["strips"] else 0)
                if y + o["h"] > pack_w + EPS:
                    continue
                if fit_mode == "waste":
                    # 多一道開條刀 ＋ 新條帶暫時沒填滿的部分
                    cost = kerf * pack_l + (pack_l - o["w"]) * o["h"] * 0.5
                else:
                    cost = (pack_w - y - o["h"]) * 1e3 + (pack_l - o["w"])
                if new_best is None or cost < new_best["cost"]:
                    new_best = {"cost": cost, "kind": "newstrip", "si": si, "y": y, "o": o}

        if fit_mode == "waste":
            if new_best is not None and (best is None or new_best["cost"] < best["cost"]):
                best = new_best
        elif best is None:
            best = new_best

        if best is None:
            if max_sheets and len(sheets) >= max_sheets:
                unplaced.append({**p, "why": "板數用盡"})
                continue
            sheets.append({"strips": [], "usedH": 0})
            best = {"kind": "newstrip", "si": len(sheets) - 1, "y": 0, "o": ors[0]}

        sh = sheets[best["si"]]
        o = best["o"]
        if best["kind"] == "strip":
            st = sh["strips"][best["ti"]]
            st["items"].append({**p, "x": best["x"], "y": st["y"],
                                "w": o["w"], "h": o["h"], "rotated": o["rotated"]})
            st["x"] = best["x"] + o["w"]
        else:
            st = {"y": best["y"], "h": o["h"], "x": o["w"], "items": []}
            st["items"].append({**p, "x": 0, "y": best["y"],
                                "w": o["w"], "h": o["h"], "rotated": o["rotated"]})
            sh["strips"].append(st)
            sh["usedH"] = best["y"] + o["h"]

    return {"sheets": sheets, "unplaced": unplaced}


def _pack_by_group(pieces, pack_l, pack_w, kerf, max_sheets):
    """
    「同尺寸各開各的條」——現場師傅的做法。對應 JS 的 `packByGroup()`。

    每一種尺寸算出一條裝幾件、要幾條，然後照順序往下疊。
    骨仔 25/50/75 就會各自得到一條 1315×25、1315×50、1315×75，
    而不是被塞進 630 高的條帶裡浪費掉高度。
    """
    groups: dict[str, dict] = {}
    for p in pieces:
        key = f"{p['l']}x{p['w']}x{p['rot']}"
        if key not in groups:
            groups[key] = {"sample": p, "items": []}
        groups[key]["items"].append(p)

    plan: list[dict] = []
    for g in groups.values():
        p, n = g["sample"], len(g["items"])
        cands: list[dict] = []

        def try_orient(h, w, rotated):
            if h > pack_w + EPS or w > pack_l + EPS:
                return
            per_strip = math.floor((pack_l + kerf) / (w + kerf))
            if per_strip < 1:
                return
            strips = math.ceil(n / per_strip)
            cands.append({"h": h, "w": w, "rotated": rotated, "perStrip": per_strip,
                          "strips": strips, "thickness": strips * (h + kerf)})

        try_orient(p["w"], p["l"], False)
        if p["rot"] and p["l"] != p["w"]:
            try_orient(p["l"], p["w"], True)

        if not cands:
            plan.append({"g": g, "impossible": True})
            continue
        cands.sort(key=cmp_to_key(
            lambda a, b: _sign((a["thickness"] - b["thickness"]) or (a["strips"] - b["strips"]))
        ))
        plan.append({"g": g, "impossible": False, **cands[0]})

    # 厚的先開條，薄的往後排（骨仔自然排在最後）
    plan.sort(key=cmp_to_key(lambda a, b: _sign((b.get("h") or 0) - (a.get("h") or 0))))

    sheets: list[dict] = []
    unplaced: list[dict] = []
    for item in plan:
        if item["impossible"]:
            for p in item["g"]["items"]:
                unplaced.append({**p, "why": "尺寸超出原板"})
            continue
        left = list(item["g"]["items"])
        while left:
            take, left = left[:item["perStrip"]], left[item["perStrip"]:]
            sh = next((s for s in sheets
                       if s["usedH"] + (kerf if s["strips"] else 0) + item["h"] <= pack_w + EPS),
                      None)
            if sh is None:
                if max_sheets and len(sheets) >= max_sheets:
                    for p in take:
                        unplaced.append({**p, "why": "板數用盡"})
                    continue
                sh = {"strips": [], "usedH": 0}
                sheets.append(sh)
            y = sh["usedH"] + (kerf if sh["strips"] else 0)
            st = {"y": y, "h": item["h"], "x": 0, "items": []}
            for i, p in enumerate(take):
                x = 0 if i == 0 else st["x"] + kerf
                st["items"].append({**p, "x": x, "y": y, "w": item["w"],
                                    "h": item["h"], "rotated": item["rotated"]})
                st["x"] = x + item["w"]
            sh["strips"].append(st)
            sh["usedH"] = y + item["h"]

    return {"sheets": sheets, "unplaced": unplaced}


# ── pack frame → 真實板材座標 ────────────────────────────────────────

def map_rect(res: dict, x: float, y: float, w: float, h: float) -> dict:
    t = res["trim"]
    if res["axis"] == "L":
        return {"x": t + x, "y": t + y, "w": w, "h": h}
    return {"x": t + y, "y": t + x, "w": h, "h": w}


# ── 剩料 ─────────────────────────────────────────────────────────────

def _js_num(v: float) -> str:
    """數字轉字串，跟 JS 的樣板字串一樣：整數不帶 `.0`（JS 印 400，Python 的 f-string 會印 400.0）。"""
    v = float(v)
    return str(int(v)) if v.is_integer() else repr(v)


def _strips_sorted(sheet: dict) -> list[dict]:
    """條帶依 y、條內零件依 x 排好（等同 cutplan 的 `oldToResult()`）。"""
    return [{**st, "items": sorted(st["items"], key=lambda it: it["x"])}
            for st in sorted(sheet["strips"], key=lambda s: s["y"])]


def remnants_of(sheet: dict, res: dict, min_rem: float) -> list[dict]:
    """
    算一張板的剩料，回傳真實板材座標（移植自 cutplan 10-15 版 `mxRemnants()`）。

    來源有三種，順序與 JS 相同：每一條先列條尾料、再列該條的修窄邊料，最後是整條剩料。
    - 條尾料：條帶最後一件之後剩下的長度
    - 修窄邊料（v2.3.4 新增）：同一條裡比條寬窄的零件，修窄之後切下來的那塊
    - 整條剩料（`band=True`）：貫穿整板，邊是直的，可以直接上架再用
    等級：A ≥ 300×300（一才以上）、B ≥ 150×150、C 其餘。未達 `min_rem` 的零星料不列出（整條除外）。
    """
    pack_l, pack_w, kerf = res["packL"], res["packW"], res["kerf"]
    raw: list[dict] = []
    strips = _strips_sorted(sheet)
    for i, st in enumerate(strips):
        w = pack_l - st["x"] - kerf
        if w > 0.5:
            raw.append({"x": st["x"] + kerf, "y": st["y"], "w": w, "h": st["h"],
                        "from": f"第 {i + 1} 條尾料", "band": False})
        for it in st["items"]:
            hh = st["h"] - it["h"] - kerf
            if hh > 0.5:
                raw.append({"x": it["x"], "y": it["y"] + it["h"] + kerf, "w": it["w"], "h": hh,
                            "from": f"第 {i + 1} 條修窄邊料", "band": False})
    rest = pack_w - sheet["usedH"] - (kerf if strips else 0)
    if rest > 0.5:
        raw.append({"x": 0, "y": sheet["usedH"] + kerf, "w": pack_l, "h": rest,
                    "from": "整條・沿短邊" if res["axis"] == "W" else "整條・沿長邊",
                    "band": True})

    out: list[dict] = []
    for r in raw:
        m = map_rect(res, r["x"], r["y"], r["w"], r["h"])
        a = r["w"] * r["h"]
        dim_a, dim_b = max(r["w"], r["h"]), min(r["w"], r["h"])
        rec = {**m, "long": dim_a, "short": dim_b, "area": a, "cai": a / CAI,
               "from": r["from"], "band": r["band"],
               "usable": dim_b >= min_rem and dim_a >= min_rem,
               "grade": "A" if a >= 300 * 300 else ("B" if a >= 150 * 150 else "C")}
        if rec["usable"] or rec["band"]:
            out.append(rec)
    return out


# ── 裁切順序（Level 3）──────────────────────────────────────────────

def cut_list(sheet: dict, res: dict) -> list[dict]:
    """
    照裁板機的實際動作產生刀序（移植自 cutplan 10-15 版 `mxCutList()`）：
    修邊 → 開條 → 條內分件 → **修窄**。

    修窄（v2.3.4 新增）：同一條裡比條寬窄的零件，分件後還停在條寬，要再沿條帶方向下一刀
    修到自己的寬度。v2.3 漏了這一段，照刀序施工這些零件尺寸會不對。

    `pos` 是基準位置（真實板材座標），`from`/`to` 是這一刀的起訖。
    最後一刀若切完只剩不到一個刀縫，就不下那一刀（切不出東西）。
    """
    pack_l, pack_w = res["packL"], res["packW"]
    trim, kerf, axis = res["trim"], res["kerf"], res["axis"]
    tail = kerf + 0.5
    cuts: list[dict] = []
    n = 0

    def emit(phase, kind, pos, a, b, note):
        nonlocal n
        n += 1
        # kind "rip" = pack 的 y=const 線；"cross" = pack 的 x=const 線
        is_rip_row_in_sheet = (axis == "L") == (kind == "rip")
        cuts.append({"n": n, "phase": phase, "dir": "橫切" if is_rip_row_in_sheet else "縱切",
                     "kind": kind, "pos": _round1(trim + pos),
                     "from": _round1(trim + a), "to": _round1(trim + b),
                     "len": _round1(b - a), "note": note})

    if trim > 0:
        n += 1
        cuts.append({"n": n, "phase": "修邊", "dir": "橫切", "kind": "trim",
                     "pos": _round1(trim), "from": 0, "to": _round1(res["sheetL"]),
                     "len": _round1(res["sheetL"]), "note": "修下緣基準邊"})
        n += 1
        cuts.append({"n": n, "phase": "修邊", "dir": "縱切", "kind": "trim",
                     "pos": _round1(trim), "from": 0, "to": _round1(res["sheetW"]),
                     "len": _round1(res["sheetW"]), "note": "修左緣基準邊"})

    strips = _strips_sorted(sheet)
    # 第一階段：開條
    for i, st in enumerate(strips):
        edge = st["y"] + st["h"]
        if i < len(strips) - 1 or pack_w - edge > tail:
            emit("開條", "rip", edge, 0, pack_l,
                 f"分出第 {i + 1} 條（條寬 {_js_num(_round1(st['h']))} mm）")
    # 第二階段：條內分件
    for i, st in enumerate(strips):
        items = st["items"]
        for j, it in enumerate(items):
            edge = it["x"] + it["w"]
            if j < len(items) - 1 or pack_l - edge > tail:
                emit("分件", "cross", edge, st["y"], st["y"] + st["h"],
                     f"第 {i + 1} 條・切在 {_js_num(_round1(it['w']))}")
    # 第三階段：修窄（比條寬窄的零件，沿條帶方向再一刀）
    for i, st in enumerate(strips):
        for it in st["items"]:
            if st["h"] - it["h"] > 0.5:
                emit("修窄", "rip", st["y"] + it["h"], it["x"], it["x"] + it["w"],
                     f"第 {i + 1} 條・{it['name']} 修到 {_js_num(_round1(it['h']))}")
    return cuts


# ── 主流程 ───────────────────────────────────────────────────────────

def nest(parts: Iterable[dict], sheet_l: float, sheet_w: float, kerf: float = 3,
         trim: float = 0, max_sheets: int = 0, rem_pref: str = "any",
         min_rem: float = 50) -> dict:
    """
    跑遍所有策略組合取最優：2 個開條方向 × 3 種排序 × 3 種擺向 × 3 種填法。

    `parts` 每一項需要 id / name / l / w / qty / rot。
    `rem_pref`："any"（兩個方向都試）／"strip"（強制沿短邊開條）／"long"（強制沿長邊）。
    `max_sheets` > 0 代表「我有固定張數，算最多裁幾件」。

    回傳 `error` 鍵代表輸入不合法。
    """
    if not (isinstance(min_rem, (int, float)) and math.isfinite(min_rem)):
        min_rem = 50
    u_l, u_w = sheet_l - 2 * trim, sheet_w - 2 * trim
    if u_l <= 0 or u_w <= 0:
        return {"error": "修邊量太大，沒有可用區域"}

    pieces: list[dict] = []
    for p in parts:
        for _ in range(int(p["qty"])):
            pieces.append({"id": p["id"], "name": p["name"], "l": p["l"],
                           "w": p["w"], "rot": p["rot"]})
    if not pieces:
        return {"error": "沒有有效零件"}

    wanted = ["W"] if rem_pref == "strip" else (["L"] if rem_pref == "long" else ["L", "W"])
    other = ["L"] if rem_pref == "strip" else (["W"] if rem_pref == "long" else [])

    def solve(axes):
        best = None
        for axis in axes:
            pack_l = u_l if axis == "L" else u_w
            pack_w = u_w if axis == "L" else u_l
            # v2.3.4（cutplan 10-15 版 nest() 的 piecesIn 修正）：沿短邊開條（axis W）時
            # pack frame 與板材轉了 90°，不可轉的零件要先把長寬對調，貼回板材時「長」才會
            # 沿板長邊。v2.3 少了這一步，不可轉件在 axis W 會被轉 90°。
            ax_pieces = pieces if axis == "L" else [
                p if p["rot"] else {**p, "l": p["w"], "w": p["l"]} for p in pieces]
            for sort_key in ("height", "long", "area"):
                for orient in ("cross", "along", "free"):
                    for fit_mode in ("waste", "existing", "group"):
                        if fit_mode == "group":
                            # group 排法與 sortKey／orient 無關，只跑一次避免重複計算
                            if not (sort_key == "height" and orient == "cross"):
                                continue
                            r = _pack_by_group(ax_pieces, pack_l, pack_w, kerf, max_sheets)
                        else:
                            r = _pack_once(ax_pieces, pack_l, pack_w, kerf,
                                           sort_key, orient, max_sheets, fit_mode)

                        placed = sum(len(st["items"]) for sh in r["sheets"] for st in sh["strips"])
                        area = sum(it["w"] * it["h"] for sh in r["sheets"]
                                   for st in sh["strips"] for it in st["items"])
                        n_sheets = len(r["sheets"])
                        cand = {**r, "axis": axis, "packL": pack_l, "packW": pack_w,
                                "trim": trim, "kerf": kerf, "sheetL": sheet_l, "sheetW": sheet_w,
                                "placed": placed, "area": area, "sheetsUsed": n_sheets,
                                "util": (area / (n_sheets * sheet_l * sheet_w)) if n_sheets else 0,
                                "strategy": f"{axis}/{sort_key}/{orient}/{fit_mode}"}

                        # 剩料品質
                        #   scraps   = 「可回收但零散」的條尾數量 → 越少越好
                        #   bandArea = 貫穿整板的整條剩料面積 → 越大越好
                        #   細到用不上的碎屑（< min_rem）不列入任何一邊
                        band_area = 0.0
                        scraps = 0
                        cut_count = 0
                        for si, sh in enumerate(r["sheets"]):
                            strips_n = len(sh["strips"])
                            rest_w = pack_w - sh["usedH"] - (kerf if strips_n else 0)
                            # 最後一張板的空白是「還沒用到的板」，不是刻意留下的整條剩料，
                            # 不列入評分，否則演算法會被「最後一張半空的板」騙走。
                            is_tail = len(r["sheets"]) > 1 and si == len(r["sheets"]) - 1
                            if not is_tail and rest_w >= min_rem and pack_l >= min_rem:
                                band_area += rest_w * pack_l
                            # 評分刀數：開條＋分件，跟 cut_list() 前兩階段同一套判斷
                            # （2026-09-23 發現的落差：22 vs 23，09-24 修正）。
                            # ⚠ 不含 v2.3.4 加進 cut_list() 的「修窄」刀——cutplan 10-15 版的
                            # nest() 評分也不算，照規格移植。修窄刀只在利用率、整條剩料都打平時
                            # 才可能影響選擇；v2.4 移植 mxOptimize() 後評分會改用含修窄的刀數。
                            if trim > 0:
                                cut_count += 2
                            for i, st in enumerate(sh["strips"]):
                                strip_rest = pack_w - (st["y"] + st["h"])
                                if i != strips_n - 1 or strip_rest > kerf + 0.5:
                                    cut_count += 1                      # 開條刀
                                items_n = len(st["items"])
                                for j, it in enumerate(st["items"]):
                                    item_rest = pack_l - (it["x"] + it["w"])
                                    if j != items_n - 1 or item_rest > kerf + 0.5:
                                        cut_count += 1                  # 分件刀
                                tail = pack_l - st["x"] - (kerf if st["items"] else 0)
                                if tail >= min_rem and st["h"] >= min_rem:
                                    scraps += 1
                        cand["bandArea"] = band_area
                        cand["scraps"] = scraps
                        cand["cutCount"] = cut_count
                        cand["byGroup"] = fit_mode == "group"

                        # 取捨順序（使用者 2026-09-23 確認）：
                        #   0. 排入件數多、板數少（硬條件）
                        #   1. 利用率高
                        #   2. 整條剩料大
                        #   3. 刀數少
                        #   4. 零星碎料少
                        if best is None:
                            best = cand
                            continue
                        if cand["placed"] != best["placed"]:
                            if cand["placed"] > best["placed"]:
                                best = cand
                            continue
                        if cand["sheetsUsed"] != best["sheetsUsed"]:
                            if cand["sheetsUsed"] < best["sheetsUsed"]:
                                best = cand
                            continue
                        if abs(cand["util"] - best["util"]) > 1e-9:
                            if cand["util"] > best["util"]:
                                best = cand
                            continue
                        if abs(cand["bandArea"] - best["bandArea"]) > 1:
                            if cand["bandArea"] > best["bandArea"]:
                                best = cand
                            continue
                        if cand["cutCount"] != best["cutCount"]:
                            if cand["cutCount"] < best["cutCount"]:
                                best = cand
                            continue
                        if cand["scraps"] < best["scraps"]:
                            best = cand
        return best

    best = solve(wanted)
    if best and other:
        alt = solve(other)
        if alt:
            if alt["placed"] > best["placed"]:
                # 指定的開條方向根本排不下（例如不可旋轉的長件），自動改用另一個方向
                forced_from = wanted[0]
                prev_placed = best["placed"]
                best = alt
                best["forced"] = {"from": forced_from,
                                  "lost": alt["placed"] - (prev_placed - alt["placed"])}
                best["forcedFrom"] = forced_from
            elif (alt["placed"] == best["placed"] and alt["placed"] > 0
                    and alt["sheetsUsed"] < best["sheetsUsed"]):
                best["alt"] = alt   # 排得一樣多但比較省板：尊重選擇，但要講出來
    return best
