---
name: fleetwood-pricing
description: "Weekly workflow to transform frozen protein inventory into regional customer price sheets with landed costs. Use when: (1) Running Monday freight quotes, (2) Processing raw inventory spreadsheets, (3) Generating SE/NE/TX regional price sheets with landed costs, (4) Creating opportunity deal sheets, (5) Looking up pallet counts. This is the SINGLE SOURCE OF TRUTH for all Fleetwood pricing operations."
---

# Fleetwood Pricing Workflow

Weekly process to transform raw inventory into customer-ready regional price sheets.

## Architecture

```
Raw Inventory Excel
        ↓
   Filter & Clean
        ↓
   Freight Quotes (GoShip API → Calibrated Reefer Multiplier)
        ↓
   Price Calculation (base × 1.15) + freight
        ↓
   Regional Excel Sheets (SE, NE, TX)
        ↓
   Validation (REQUIRED before PDF)
        ↓
   PDF Conversion (ReportLab)
        ↓
   Visual Verification (PNG preview)
```

## Quick Reference

| Formula | |
|---------|---|
| Landed $/lb | (Base Cost × 1.15) + Freight |
| Case Price | Landed $/lb × Case Weight |
| Reefer Freight | Dry Quote × Origin Multiplier × Season |

| Warehouse | Location | Reefer Multiplier |
|-----------|----------|-------------------|
| GA COLD | Americus, GA | **1.90x** |
| A R T | Boyertown, PA | **2.35x** |
| Indianapolis | Indianapolis, IN | **2.10x** |

| Season | Months | Modifier |
|--------|--------|----------|
| Normal | Jan-Apr, Aug-Oct | 1.00 |
| Peak | May-Jul | 1.15 |
| Holiday | Nov-Dec | 1.08 |

---

## Step 1: Create Week Folder

Create output folder for the week's files.

---

## Step 2: Get Freight Rates

### Option A: User Provides Quotes
Parse provided `freight-quotes.md` and calculate reefer rates.

### Option B: Run GoShip API
Use `scripts/request_quote.py` to get dry LTL quotes.

```bash
source .env && export GOSHIP_API_KEY
python3 scripts/request_quote.py \
  --origin-zip "31709" --dest-zip "30303" \
  --quantity 2 --weight 4000 \
  --freight-class CLASS_70 --description "Frozen protein" --packaging PALLET
```

### Calculate Reefer Rates

Use `scripts/calculate_freight.py` (SINGLE SOURCE OF TRUTH):

```python
from calculate_freight import calculate_reefer_quote, get_season_modifier

# Get current season
season_mod, season_type = get_season_modifier()
print(f"Season: {season_type} ({season_mod}x)")

# Calculate reefer from dry quote
result = calculate_reefer_quote(dry_quote=350.0, origin="GA_COLD")
print(f"Reefer: ${result['reefer_quote']} (${result['freight_per_lb']:.4f}/lb)")
```

### Save Freight Rates
Save `freight-rates.json` with audit trail. See `references/REFERENCE.md` for schema.

---

## Step 3: Load Inventory & Filter

### Read Excel (header at row 5)
```python
df = pd.read_excel("Inventory....xlsx", header=4)
```

### Filter: Target Warehouses + Available Stock
```python
warehouses = ['A R T', 'GA COLD', 'Indianapolis']
df = df[df['Warehouse'].isin(warehouses) & (df['On-Hand Available'] > 0)]
```

### CRITICAL: Exclude Internal Use Items

Remove items where ANY of these match:
- Column Z (Notes) contains: "Box", "Bag", "Tote", "For Packout"
- Column F (Pack Size) contains: "TT" or "Tote"
- Column F (Pack Size) weight ≥ 1000 LB

---

## Step 4: Pallet Count Lookup

### Check Master Reference FIRST

```python
import json
with open('references/pallet-counts.json') as f:
    pallet_counts = json.load(f)['items']

cs_plt = pallet_counts.get(item_code, {}).get('casesPerPallet', '')
```

### For Missing Items (research in this order):
1. Web search: "[Brand] [Product] [Pack] spec sheet Ti Hi pallet"
2. Similar product lookup (same pack size pattern in master reference)
3. Flag for manual review

**Update Master Reference:** Add newly researched pallet counts to `pallet-counts.json`.

---

## Step 5: Calculate Landed Prices

### Pricing Mode (CRITICAL)

```python
from calculate_freight import calculate_landed_price, calculate_case_price

if row['Average Unit Cost.1'] > 0:  # Column Y - weight-sold
    base_cost = row['Average Unit Cost.1']  # $/lb
    landed = calculate_landed_price(base_cost, freight_per_lb)
    landed_per_lb = landed['landed_per_lb']
    case_price = calculate_case_price(landed_per_lb, case_weight)
else:  # Case-sold
    base_cost = row['Average Unit Cost']  # $/case from Column P
    freight_per_case = freight_per_lb * case_weight
    case_price = (base_cost * 1.15) + freight_per_case
    landed_per_lb = None  # Don't show $/lb for case-sold items
```

---

## Step 6: Categorize by Protein Type

Parse description for keywords, apply category colors.

**Order:** Turkey → Chicken → Pork → Beef → Seafood → Other

See `references/protein-categories.json` for keywords and colors.

---

## Step 7: Generate Excel Sheets

Create 3 regional files: `SE_Fleetwood_MMDDYY.xlsx`, `NE_Fleetwood_MMDDYY.xlsx`, `TX_Fleetwood_MMDDYY.xlsx`

### Sheet Structure
```
[Header Row - blue background, white text]
CODE | DESCRIPTION | PACK | BRAND | CS AVAIL | $ PER LB | CASE PRICE | CS/PLT | SPEC SHEET

AMERICUS, GA [gray header row]
[Items grouped by category with category colors]

BOYERTOWN, PA [gray header row]
[Items grouped by category]

INDIANAPOLIS, IN [gray header row - if items exist]
[Items grouped by category]

[Disclaimer at bottom]
```

See `references/REFERENCE.md` for exact column widths, colors, and disclaimer text.

---

## Step 8: Validate Output (REQUIRED)

**Run validation BEFORE converting to PDF:**

```bash
python3 scripts/validate_output.py SE_Fleetwood_MMDDYY.xlsx
```

**Do not proceed to PDF conversion if there are errors.**

---

## Step 9: Convert to PDF

Use `scripts/professional_sales_sheet.py` with fleetwood theme:

```python
from professional_sales_sheet import create_sales_sheet

create_sales_sheet(
    excel_path='SE_Fleetwood_011926.xlsx',
    output_path='SE_Fleetwood_011926.pdf',
    theme='fleetwood',
    title='Southeast Region Specials',
    subtitle='Week of January 19, 2026',
    contact_name='Zach Chasse',
    contact_email='Chasse@fleetwoodfoods.com',
    contact_phone='352-274-0354'
)
```

### Visual Verification (CRITICAL)

Always preview PDFs after generation:

```python
from preview_pdf import preview_pdf
preview_pdf('SE_Fleetwood_011926.pdf', 'preview.png')
```

Verification checklist:
- Header: Title, subtitle, effective date
- Data: Zebra striping, currency formatting, CS/PLT populated
- Footer: Single footer with contact info (no duplicates)
- Multi-page: Headers repeat on subsequent pages

---

## Final Checklist

- [ ] Season modifier applied automatically
- [ ] Freight rates calculated with calibrated multipliers
- [ ] Internal use items excluded
- [ ] All items have pallet counts (or flagged for review)
- [ ] 3 Excel files created (SE, NE, TX)
- [ ] **Validation passed with 0 errors**
- [ ] 3 PDF files created
- [ ] Visual verification completed
- [ ] Category colors applied
- [ ] Disclaimer included on each sheet

---

## Opportunity Deal Sheets

For time-sensitive supplier deals → customer-ready PDF deal sheets.

### Workflow
```
Supplier Email/Deal
        ↓
   Extract: Product, Pack, FOB Price, Location, Qty
        ↓
   6x GoShip Quotes (FOB → ATL, NSH, LEX, TPA, CIN, NOLA)
        ↓
   Average Freight + Reefer Multiplier
        ↓
   Landed Price = (FOB + Avg Freight) × 1.15
        ↓
   Generate Deal Sheet PDF
```

### Quick Freight Estimate (No API)

```python
from calculate_freight import estimate_freight_quick

freight = estimate_freight_quick("GA")  # ~$0.17/lb for GA origin
landed = (fob_price + freight) * 1.15
```

---

## Reference Files

All paths relative to this skill directory:

| File | Purpose |
|------|---------|
| `references/REFERENCE.md` | All lookup tables, formulas, column mappings |
| `references/freight-modifiers.json` | **SINGLE SOURCE**: Calibrated reefer multipliers |
| `references/pallet-counts.json` | Master pallet count database |
| `references/protein-categories.json` | Category keywords and colors |
| `references/freight-lanes.json` | Representative lanes for quotes |
| `references/api-schema.md` | GoShip GraphQL schema |
| `references/freight-classes.md` | NMFC freight class guide |

## Scripts

| Script | Purpose |
|--------|---------|
| `scripts/request_quote.py` | GoShip API integration |
| `scripts/calculate_freight.py` | **UNIFIED** reefer/landed cost calculator |
| `scripts/process_inventory.py` | Excel parsing and filtering |
| `scripts/lookup_pallet_counts.py` | Pallet count research |
| `scripts/professional_sales_sheet.py` | ReportLab PDF generation |
| `scripts/preview_pdf.py` | PDF to PNG preview |
| `scripts/validate_output.py` | Pricing and data validation |
