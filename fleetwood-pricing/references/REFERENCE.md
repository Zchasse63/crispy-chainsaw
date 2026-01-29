# Fleetwood Pricing Reference

Lookup tables, formulas, and configuration for the weekly pricing workflow.

## Warehouses

| Code | Location | Zip | Freight Key |
|------|----------|-----|-------------|
| A R T | Boyertown, PA | 19512 | A_R_T |
| GA COLD | Americus, GA | 31709 | GA_COLD |
| Indianapolis | Indianapolis, IN | 46201 | Indianapolis |

## Pricing Formulas

### Landed Price Calculation
```
Landed $/lb = (Base Cost × 1.15) + Freight $/lb
Case Price = Landed $/lb × Case Weight
```

### Reefer Freight Multiplier (Calibrated Jan 2026)
```
Reefer Quote = Dry Quote × Origin Multiplier × Season Modifier
Freight $/lb = Reefer Quote ÷ 4,000 lbs
```

**Origin Multipliers** (calibrated against 4 actual broker quotes):
| Origin | Multiplier | Notes |
|--------|------------|-------|
| GA (Americus) | **1.90x** | SE poultry hub - abundant reefer capacity |
| PA (Boyertown) | **2.35x** | NE - tighter reefer capacity |
| IN (Indianapolis) | **2.10x** | Midwest - moderate capacity |

See `freight-modifiers.json` for complete state-by-state multipliers.

**Calibration Validation:**
| Lane | Our Est | Actual | Variance |
|------|---------|--------|----------|
| PA→GA frozen | $0.482/lb | $0.475/lb | +1.5% ✅ |
| PA→KY frozen | $0.482/lb | $0.475/lb | +1.5% ✅ |
| GA→NO frozen | $0.429/lb | ~$0.40/lb | +7% ✅ |

**Season Modifiers:**
| Period | Modifier |
|--------|----------|
| Jan-Apr | 1.00 |
| May-Jul | 1.15 (peak produce) |
| Aug-Oct | 1.00 |
| Nov-Dec | 1.08 (holiday) |

## Column Mapping (Raw Inventory)

| Excel Column | Header Name | Output Use |
|--------------|-------------|------------|
| B | Item Code | CODE |
| C | Description | DESCRIPTION |
| F | Pack Size | PACK |
| G | Brand | BRAND |
| N | On-Hand Available | CS AVAIL |
| P | Average Unit Cost | Base cost for case-sold items |
| Y | Average Unit Cost.1 | Base cost for weight-sold items ($/lb) |
| Z | Notes | SPEC SHEET LINK (if URL present) |

**Note:** Raw inventory Excel has header at row 5 (use `header=4` in pandas).

### Pricing Mode Logic
- **Column Y > 0**: Item sold by weight → use $/lb pricing, calculate case price from weight
- **Column Y = 0 or empty**: Item sold by case → use Column P for case pricing

## Protein Categories

| Category | Keywords | Excel Color (Hex) | RGB |
|----------|----------|-------------------|-----|
| Turkey | turkey, turk | FFCCCC | (255, 204, 204) |
| Chicken | chicken, wing, tender, nugget, patty, filet, breast, thigh, WOG, poultry, chick | CCE5FF | (204, 229, 255) |
| Pork | pork, bacon, ham, sausage, rib, loin | FFCC99 | (255, 204, 153) |
| Beef | beef, burger, meatball, roast, steak | CCCCFF | (204, 204, 255) |
| Seafood | pollock, fish, shrimp, seafood, salmon, tilapia | FFFF99 | (255, 255, 153) |
| Other | (default) | E6E6E6 | (230, 230, 230) |

**Sort order:** Turkey → Chicken → Pork → Beef → Seafood → Other

## Pack Size Parsing

| Pattern | Example | Case Weight |
|---------|---------|-------------|
| `N/N LB` | 2/5 LB | 10 lbs |
| `N/NLB` | 6/5LB | 30 lbs |
| `N LB` | 40 LB | 40 lbs |
| `NLB` | 30LB | 30 lbs |
| `N/N.NLB` | 6/5.62LB | 33.72 lbs |

**Catch Weight Indicators** (case price = blank):
- PC, HD, Head, CW, TRAY in pack size

## Internal Use Item Exclusions

**Exclude from price sheets if ANY of these match:**

| Check | Criteria | Examples |
|-------|----------|----------|
| Column Z (Notes) | Contains: "Box", "Bag", "Tote", "For Packout" | "BAG", "for packout" |
| Column F (Pack Size) | Contains: "TT" or "Tote" | "1000 LB TT" |
| Column F (Pack Size) | Weight ≥ 1000 LB | "1000 LB", "2000LB" |

## Freight Lanes (for GoShip quotes)

Quote at **4,000 lbs / 2 pallets** for each lane.

### From Americus, GA (31709)
| Destination | Zip | Region |
|-------------|-----|--------|
| Atlanta, GA | 30303 | SE |
| Jacksonville, FL | 32099 | SE |
| Charlotte, NC | 28202 | SE |
| Nashville, TN | 37203 | SE |
| Birmingham, AL | 35203 | SE |
| New Orleans, LA | 70112 | SE |
| New York, NY | 10001 | NE |
| Philadelphia, PA | 19102 | NE |
| Dallas, TX | 75201 | TX |
| Houston, TX | 77002 | TX |

### From Boyertown, PA (19512)
| Destination | Zip | Region |
|-------------|-----|--------|
| New York, NY | 10001 | NE |
| Boston, MA | 02101 | NE |
| Baltimore, MD | 21202 | NE |
| Pittsburgh, PA | 15222 | NE |
| Columbus, OH | 43215 | NE |
| Atlanta, GA | 30303 | SE |
| Jacksonville, FL | 32099 | SE |
| Dallas, TX | 75201 | TX |

### From Indianapolis, IN (46201)
| Destination | Zip | Region |
|-------------|-----|--------|
| Chicago, IL | 60601 | TX |
| St. Louis, MO | 63101 | TX |
| Nashville, TN | 37203 | SE |
| Louisville, KY | 40202 | SE |
| Atlanta, GA | 30303 | SE |
| Columbus, OH | 43215 | NE |
| Detroit, MI | 48201 | NE |

## Regional Distribution

| Region | Key | States |
|--------|-----|--------|
| Southeast | SE | GA, FL, TN, NC, SC, AL, KY, LA, MS, AR |
| Northeast | NE | PA, NJ, NY, CT, MA, MD, VA, OH, MI, IN, WV, DE, RI, NH, ME |
| Texas/Central | TX | TX, MO, OK, KS, NE, MN, IA, IL, AZ, CA, OR, WA |

## Output Sheet Structure

### Columns
```
CODE | DESCRIPTION | PACK | BRAND | CS AVAIL | $ PER LB | CASE PRICE | CS/PLT | SPEC SHEET
```

### Warehouse Order (on sheets)
1. AMERICUS, GA
2. BOYERTOWN, PA
3. INDIANAPOLIS, IN

### Disclaimer Text
```
Prices include delivered freight based on 2-pallet (4,000 lb) minimum order.
Smaller orders or remote locations may incur additional charges. Quote valid 7 days.
Temperature: 0°F to -10°F continuous.

Zach Chasse | Chasse@fleetwoodfoods.com | 352-274-0354
```

## Reference Files (Relative Paths)

All paths are relative to the skill directory (`fleetwood-pricing/`):

```
references/
├── REFERENCE.md              # This file
├── freight-modifiers.json    # SINGLE SOURCE: Calibrated reefer multipliers
├── pallet-counts.json        # Master pallet count lookup
├── protein-categories.json   # Category keywords and colors
├── freight-lanes.json        # Representative lanes for quotes
├── pack-size-patterns.json   # Regex for parsing pack sizes
├── api-schema.md             # GoShip GraphQL schema
├── freight-classes.md        # NMFC freight class guide
└── freight-rate-archive/     # Historical freight rates
    └── freight-rates-YYYY-MM-DD.json
```

## Known Limitations

### Spec Sheet URLs
- URLs like `specff.psce.pw/*` redirect to SharePoint
- SharePoint requires authentication (will get 403 errors)
- **Workaround:** Use web research instead: "[Brand] [Product] [Pack] spec sheet Ti Hi"

### Pallet Count Research Priority
1. Master reference lookup (pallet-counts.json)
2. Web research for Ti/Hi specifications
3. Similar product lookup (same pack size pattern)
4. Flag for manual review if cannot determine

## Freight Rates JSON Schema

**Full audit trail structure:**
```json
{
  "metadata": {
    "quoteDate": "2026-01-19",
    "seasonModifier": 1.00,
    "seasonType": "normal",
    "priorWeekFile": "freight-rates-2026-01-12.json"
  },
  "warehouses": {
    "GA_COLD": {
      "SE": {
        "average_per_lb": 0.213,
        "lanes": {
          "Atlanta_30303": { "dry": 280, "reefer": 770, "per_lb": 0.193 },
          "Jacksonville_32099": { "dry": 320, "reefer": 880, "per_lb": 0.220 }
        }
      },
      "NE": { "..." },
      "TX": { "..." }
    },
    "A_R_T": { "..." },
    "Indianapolis": { "..." }
  },
  "weekOverWeek": {
    "GA_COLD": {
      "SE": { "current": 0.213, "prior": 0.205, "change_pct": 3.9 }
    }
  }
}
```

## Output Validation Rules

### Pricing Validation
| Check | Rule | Flag If |
|-------|------|---------|
| Landed > Base | landed_per_lb > base_cost | Always false (error) |
| Freight bounds | 0.10 ≤ freight_per_lb ≤ 0.50 | Outside range (warning) |
| Case price bounds | 5.00 ≤ case_price ≤ 500.00 | Outside range (warning) |
| Margin applied | landed_per_lb ≥ base_cost × 1.15 | Less than (error) |
| Case math | case_price ≈ landed_per_lb × case_weight | >1% variance (error) |

### Data Completeness Validation
| Check | Rule | Flag If |
|-------|------|---------|
| CS/PLT coverage | % items with pallet counts | < 50% (warning), 0% (error) |
| Internal items excluded | No TOTE/TT/>=1000 LB items in output | Any found (error) |
| CW markers | Catch weight items show "CW" in case price | Missing (error) |
| No NaN values | No "$nan", "nan", or "#N/A" in output | Any found (error) |
| Price coverage | Items with $/lb OR case price | < 90% (warning) |
