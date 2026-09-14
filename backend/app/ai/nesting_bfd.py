from dataclasses import dataclass, field
from typing import List, Optional, Tuple
import copy

@dataclass
class Part:
    id: str
    label: str
    length: float
    width: float
    quantity: int = 1
    can_rotate: bool = True

@dataclass
class Sheet:
    length: float
    width: float
    free_rects: list = field(default_factory=list)

    def __post_init__(self):
        if not self.free_rects:
            self.free_rects = [(0.0, 0.0, self.length, self.width)]

class BFDNestingEngine:
    """
    Guillotine Best-Fit Decreasing 2D Nesting
    壓克力工廠排版核心引擎

    特性：
    - 支援零件旋轉（can_rotate=True）
    - 自動計算利用率與剩料
    - 刀縫補償（kerf_mm）
    """

    def __init__(self, sheet_length: float = 2000, sheet_width: float = 1000, kerf: float = 3):
        self.sheet_length = sheet_length
        self.sheet_width = sheet_width
        self.kerf = kerf

    def nest(self, parts: List[Part]) -> dict:
        # 展開數量
        expanded = []
        for p in parts:
            for _ in range(p.quantity):
                cp = copy.deepcopy(p)
                cp.quantity = 1
                expanded.append(cp)

        # 大件優先排
        expanded.sort(key=lambda p: p.length * p.width, reverse=True)

        sheets: List[Sheet] = [Sheet(self.sheet_length, self.sheet_width)]
        placements = []

        for part in expanded:
            placed = False
            for i, sheet in enumerate(sheets):
                result = self._try_place(sheet, part)
                if result:
                    x, y, rotated = result
                    pl = part.width if rotated else part.length
                    pw = part.length if rotated else part.width
                    placements.append({
                        "part_id": part.id, "label": part.label,
                        "sheet_index": i, "x": round(x, 1), "y": round(y, 1),
                        "placed_length": pl, "placed_width": pw, "rotated": rotated
                    })
                    placed = True
                    break

            if not placed:
                new_sheet = Sheet(self.sheet_length, self.sheet_width)
                result = self._try_place(new_sheet, part)
                if result:
                    x, y, rotated = result
                    pl = part.width if rotated else part.length
                    pw = part.length if rotated else part.width
                    placements.append({
                        "part_id": part.id, "label": part.label,
                        "sheet_index": len(sheets), "x": round(x, 1), "y": round(y, 1),
                        "placed_length": pl, "placed_width": pw, "rotated": rotated
                    })
                    sheets.append(new_sheet)

        total_part_area = sum(p.length * p.width for p in expanded)
        total_sheet_area = len(sheets) * self.sheet_length * self.sheet_width
        utilization = total_part_area / total_sheet_area if total_sheet_area > 0 else 0

        return {
            "sheets_used": len(sheets),
            "utilization_rate": round(utilization, 4),
            "placements": placements,
            "waste_area_mm2": round(total_sheet_area - total_part_area, 2),
            "remnants": self._extract_remnants(sheets),
        }

    def _try_place(self, sheet: Sheet, part: Part) -> Optional[Tuple]:
        orientations = [(part.length, part.width, False)]
        if part.can_rotate and part.length != part.width:
            orientations.append((part.width, part.length, True))

        best = None
        best_waste = float("inf")

        for pl, pw, rotated in orientations:
            for rect in sheet.free_rects:
                rx, ry, rw, rh = rect
                if pl + self.kerf <= rw and pw + self.kerf <= rh:
                    waste = rw * rh - pl * pw
                    if waste < best_waste:
                        best_waste = waste
                        best = (rx, ry, rotated, pl, pw, rect)

        if best:
            x, y, rotated, pl, pw, rect = best
            self._guillotine_split(sheet, rect, x, y, pl, pw)
            return (x, y, rotated)
        return None

    def _guillotine_split(self, sheet: Sheet, rect, x, y, pl, pw):
        rx, ry, rw, rh = rect
        sheet.free_rects.remove(rect)
        # 右側空間
        if rw - pl - self.kerf > 20:
            sheet.free_rects.append((x + pl + self.kerf, ry, rw - pl - self.kerf, rh))
        # 下方空間
        if rh - pw - self.kerf > 20:
            sheet.free_rects.append((rx, y + pw + self.kerf, pl, rh - pw - self.kerf))

    def _extract_remnants(self, sheets: List[Sheet]) -> list:
        remnants = []
        for i, sheet in enumerate(sheets):
            for rx, ry, rw, rh in sheet.free_rects:
                if rw >= 50 and rh >= 50:  # 最小5cm可回收
                    remnants.append({
                        "sheet_index": i, "x": round(rx, 1), "y": round(ry, 1),
                        "length_mm": round(rw, 1), "width_mm": round(rh, 1),
                        "area_mm2": round(rw * rh),
                        "area_cai": round(rw * rh / 90000, 3)
                    })
        return remnants


# ── 板型預設（工廠實際使用的9種原板規格）─────────────────────────
SHEET_PRESETS: List[dict] = [
    {"name": "標準板", "length": 2000, "width": 1000},
    {"name": "A2",    "length": 2365, "width": 1415},
    {"name": "T",     "length": 1905, "width": 1005},
    {"name": "B",     "length": 2045, "width": 1045},
    {"name": "H",     "length": 2205, "width": 1105},
    {"name": "a",     "length": 1855, "width": 1245},
    {"name": "S",     "length": 1915, "width": 1315},
    {"name": "L",     "length": 2565, "width": 1315},
    {"name": "M",     "length": 3095, "width": 1585},
]


def compare_all_presets(parts: List[Part], kerf: float = 3.0) -> dict:
    """
    對 9 種標準板型各跑一次 BFDNestingEngine，比較所需片數與利用率，
    回傳最省片數的推薦方案（片數相同時取利用率較高者）。
    """
    results = []
    for preset in SHEET_PRESETS:
        sl, sw = float(preset["length"]), float(preset["width"])

        # 檢查是否有零件在任何方向都超出此板型
        impossible = any(
            (p.length > sl and p.width > sw) or (p.width > sl and p.length > sw)
            for p in parts
        )
        if impossible:
            results.append({
                "name": preset["name"], "sheet_length": sl, "sheet_width": sw,
                "sheets_used": None, "utilization_rate": 0.0, "impossible": True,
            })
            continue

        engine = BFDNestingEngine(sheet_length=sl, sheet_width=sw, kerf=kerf)
        r = engine.nest(parts)
        results.append({
            "name": preset["name"], "sheet_length": sl, "sheet_width": sw,
            "sheets_used": r["sheets_used"], "utilization_rate": r["utilization_rate"],
            "impossible": False,
        })

    valid = [r for r in results if not r["impossible"]]
    best = None
    if valid:
        min_sheets = min(r["sheets_used"] for r in valid)
        candidates = [r for r in valid if r["sheets_used"] == min_sheets]
        best = max(candidates, key=lambda r: r["utilization_rate"])

    return {
        "items": results,
        "best_preset": best["name"] if best else None,
        "best_sheets_used": best["sheets_used"] if best else None,
        "best_utilization_rate": best["utilization_rate"] if best else None,
    }
