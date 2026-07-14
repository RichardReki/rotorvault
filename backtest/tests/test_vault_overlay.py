import pytest
from rotoredge.vault import allocate

CFG = {"max_venue_weight": 0.8}

def _sum(alloc):
    v = alloc["venue_allocation"]
    return round(v["firelight"] + v["upshift"] + v["idle"], 9)

def test_risk_off_goes_fully_idle():
    a = allocate(exposure=0.0, regime_on=False, apys={"firelight": 0.03, "upshift": 0.08}, cfg=CFG)
    assert a["fxrp_exposure"] == 0.0
    assert a["venue_allocation"]["idle"] == 1.0
    assert _sum(a) == 1.0

def test_deployed_portion_tilts_to_higher_apy():
    a = allocate(exposure=1.0, regime_on=True, apys={"firelight": 0.02, "upshift": 0.08}, cfg=CFG)
    v = a["venue_allocation"]
    assert v["upshift"] > v["firelight"] > 0.0
    assert _sum(a) == 1.0

def test_exposure_leaves_remainder_idle():
    a = allocate(exposure=0.6, regime_on=True, apys={"firelight": 0.04, "upshift": 0.04}, cfg=CFG)
    v = a["venue_allocation"]
    assert v["idle"] == pytest.approx(0.4)
    assert v["firelight"] == pytest.approx(0.3)
    assert v["upshift"] == pytest.approx(0.3)
    assert _sum(a) == 1.0

def test_per_venue_cap_overflow_to_idle():
    a = allocate(exposure=1.0, regime_on=True, apys={"firelight": 0.0, "upshift": 0.10}, cfg={"max_venue_weight": 0.7})
    v = a["venue_allocation"]
    assert v["upshift"] == pytest.approx(0.7)         # capped
    assert v["idle"] == pytest.approx(0.3)            # overflow parked idle
    assert _sum(a) == 1.0

def test_zero_apy_info_splits_equally():
    a = allocate(exposure=1.0, regime_on=True, apys={"firelight": 0.0, "upshift": 0.0}, cfg=CFG)
    v = a["venue_allocation"]
    assert v["firelight"] == pytest.approx(0.5)
    assert v["upshift"] == pytest.approx(0.5)
    assert _sum(a) == 1.0

def test_negative_cap_is_floored_no_negative_weights():
    a = allocate(exposure=1.0, regime_on=True, apys={"firelight": 0.05, "upshift": 0.05}, cfg={"max_venue_weight": -0.1})
    v = a["venue_allocation"]
    assert v["firelight"] >= 0.0 and v["upshift"] >= 0.0 and v["idle"] >= 0.0
    assert _sum(a) == 1.0

def test_both_venues_over_cap_overflow_to_idle():
    a = allocate(exposure=1.0, regime_on=True, apys={"firelight": 0.05, "upshift": 0.05}, cfg={"max_venue_weight": 0.3})
    v = a["venue_allocation"]
    assert v["firelight"] == pytest.approx(0.3)
    assert v["upshift"] == pytest.approx(0.3)
    assert v["idle"] == pytest.approx(0.4)
    assert _sum(a) == 1.0

def test_exposure_out_of_range_is_clamped():
    a_hi = allocate(exposure=1.5, regime_on=True, apys={"firelight": 0.0, "upshift": 0.0}, cfg=CFG)
    assert a_hi["fxrp_exposure"] == 1.0 and _sum(a_hi) == 1.0
    a_lo = allocate(exposure=-0.5, regime_on=True, apys={"firelight": 0.0, "upshift": 0.0}, cfg=CFG)
    assert a_lo["venue_allocation"]["idle"] == 1.0 and _sum(a_lo) == 1.0
