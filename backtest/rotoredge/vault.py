"""LIVE-ONLY venue-allocation overlay. NOT backtested (venue APYs have no free history).

Input:
  exposure : float in [0,1]  -- the engine's daily gross exposure for FXRP (from Engine._gross)
  regime_on: bool            -- master risk-on/off (BTC vs MA)
  apys     : {venue: apy_fraction}  -- LIVE APYs (Upshift via FDC Web2Json; Firelight on-chain-derived)
  cfg      : {max_venue_weight: float}
Output (all fractions of the whole book, summing to 1.0):
  {"fxrp_exposure": float, "venue_allocation": {"firelight": ., "upshift": ., "idle": .}}
"""
from __future__ import annotations


def allocate(exposure: float, regime_on: bool, apys: dict, cfg: dict) -> dict:
    exposure = max(0.0, min(1.0, float(exposure)))
    venues = ["firelight", "upshift"]
    if not regime_on or exposure <= 0.0:
        return {"fxrp_exposure": 0.0,
                "venue_allocation": {"firelight": 0.0, "upshift": 0.0, "idle": 1.0}}

    cap = float(cfg.get("max_venue_weight", 0.8))
    pos = {v: max(0.0, float(apys.get(v, 0.0))) for v in venues}
    total = sum(pos.values())
    if total <= 0.0:
        split = {v: exposure / len(venues) for v in venues}
    else:
        split = {v: exposure * (pos[v] / total) for v in venues}

    # per-venue cap (as a fraction of the whole book); overflow parks idle
    overflow = 0.0
    for v in venues:
        if split[v] > cap:
            overflow += split[v] - cap
            split[v] = cap
    idle = (1.0 - exposure) + overflow
    return {"fxrp_exposure": exposure,
            "venue_allocation": {"firelight": split["firelight"], "upshift": split["upshift"], "idle": idle}}
