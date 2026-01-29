# Fleetwood Pricing

Weekly workflow to transform frozen protein inventory into regional customer price sheets with landed costs.

## Overview

This project processes Fleetwood's raw inventory data and generates professional price sheets for three regions (Southeast, Northeast, and Texas) with calculated landed costs including freight.

## Features

- **Automated Freight Quotes**: Integration with GoShip API for LTL freight pricing
- **Reefer Calculations**: Automatic reefer multiplier application for frozen products
- **Regional Price Sheets**: Generates Excel and PDF outputs for SE, NE, and TX regions
- **Professional PDFs**: ReportLab-based sales sheets with Fleetwood branding
- **Deal Sheet Generator**: Creates customer-ready PDFs for time-sensitive supplier deals

## Project Structure

```
Fleetwood Pricing/
├── CLAUDE.md                 # Detailed workflow documentation
├── fleetwood-logo.png        # Company logo for PDFs
├── deals/                    # Opportunity deal sheets
├── [M-D-YY]/                 # Weekly output folders
│   ├── Inventory_*.xlsx      # Raw inventory input
│   ├── freight-quotes.md     # GoShip dry quotes
│   ├── freight-rates.json    # Calculated reefer rates
│   ├── SE_Fleetwood_*.xlsx   # Southeast price sheet
│   ├── NE_Fleetwood_*.xlsx   # Northeast price sheet
│   ├── TX_Fleetwood_*.xlsx   # Texas price sheet
│   └── *.pdf                 # PDF versions
```

## Tech Stack

- **Python** with pandas, openpyxl
- **GoShip GraphQL API** for freight quotes
- **ReportLab** for professional PDF generation
- **PyMuPDF (fitz)** for PDF verification

## Documentation

See [CLAUDE.md](CLAUDE.md) for complete workflow documentation, including:
- Pricing formulas and logic
- Freight calculation methods
- PDF generation and verification
- Deal sheet creation
- Regional configurations

## Contact

Zach Chasse  
Email: Chasse@fleetwoodfoods.com  
Phone: 352-274-0354

