# Fleetwood Pricing

Weekly workflow to transform frozen protein inventory into regional customer price sheets with landed costs.

## Architecture

- **Input:** Raw inventory Excel from Fleetwood's system (header at row 5)
- **Processing:** Filter warehouses → Get freight quotes → Calculate landed prices → Categorize by protein
- **Output:** 3 regional price sheets (SE, NE, TX) in Excel and PDF formats

```
Raw Inventory Excel
        ↓
   Filter & Clean
        ↓
   Freight Quotes (GoShip API → Reefer multiplier)
        ↓
   Price Calculation (base × 1.15) + freight
        ↓
   Regional Excel Sheets (SE, NE, TX)
        ↓
   PDF Conversion (ReportLab professional method)
        ↓
   Visual Verification (PNG preview)
```

## Tech Stack

- **Data Processing:** Python, pandas, openpyxl
- **Freight Quotes:** GoShip GraphQL API (requires `GOSHIP_API_KEY`)
- **PDF Generation:** ReportLab (professional sales sheet method with fleetwood theme)
- **PDF Verification:** PyMuPDF (fitz) for PNG preview
- **Skills:** `fleetwood-inventory-pricing`, `goship-ltl-quotes`, `reefer-ltl-pricing`, `excel-to-pdf`, `opportunity-deals`

## Key Files & Entry Points

### Weekly Output Folder
```
~/Desktop/Fleetwood Pricing/[M-D-YY]/
├── Inventory_*.xlsx          # Raw input from system
├── freight-quotes.md         # GoShip quotes (dry rates)
├── freight-rates.json        # Calculated reefer rates
├── SE_Fleetwood_MMDDYY.xlsx  # Southeast price sheet
├── NE_Fleetwood_MMDDYY.xlsx  # Northeast price sheet
├── TX_Fleetwood_MMDDYY.xlsx  # Texas/Central price sheet
└── *.pdf                     # PDF versions of above
```

### Skill Reference Files
```
~/.claude/skills/fleetwood-inventory-pricing/
├── SKILL.md                  # Main workflow instructions
├── REFERENCE.md              # Lookup tables, formulas, column mappings
└── references/
    └── pallet-counts.json    # CRITICAL: Check this FIRST for CS/PLT values

~/.claude/skills/excel-to-pdf/
├── SKILL.md                  # PDF conversion guide
├── scripts/
│   ├── professional_sales_sheet.py  # Main PDF generator
│   ├── convert.py            # CLI tool
│   └── preview_pdf.py        # PNG preview utility
└── references/
    ├── templates.md          # Theme customization
    └── design-system.md      # Colors, typography, spacing

~/.claude/skills/opportunity-deals/
├── SKILL.md                  # Deal sheet generator guide
├── scripts/
│   ├── create_deal_sheet.py  # Single-deal PDF generator
│   ├── fleetwood-logo.png    # Company logo (transparent PNG)
│   └── freight_calculator.py # GoShip + reefer pricing
└── references/
    ├── destinations.json     # 6 SE destinations for averaging
    └── origin-modifiers.json # State freight modifiers
```

## Patterns & Conventions

### Pricing Logic
- **Column Y > 0:** Weight-sold item → `Landed $/lb = (Col Y × 1.15) + freight/lb`
- **Column Y = 0:** Case-sold item → `Case Price = (Col P × 1.15) + freight/case`

### Reefer Freight Formula
```
Reefer Quote = Dry Quote × 2.75 × Origin Modifier × Season Modifier
Freight $/lb = Reefer Quote ÷ 4,000 lbs
```

### Warehouses
| Code | Location | Freight Key |
|------|----------|-------------|
| A R T | Boyertown, PA | A_R_T |
| GA COLD | Americus, GA | GA_COLD |
| Indianapolis | Indianapolis, IN | Indianapolis |

### Protein Categories (sort order)
Turkey → Chicken → Pork → Beef → Seafood → Other

### Exclusion Rules
Remove items where:
- Column Z contains: "Box", "Bag", "Tote", "For Packout"
- Column F contains: "TT", "Tote", or weight ≥ 1000 LB

## Current State

### Working
- GoShip API integration for dry LTL quotes
- Reefer multiplier calculations with origin/season modifiers
- Regional price sheet generation with category colors
- PDF generation via ReportLab professional sales sheets (fleetwood theme)
- Visual verification workflow (PNG preview after generation)

### Typical Week Folder
- `1-19-26/` has complete output: 3 Excel + 3 PDF files with freight-rates.json

### Known Limitations
- Spec sheet URLs (specff.psce.pw) redirect to SharePoint requiring auth
- Workaround: Web search "[Brand] [Product] spec sheet Ti Hi" for pallet counts

### Recent Changes (Jan 2026)
- Switched from LibreOffice to ReportLab for PDF generation
- Default theme: `fleetwood` (forest green #1B4D3E)
- Auto-filters embedded disclaimers from Excel (prevents duplicate footers)
- Added visual verification step (always preview PDFs as PNG)

## Development Notes

### GoShip API Authentication
```bash
source ~/.claude/skills/goship-ltl-quotes/.env && export GOSHIP_API_KEY
python3 ~/.claude/skills/goship-ltl-quotes/scripts/request_quote.py \
  --origin-zip "31709" --dest-zip "30303" --quantity 2 --weight 4000 \
  --freight-class CLASS_70 --description "Frozen protein" --packaging PALLET
```

### PDF Generation (Professional Sales Sheets)
```python
from professional_sales_sheet import create_sales_sheet

create_sales_sheet(
    excel_path='SE_Fleetwood_011926.xlsx',
    output_path='SE_Fleetwood_011926.pdf',
    theme='fleetwood',  # Forest green theme (default)
    title='Southeast Region Specials',
    subtitle='Week of January 19, 2026',
    contact_name='Zach Chasse',
    contact_email='Chasse@fleetwoodfoods.com',
    contact_phone='352-274-0354'
)
```

### PDF Verification (CRITICAL)
Always preview PDFs after generation:
```python
import fitz  # PyMuPDF

doc = fitz.open('output.pdf')
for i, page in enumerate(doc):
    pix = page.get_pixmap(matrix=fitz.Matrix(2.0, 2.0))
    pix.save(f'preview_page{i+1}.png')
```

Verification checklist:
- Header: Title, subtitle, effective date
- Data: Zebra striping, currency formatting, CS/PLT populated
- Footer: Single footer with contact info (no duplicates)
- Multi-page: Headers repeat on subsequent pages

### Pallet Count Lookup
Always check master reference first before web research:
```python
with open('~/.claude/skills/fleetwood-inventory-pricing/references/pallet-counts.json') as f:
    pallet_counts = json.load(f)['items']
cs_plt = pallet_counts.get(item_code, {}).get('casesPerPallet', '')
```

### Excel Print Setup (for direct Excel printing)
```python
ws.page_setup.orientation = 'landscape'
ws.page_setup.fitToWidth = 1
ws.page_setup.fitToHeight = 0
ws.print_area = f'A1:I{ws.max_row}'
```
Note: PDF generation now uses ReportLab directly, not Excel print-to-PDF.

## Quick Reference

| Formula | |
|---------|---|
| Landed $/lb | (Base Cost × 1.15) + Freight |
| Reefer Freight | Dry Quote × 2.75 × Origin × Season |
| GA Origin Modifier | 1.00 |
| PA Origin Modifier | 1.15 |
| Jan-Apr Season | 1.00 |
| May-Jul Season | 1.15 (peak) |
| Nov-Dec Season | 1.08 (holiday) |

### PDF Themes
| Theme | Colors | Use Case |
|-------|--------|----------|
| `fleetwood` | Forest green #1B4D3E | **Default** - Standard customer sheets |
| `professional` | Navy #1E3A5F | General B2B |
| `minimal` | Gray #424242 | Tech clients |
| `bold` | Red #D32F2F | Promotions |

### Regional Titles
| Region | Title |
|--------|-------|
| SE | Southeast Region Specials |
| NE | Northeast Region Specials |
| TX | Texas Region Specials |

---

## Opportunity Deal Sheets

Time-sensitive supplier deals → customer-ready PDF deal sheets.

### Workflow
```
Supplier Email/Deal
        ↓
   Extract: Product, Pack, FOB Price, Location, Qty
        ↓
   6x GoShip Quotes (FOB → ATL, NSH, LEX, TPA, CIN, NOLA)
        ↓
   Average Freight + Reefer Multiplier (if frozen)
        ↓
   Landed Price = (FOB + Avg Freight) × 1.15
        ↓
   Generate Deal Sheet PDF
        ↓
   Visual Verification
```

### Deal Sheet Generation
```python
from create_deal_sheet import create_deal_sheet

create_deal_sheet(
    output_path="Gold_Creek_Ground_Chicken_Deal.pdf",
    product_name="Ground Chicken Mixed Dark White",
    brand="Gold Creek",
    pack_size="50 LB Wax Box",
    price_per_unit=0.62,
    price_unit="LB",
    case_price=31.00,
    quantity="3 Loads Available",
    dating="BBD: Jun 2026",
    has_spec_sheet=True,
)
```

### Deal Sheet Design
- **Colors:** Fleetwood Blue (#1E6BB8) + Yellow (#F5C731) accent
- **Layout:** Logo header, product image, large price box, availability section, contact footer
- **Logo:** Uses `fleetwood-logo.png` in scripts folder

### Freight Averaging Destinations
| City | Zip |
|------|-----|
| Atlanta, GA | 30303 |
| Nashville, TN | 37203 |
| Lexington, KY | 40507 |
| Tampa, FL | 33602 |
| Cincinnati, OH | 45202 |
| New Orleans, LA | 70112 |

### Quick Freight Estimate (No API)
```python
from freight_calculator import estimate_freight_per_lb

freight = estimate_freight_per_lb("GA", "FROZEN")  # ~$0.24/lb
landed = (fob_price + freight) * 1.15
```
