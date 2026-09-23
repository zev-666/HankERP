"""
裁切最佳化引擎 — pytest 單元測試
針對 backend/app/ai/nesting_bfd.py 的 BFDNestingEngine / compare_all_presets 撰寫，
不依賴資料庫，純演算法邏輯驗證。

⚠️ 版本說明：此測試套件為 2026-08-13 針對目前 zip 版本重新撰寫並實測通過，
   取代先前文件中記載但實際未隨附於zip的「15項測試」錯誤描述。
"""
import time

import pytest

from app.ai.nesting_bfd import BFDNestingEngine, Part, compare_all_presets, SHEET_PRESETS


def _mk_parts(id_, label, length, width, quantity=1, can_rotate=True):
    return Part(id=id_, label=label, length=length, width=width,
                quantity=quantity, can_rotate=can_rotate)


# ── 基本排版邏輯 ──────────────────────────────────────────────────────────

def test_basic_single_sheet_fit():
    """500x300 x4 in 2000x1000 kerf=3 -> 應可裝入1張板"""
    engine = BFDNestingEngine(sheet_length=2000, sheet_width=1000, kerf=3)
    r = engine.nest([_mk_parts("p1", "測試件", 500, 300, quantity=4)])
    assert r["sheets_used"] == 1
    assert len(r["placements"]) == 4


def test_utilization_rate_bounds():
    """利用率必須介於0與1之間"""
    engine = BFDNestingEngine(sheet_length=2000, sheet_width=1000, kerf=3)
    r = engine.nest([_mk_parts("p1", "測試件", 600, 400, quantity=3)])
    assert 0 <= r["utilization_rate"] <= 1


def test_multiple_sheets_when_overflow():
    """零件總面積超過1張板時應自動開新板"""
    engine = BFDNestingEngine(sheet_length=1000, sheet_width=1000, kerf=3)
    r = engine.nest([_mk_parts("p1", "大件", 900, 900, quantity=3)])
    assert r["sheets_used"] == 3
    assert len(r["placements"]) == 3


def test_impossible_part_not_placed():
    """零件超出板材尺寸應不放置，不崩潰"""
    engine = BFDNestingEngine(sheet_length=2000, sheet_width=1000, kerf=3)
    r = engine.nest([_mk_parts("p1", "超大件", 3000, 100, quantity=1)])
    assert len(r["placements"]) == 0
    # v2.1：一件都沒排進去時不算用板（舊版會回報 1 張空板）
    assert r["sheets_used"] == 0
    assert r["utilization_rate"] == 0
    assert len(r["unplaced"]) == 1


def test_rotation_invariance():
    """旋轉不變性：460x160 與 160x460 在允許旋轉下應排出相同件數"""
    engine_a = BFDNestingEngine(sheet_length=1915, sheet_width=1315, kerf=3)
    engine_b = BFDNestingEngine(sheet_length=1915, sheet_width=1315, kerf=3)
    r_a = engine_a.nest([_mk_parts("p1", "件A", 460, 160, quantity=20, can_rotate=True)])
    r_b = engine_b.nest([_mk_parts("p1", "件B", 160, 460, quantity=20, can_rotate=True)])
    assert len(r_a["placements"]) == len(r_b["placements"]) == 20


def test_no_rotate_flag_respected():
    """can_rotate=False 時不應旋轉零件"""
    engine = BFDNestingEngine(sheet_length=2000, sheet_width=1000, kerf=3)
    r = engine.nest([_mk_parts("p1", "不可旋轉", 1500, 200, quantity=1, can_rotate=False)])
    if r["placements"]:
        assert r["placements"][0]["rotated"] is False


def test_kerf_zero_boundary():
    """kerf=0 邊界條件不應崩潰"""
    engine = BFDNestingEngine(sheet_length=2000, sheet_width=1000, kerf=0)
    r = engine.nest([_mk_parts("p1", "件", 500, 500, quantity=4, can_rotate=False)])
    assert r["sheets_used"] == 1
    assert len(r["placements"]) == 4


def test_no_overlap_mixed_parts():
    """混排多種零件不得重疊"""
    engine = BFDNestingEngine(sheet_length=2000, sheet_width=1000, kerf=3)
    r = engine.nest([
        _mk_parts("p1", "側板", 600, 400, quantity=5),
        _mk_parts("p2", "背板", 300, 200, quantity=10),
    ])
    placements = r["placements"]
    for i in range(len(placements)):
        for j in range(i + 1, len(placements)):
            a, b = placements[i], placements[j]
            if a["sheet_index"] != b["sheet_index"]:
                continue
            overlap_x = a["x"] < b["x"] + b["placed_length"] and a["x"] + a["placed_length"] > b["x"]
            overlap_y = a["y"] < b["y"] + b["placed_width"] and a["y"] + a["placed_width"] > b["y"]
            assert not (overlap_x and overlap_y), f"Overlap: {a} vs {b}"


def test_remnants_grade_threshold():
    """剩料須符合最小50mm門檻才會被列入"""
    engine = BFDNestingEngine(sheet_length=2000, sheet_width=1000, kerf=3)
    r = engine.nest([_mk_parts("p1", "件", 1990, 990, quantity=1)])
    for rem in r["remnants"]:
        assert rem["length_mm"] >= 50 and rem["width_mm"] >= 50


def test_performance_large_quantity():
    """500x300 x1000件效能測試，需在合理時間內完成"""
    engine = BFDNestingEngine(sheet_length=2000, sheet_width=1000, kerf=3)
    start = time.time()
    r = engine.nest([_mk_parts("p1", "件", 500, 300, quantity=1000)])
    elapsed = time.time() - start
    assert len(r["placements"]) == 1000
    assert elapsed < 10.0, f"效能測試耗時{elapsed:.2f}s，超過10s上限"


# ── compare_all_presets 板型比較功能 ──────────────────────────────────────

def test_compare_presets_returns_all_9():
    """9種板型應全部回傳結果"""
    parts = [_mk_parts("p1", "測試件", 600, 400, quantity=4)]
    result = compare_all_presets(parts, kerf=3.0)
    assert len(result["items"]) == len(SHEET_PRESETS) == 9


def test_compare_presets_finds_best():
    """應正確找出片數最少的推薦板型"""
    parts = [
        _mk_parts("p1", "側板", 600, 400, quantity=4),
        _mk_parts("p2", "背板", 300, 300, quantity=6),
    ]
    result = compare_all_presets(parts, kerf=3.0)
    assert result["best_preset"] is not None
    assert result["best_sheets_used"] >= 1
    # 驗證推薦方案確實是所有可行方案中片數最少者
    valid_items = [i for i in result["items"] if not i["impossible"]]
    min_sheets = min(i["sheets_used"] for i in valid_items)
    assert result["best_sheets_used"] == min_sheets


def test_compare_presets_marks_impossible():
    """超出所有板型尺寸的零件應標記為impossible"""
    parts = [_mk_parts("p1", "超巨大件", 5000, 5000, quantity=1)]
    result = compare_all_presets(parts, kerf=3.0)
    assert all(item["impossible"] for item in result["items"])
    assert result["best_preset"] is None


def test_compare_presets_no_nan():
    """比較結果不應包含NaN或None（除了impossible項目外）"""
    parts = [_mk_parts("p1", "測試件", 500, 300, quantity=3)]
    result = compare_all_presets(parts, kerf=3.0)
    for item in result["items"]:
        if not item["impossible"]:
            assert item["sheets_used"] is not None
            assert item["utilization_rate"] == item["utilization_rate"]  # NaN != NaN


@pytest.mark.parametrize("length,width,qty", [
    (2000, 1000, 1), (1, 1, 1), (999.9, 0.1, 1),
])
def test_edge_dimensions_do_not_crash(length, width, qty):
    """邊界尺寸（含極端值）不應導致例外"""
    engine = BFDNestingEngine(sheet_length=2000, sheet_width=1000, kerf=3)
    r = engine.nest([_mk_parts("p1", "邊界件", length, width, quantity=qty)])
    assert r is not None


# ── v2.1 利用率修正（回歸測試）─────────────────────────────────────────
# 舊版利用率分子用「需求零件總面積」，排不下時回報 100% 並污染廠長儀表板 KPI。

def test_utilization_full_sheet_part_unplaced_is_zero():
    """整板尺寸零件遇到刀縫排不下 → 利用率 0，不可回報 100%"""
    engine = BFDNestingEngine(sheet_length=2000, sheet_width=1000, kerf=3)
    r = engine.nest([_mk_parts("p1", "整板件", 2000, 1000, quantity=1)])
    assert r["placed_count"] == 0
    assert r["requested_count"] == 1
    assert r["utilization_rate"] == 0
    assert r["sheets_used"] == 0
    assert r["waste_area_mm2"] == 0
    assert r["unplaced"][0]["label"] == "整板件"


def test_utilization_counts_only_placed_area():
    """部分排不下時，利用率只算實際放上板的面積"""
    engine = BFDNestingEngine(sheet_length=2000, sheet_width=1000, kerf=3)
    r = engine.nest([
        _mk_parts("big", "超大件", 3000, 100, quantity=1),
        _mk_parts("ok", "正常件", 500, 300, quantity=4),
    ])
    assert r["placed_count"] == 4
    assert r["requested_count"] == 5
    assert [u["part_id"] for u in r["unplaced"]] == ["big"]
    assert r["sheets_used"] == 1
    assert r["utilization_rate"] == round(4 * 500 * 300 / (2000 * 1000), 4)  # 0.3，舊版會算成 0.45
    assert r["placed_area_mm2"] == 4 * 500 * 300
    assert r["waste_area_mm2"] == 2000 * 1000 - 4 * 500 * 300


def test_utilization_matches_placements_general():
    """一般情況：利用率 = Σ(放置面積) ÷ (板數 × 板面積)，且不超過 1"""
    engine = BFDNestingEngine(sheet_length=1915, sheet_width=1315, kerf=3)
    r = engine.nest([
        _mk_parts("a", "側板", 630, 400, quantity=4),
        _mk_parts("b", "層板", 630, 200, quantity=6),
    ])
    area = sum(p["placed_length"] * p["placed_width"] for p in r["placements"])
    expected = round(area / (r["sheets_used"] * 1915 * 1315), 4)
    assert r["utilization_rate"] == expected
    assert 0 < r["utilization_rate"] <= 1
    assert r["unplaced"] == []


def test_compare_presets_excludes_preset_with_unplaced():
    """剛好等於 S 板尺寸的零件（扣刀縫排不下）→ S 板不能被推薦"""
    parts = [_mk_parts("p1", "整板件", 1915, 1315, quantity=1)]
    result = compare_all_presets(parts, kerf=3.0)
    s_item = next(i for i in result["items"] if i["name"] == "S")
    assert s_item["impossible"] is True
    assert s_item["unplaced_count"] == 1
    assert result["best_preset"] != "S"
    best = next(i for i in result["items"] if i["name"] == result["best_preset"])
    assert best["unplaced_count"] == 0
