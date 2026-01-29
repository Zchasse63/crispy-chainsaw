#!/usr/bin/env python3
"""
Unified Freight Calculator for Fleetwood Pricing

This is the SINGLE SOURCE OF TRUTH for all freight calculations.
Uses calibrated origin-specific multipliers (Jan 2026).

DO NOT use the old 2.75x generic multiplier - it was 37-176% too high.
"""

import json
import os
from datetime import date, datetime
from typing import Optional, Tuple, Dict, Any

# Load freight modifiers from the unified reference file
SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REFERENCES_DIR = os.path.join(SKILL_DIR, "references")

with open(os.path.join(REFERENCES_DIR, "freight-modifiers.json")) as f:
    MODIFIERS = json.load(f)

ORIGIN_MULTIPLIERS = {k: v["multiplier"] for k, v in MODIFIERS["origin_multipliers"].items() if isinstance(v, dict) and "multiplier" in v}
WAREHOUSE_MULTIPLIERS = MODIFIERS["warehouse_multipliers"]
SEASON_MODIFIERS = {k: v["modifier"] for k, v in MODIFIERS["season_modifiers"].items() if isinstance(v, dict) and "modifier" in v}
MARGIN_MULTIPLIER = MODIFIERS["margin_multiplier"]
STANDARD_WEIGHT = MODIFIERS["standard_quote_weight_lbs"]


def get_season_modifier(target_date: Optional[date] = None) -> Tuple[float, str]:
    """
    Get the seasonal freight modifier based on the date.
    
    Args:
        target_date: Date to check. Defaults to today.
    
    Returns:
        Tuple of (modifier, season_type)
    """
    if target_date is None:
        target_date = date.today()
    
    month = target_date.month
    month_names = ["jan", "feb", "mar", "apr", "may", "jun",
                   "jul", "aug", "sep", "oct", "nov", "dec"]
    month_key = month_names[month - 1]
    
    modifier_data = MODIFIERS["season_modifiers"].get(month_key, {"modifier": 1.00, "type": "normal"})
    return modifier_data["modifier"], modifier_data["type"]


def get_origin_multiplier(origin: str) -> float:
    """
    Get the reefer multiplier for an origin state or warehouse.
    
    Args:
        origin: State code (e.g., "GA", "PA") or warehouse key (e.g., "GA_COLD", "A_R_T")
    
    Returns:
        Reefer multiplier (calibrated Jan 2026)
    """
    origin_upper = origin.upper().strip()
    
    # Check if it's a warehouse key first
    if origin_upper in WAREHOUSE_MULTIPLIERS:
        return WAREHOUSE_MULTIPLIERS[origin_upper]["multiplier"]
    
    # Check state codes
    if origin_upper in ORIGIN_MULTIPLIERS:
        return ORIGIN_MULTIPLIERS[origin_upper]
    
    # Handle common aliases
    aliases = {
        "AMERICUS": "GA",
        "BOYERTOWN": "PA",
        "INDIANAPOLIS": "IN",
        "GEORGIA": "GA",
        "PENNSYLVANIA": "PA",
        "INDIANA": "IN",
    }
    if origin_upper in aliases:
        return ORIGIN_MULTIPLIERS[aliases[origin_upper]]
    
    # Default to Midwest average if unknown
    print(f"Warning: Unknown origin '{origin}', using default 2.10x (Midwest)")
    return 2.10


def calculate_reefer_quote(
    dry_quote: float,
    origin: str,
    target_date: Optional[date] = None
) -> Dict[str, Any]:
    """
    Calculate refrigerated freight quote from a dry LTL quote.
    
    This uses the CALIBRATED multipliers (Jan 2026), not the old 2.75x.
    
    Args:
        dry_quote: Dry LTL quote amount in dollars
        origin: Origin state code or warehouse key
        target_date: Date for season modifier. Defaults to today.
    
    Returns:
        Dictionary with reefer quote and breakdown
    """
    origin_mod = get_origin_multiplier(origin)
    season_mod, season_type = get_season_modifier(target_date)
    
    reefer_quote = dry_quote * origin_mod * season_mod
    freight_per_lb = reefer_quote / STANDARD_WEIGHT
    
    return {
        "dry_quote": dry_quote,
        "origin": origin,
        "origin_multiplier": origin_mod,
        "season_modifier": season_mod,
        "season_type": season_type,
        "reefer_quote": round(reefer_quote, 2),
        "freight_per_lb": round(freight_per_lb, 4),
        "standard_weight_lbs": STANDARD_WEIGHT,
    }


def calculate_landed_price(
    base_cost_per_lb: float,
    freight_per_lb: float,
    margin: float = MARGIN_MULTIPLIER
) -> Dict[str, Any]:
    """
    Calculate landed price with margin.
    
    Formula: Landed $/lb = (Base Cost × Margin) + Freight
    Note: Margin applies to product cost ONLY, not freight.
    
    Args:
        base_cost_per_lb: FOB/base cost per pound
        freight_per_lb: Freight cost per pound
        margin: Margin multiplier (default 1.15 = 15%)
    
    Returns:
        Dictionary with pricing breakdown
    """
    product_with_margin = base_cost_per_lb * margin
    landed_per_lb = product_with_margin + freight_per_lb
    
    return {
        "base_cost_per_lb": base_cost_per_lb,
        "margin_multiplier": margin,
        "product_with_margin": round(product_with_margin, 4),
        "freight_per_lb": freight_per_lb,
        "landed_per_lb": round(landed_per_lb, 4),
        "margin_amount": round(base_cost_per_lb * (margin - 1), 4),
    }


def calculate_case_price(
    landed_per_lb: float,
    case_weight_lbs: float
) -> float:
    """
    Calculate case price from landed $/lb and case weight.
    
    Args:
        landed_per_lb: Landed price per pound
        case_weight_lbs: Weight of one case in pounds
    
    Returns:
        Case price rounded to 2 decimal places
    """
    return round(landed_per_lb * case_weight_lbs, 2)


def estimate_freight_quick(
    origin: str,
    base_dry_estimate: float = 350.0,
    target_date: Optional[date] = None
) -> float:
    """
    Quick freight estimate without API calls.
    
    Uses a reasonable base dry estimate and applies calibrated multipliers.
    
    Args:
        origin: Origin state code or warehouse key
        base_dry_estimate: Base dry freight estimate (default $350)
        target_date: Date for season modifier. Defaults to today.
    
    Returns:
        Estimated freight per lb
    """
    result = calculate_reefer_quote(base_dry_estimate, origin, target_date)
    return result["freight_per_lb"]


def process_freight_rates(
    dry_quotes: Dict[str, Dict[str, float]],
    target_date: Optional[date] = None
) -> Dict[str, Any]:
    """
    Process dry quotes for all warehouses and regions into reefer rates.
    
    Args:
        dry_quotes: Dict of {warehouse: {region: dry_quote}}
        target_date: Date for season modifier. Defaults to today.
    
    Returns:
        Complete freight rates structure with audit trail
    """
    if target_date is None:
        target_date = date.today()
    
    season_mod, season_type = get_season_modifier(target_date)
    
    result = {
        "metadata": {
            "quoteDate": target_date.isoformat(),
            "seasonModifier": season_mod,
            "seasonType": season_type,
            "generatedBy": "fleetwood-pricing/calculate_freight.py",
        },
        "warehouses": {},
    }
    
    for warehouse, regions in dry_quotes.items():
        wh_data = WAREHOUSE_MULTIPLIERS.get(warehouse, {})
        origin_mod = wh_data.get("multiplier", 2.10)
        
        result["warehouses"][warehouse] = {}
        
        for region, dry_quote in regions.items():
            reefer_quote = dry_quote * origin_mod * season_mod
            freight_per_lb = reefer_quote / STANDARD_WEIGHT
            
            result["warehouses"][warehouse][region] = {
                "dry_quote": dry_quote,
                "origin_multiplier": origin_mod,
                "reefer_quote": round(reefer_quote, 2),
                "freight_per_lb": round(freight_per_lb, 4),
            }
    
    return result


if __name__ == "__main__":
    # Test the calculator
    print("Fleetwood Freight Calculator - Calibrated Jan 2026")
    print("=" * 50)
    
    # Test origin multipliers
    for origin in ["GA", "PA", "IN", "GA_COLD", "A_R_T", "Indianapolis"]:
        mult = get_origin_multiplier(origin)
        print(f"{origin}: {mult}x")
    
    print()
    
    # Test reefer calculation
    dry_quote = 350.0
    for origin in ["GA_COLD", "A_R_T", "Indianapolis"]:
        result = calculate_reefer_quote(dry_quote, origin)
        print(f"{origin}: Dry ${dry_quote} → Reefer ${result['reefer_quote']} (${result['freight_per_lb']:.4f}/lb)")
    
    print()
    
    # Test landed price
    base_cost = 0.48
    freight = 0.20
    landed = calculate_landed_price(base_cost, freight)
    print(f"Base ${base_cost}/lb + Freight ${freight}/lb = Landed ${landed['landed_per_lb']:.4f}/lb")
    
    # Test case price
    case_weight = 40.0
    case_price = calculate_case_price(landed['landed_per_lb'], case_weight)
    print(f"Case price ({case_weight} lbs): ${case_price}")
