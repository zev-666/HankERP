from typing import Dict, List

# 壓克力每才成本 (1才=30cm×30cm=900cm²=90,000mm²)
# 格式：(顏色, 厚度mm) -> TWD/才
ACRYLIC_PRICE_PER_CAI: Dict = {
    ("transparent", 2): 120, ("transparent", 3): 145,
    ("transparent", 5): 185, ("transparent", 8): 280, ("transparent", 10): 360,
    ("white", 2): 130, ("white", 3): 158, ("white", 5): 200, ("white", 8): 300,
    ("black", 3): 160, ("black", 5): 210,
    ("frosted", 3): 170, ("frosted", 5): 230,
    ("colored", 3): 175, ("colored", 5): 240,
    ("mirror", 3): 220, ("mirror", 5): 310,
}

# 加工成本 TWD/分鐘
PROCESSING_COST_PER_MIN: Dict = {
    "cnc_cut": 8,
    "laser_cut": 10,
    "laser_engrave": 12,
    "drilling": 5,
    "polishing": 6,
    "assembly": 4,
    "painting": 15,
    "quality_check": 2,
    "packaging": 2,
}

CAI_MM2 = 300.0 * 300.0  # 90,000 mm²


class QuoteEngine:
    """
    Phase 1 規則引擎報價
    輸入BOM零件清單 + 工序 → 輸出含毛利的報價
    """

    def __init__(self, overhead_rate: float = 0.25, target_margin: float = 0.35):
        self.overhead_rate = overhead_rate    # 管銷費用率
        self.target_margin = target_margin   # 目標毛利率

    def calc_acrylic_cost(self, bom_items: List[Dict]) -> float:
        total = 0.0
        for item in bom_items:
            if item.get("type") != "acrylic":
                continue
            area_mm2 = item["length_mm"] * item["width_mm"] * item.get("quantity", 1)
            area_cai = area_mm2 / CAI_MM2 * 1.10   # +10% 損耗
            color = item.get("color", "transparent")
            thickness = int(item["thickness_mm"])
            price = ACRYLIC_PRICE_PER_CAI.get((color, thickness), 200)
            total += area_cai * price
        return round(total, 2)

    def calc_processing_cost(self, operations: List[Dict]) -> float:
        return round(sum(
            PROCESSING_COST_PER_MIN.get(op["type"], 5)
            * op["estimated_minutes"]
            * op.get("quantity", 1)
            for op in operations
        ), 2)

    def generate_quote(self, bom_items: List[Dict], operations: List[Dict], qty: int = 1) -> Dict:
        unit_mat = self.calc_acrylic_cost(bom_items)
        unit_proc = self.calc_processing_cost(operations)

        mat = unit_mat * qty
        proc = unit_proc * qty
        overhead = (mat + proc) * self.overhead_rate
        subtotal = mat + proc + overhead
        final = subtotal / (1 - self.target_margin)

        return {
            "quantity": qty,
            "unit_price_twd": round(final / qty, 0),
            "total_price_twd": round(final, 0),
            "breakdown": {
                "material_cost_twd": round(mat, 0),
                "processing_cost_twd": round(proc, 0),
                "overhead_cost_twd": round(overhead, 0),
                "subtotal_twd": round(subtotal, 0),
            },
            "margin_pct": f"{self.target_margin * 100:.0f}%",
            "note": "此為AI規則引擎初步估價，正式報價請業務審核確認"
        }
