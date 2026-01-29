#!/usr/bin/env python3
"""
Fleetwood Inventory Processor

Transforms raw inventory exports into regional customer price sheets
with landed costs (freight + 15% margin included).

Usage:
    python process_inventory.py --input <raw_inventory.xlsx> --date-folder <M-D-YY> --freight-rates <freight-rates.json>
"""

import pandas as pd
import json
import re
import os
import sys
from datetime import datetime
from pathlib import Path
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils.dataframe import dataframe_to_rows
from openpyxl.worksheet.page import PageMargins

# =============================================================================
# CONFIGURATION
# =============================================================================

WAREHOUSES = {
    'A R T': {'name': 'BOYERTOWN, PA', 'code': 'PA', 'zip': '19512'},
    'GA COLD': {'name': 'AMERICUS, GA', 'code': 'GA', 'zip': '31709'},
    'Indianapolis': {'name': 'INDIANAPOLIS, IN', 'code': 'IN', 'zip': '46201'},
}

REGIONS = ['SE', 'NE', 'TX']

MARGIN_PERCENT = 15

CONTACT_INFO = {
    'name': 'Zach Chasse',
    'email': 'Chasse@fleetwoodfoods.com',
    'phone': '352-274-0354'
}

DISCLAIMER = """Prices include delivered freight based on 2-pallet (4,000 lb) minimum order.
Smaller orders or remote locations may incur additional charges. Quote valid 7 days.
Temperature: 0°F to -10°F continuous.

{name} | {email} | {phone}""".format(**CONTACT_INFO)

# Category colors (ARGB format for openpyxl)
CATEGORY_COLORS = {
    'Turkey': 'FFFFCCCC',    # Light Pink
    'Chicken': 'FFCCE5FF',   # Light Blue
    'Pork': 'FFFFCC99',      # Light Coral
    'Beef': 'FFCCCCFF',      # Light Purple
    'Seafood': 'FFFFFF99',   # Light Yellow
    'Fries': 'FFFFD9B3',     # Light Orange/Tan
    'Dessert': 'FFFFE6CC',   # Light Peach
    'Other': 'FFD4EDDA',     # Light Green (for misc items)
}

# Category keywords (checked in order)
CATEGORY_KEYWORDS = {
    'Turkey': ['turkey', 'turk'],
    'Chicken': ['chicken', 'chick', 'wing', 'tender', 'nugget', 'patty', 
                'filet', 'fillet', 'breast', 'thigh', 'drumstick', 'leg',
                'wog', 'poultry', 'hen', 'fryer', 'roaster',
                # Additional keywords to catch more chicken items
                'halal', 'diced', 'glazed', 'breaded', 'white meat', 
                'buffalo', 'chunk', 'strips', 'fritter', 'bnls', 'boneless',
                'dark meat', 'fried', 'grilled', 'roasted', 'rtc', 'fc '],
    'Pork': ['pork', 'bacon', 'ham', 'sausage', 'rib', 'loin', 
             'chop', 'belly', 'shoulder', 'butt', 'carnitas'],
    'Beef': ['beef', 'burger', 'meatball', 'roast', 'steak', 
             'chuck', 'sirloin', 'ribeye', 'brisket'],
    'Seafood': ['pollock', 'fish', 'shrimp', 'seafood', 'salmon', 
                'tilapia', 'cod', 'catfish', 'crab', 'lobster', 'tuna'],
    'Fries': ['fries', 'fry', 'potato', 'tater', 'hash brown'],
    'Dessert': ['cake', 'tiramisu', 'dessert', 'pie', 'brownie', 'cookie', 'cheesecake'],
}

# =============================================================================
# PACK SIZE PARSING
# =============================================================================

def parse_pack_size(pack_size, description=''):
    """
    Parse pack size to get total case weight in pounds.
    Returns None for catch weight items.
    """
    if not pack_size or pd.isna(pack_size):
        return None
    
    pack_str = str(pack_size).upper().strip()
    desc_str = str(description).upper() if description else ''
    
    # Check for catch weight indicators
    cw_indicators = ['PC', '/HD', 'HEAD', ' CW ']
    if any(ind in pack_str or ind in desc_str for ind in cw_indicators):
        return None
    
    # Try multiplied format: N/N LB or N-N LB or N/NLB or N-NLB
    # Both slash and dash mean the same thing (e.g., 12/2 LB = 12-2 LB = 24 lbs)
    match = re.match(r'(\d+)\s*[/\-]\s*(\d+\.?\d*)\s*LB', pack_str, re.IGNORECASE)
    if match:
        return float(match.group(1)) * float(match.group(2))
    
    # Try bulk format: N LB or NLB
    match = re.match(r'^(\d+\.?\d*)\s*LB', pack_str, re.IGNORECASE)
    if match:
        return float(match.group(1))
    
    # Try ounce format: N/N OZ or N-N OZ
    match = re.match(r'(\d+)\s*[/\-]\s*(\d+\.?\d*)\s*OZ', pack_str, re.IGNORECASE)
    if match:
        return (float(match.group(1)) * float(match.group(2))) / 16
    
    # Try single ounce format: N OZ
    match = re.match(r'^(\d+\.?\d*)\s*OZ', pack_str, re.IGNORECASE)
    if match:
        return float(match.group(1)) / 16
    
    return None

def categorize_product(description):
    """Categorize product based on description keywords."""
    if not description or pd.isna(description):
        return 'Other'
    
    desc_lower = str(description).lower()
    
    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(kw in desc_lower for kw in keywords):
            return category
    
    return 'Other'

# =============================================================================
# DATA PROCESSING
# =============================================================================

def load_raw_inventory(filepath):
    """Load and filter raw inventory file."""
    # Read with header at row 4 (0-indexed)
    df = pd.read_excel(filepath, header=4)
    
    # Filter for target warehouses
    df = df[df['Warehouse'].isin(WAREHOUSES.keys())]
    
    # Filter for available inventory
    df = df[df['On-Hand Available'].notna() & (df['On-Hand Available'] > 0)]
    
    # Rename columns for clarity
    # Column Y = 'Average Unit Cost.1' ($/lb) - primary pricing
    # Column P = 'Average Unit Cost' ($/case) - fallback for items not sold by pound
    df = df.rename(columns={
        'Item Code': 'code',
        'Description': 'description',
        'Pack Size': 'pack_size',
        'Brand': 'brand',
        'On-Hand Available': 'cases_available',
        'Average Unit Cost.1': 'cost_per_lb',      # Column Y
        'Average Unit Cost': 'cost_per_case',       # Column P (fallback)
        'Notes': 'spec_sheet_url',
        'Warehouse': 'warehouse_code'
    })
    
    # Select and order columns
    cols = ['warehouse_code', 'code', 'description', 'pack_size', 'brand', 
            'cases_available', 'cost_per_lb', 'cost_per_case', 'spec_sheet_url']
    df = df[[c for c in cols if c in df.columns]]
    
    return df

def load_freight_rates(filepath):
    """Load freight rates JSON."""
    with open(filepath, 'r') as f:
        return json.load(f)

def load_pallet_counts(filepath):
    """Load pallet counts master reference."""
    with open(filepath, 'r') as f:
        data = json.load(f)
    return data.get('items', {})

def get_pallet_count(item_code, pallet_counts):
    """Get pallet count for item, return None if not found."""
    item_data = pallet_counts.get(str(item_code))
    if item_data:
        return item_data.get('casesPerPallet')
    return None

def calculate_landed_price(base_cost, freight_per_lb):
    """Calculate landed price with margin.

    Formula: Landed $/lb = (Base Cost × 1.15) + Freight $/lb
    Margin applies to base cost ONLY, not to freight.
    """
    if pd.isna(base_cost) or base_cost <= 0:
        return None
    return round((base_cost * 1.15) + freight_per_lb, 4)

def calculate_case_price(landed_per_lb, pack_size, description):
    """Calculate case price from landed $/lb and pack size."""
    if landed_per_lb is None:
        return None
    
    case_weight = parse_pack_size(pack_size, description)
    if case_weight is None:
        return None
    
    return round(landed_per_lb * case_weight, 2)

# =============================================================================
# EXCEL GENERATION
# =============================================================================

def create_price_sheet(df, region, freight_rates, pallet_counts, date_str):
    """Create Excel workbook for a region."""
    wb = Workbook()
    ws = wb.active
    ws.title = "Price List"
    
    # Column headers
    headers = ['CODE', 'DESCRIPTION', 'PACK', 'BRAND', 'CS AVAIL', 
               '$ PER LB', 'CASE PRICE', 'CS/PLT', 'SPEC SHEET']
    
    # Column widths
    col_widths = [15, 45, 12, 22, 10, 10, 12, 8, 35]
    
    # Header style
    header_font = Font(bold=True, color='FFFFFF')
    header_fill = PatternFill(start_color='FF1F4E79', end_color='FF1F4E79', fill_type='solid')
    header_alignment = Alignment(horizontal='center', vertical='center')
    
    # Border style
    thin_border = Border(
        left=Side(style='thin'),
        right=Side(style='thin'),
        top=Side(style='thin'),
        bottom=Side(style='thin')
    )
    
    # Write headers
    for col, (header, width) in enumerate(zip(headers, col_widths), 1):
        cell = ws.cell(row=1, column=col, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_alignment
        cell.border = thin_border
        ws.column_dimensions[chr(64 + col)].width = width
    
    current_row = 2
    
    # Process each warehouse
    for wh_code, wh_info in WAREHOUSES.items():
        wh_df = df[df['warehouse_code'] == wh_code].copy()
        
        if len(wh_df) == 0:
            continue
        
        # Get freight rate for this warehouse → region
        wh_key = wh_info['code']
        freight_per_lb = freight_rates.get(wh_key, {}).get(region, 0.30)  # Default fallback
        
        # Add category column
        wh_df['category'] = wh_df['description'].apply(categorize_product)
        
        # Calculate prices
        # For items with cost_per_lb (Column Y): calculate landed $/lb and case price
        # For items with only cost_per_case (Column P): use case price directly with markup (no $/lb shown)
        def calc_prices(row):
            cost_lb = row.get('cost_per_lb', 0) if pd.notna(row.get('cost_per_lb')) else 0
            cost_case = row.get('cost_per_case', 0) if pd.notna(row.get('cost_per_case')) else 0
            
            if cost_lb > 0:
                # Normal pricing - item sold by pound
                landed_lb = calculate_landed_price(cost_lb, freight_per_lb)
                case_weight = parse_pack_size(row['pack_size'], row['description'])
                if landed_lb and case_weight:
                    case_price = round(landed_lb * case_weight, 2)
                else:
                    case_price = None
                return pd.Series({'landed_per_lb': landed_lb, 'case_price': case_price, 'price_type': 'per_lb'})
            elif cost_case > 0:
                # Fallback - item sold by case (like cakes, desserts)
                # Formula: Case Price = (Base Cost × 1.15) + Freight per Case
                # No $/lb shown for case-sold items
                case_weight = parse_pack_size(row['pack_size'], row['description'])
                if case_weight:
                    freight_per_case = freight_per_lb * case_weight
                    case_price = round((cost_case * 1.15) + freight_per_case, 2)
                else:
                    # Can't calculate freight without case weight, just apply margin
                    case_price = round(cost_case * 1.15, 2)
                return pd.Series({'landed_per_lb': None, 'case_price': case_price, 'price_type': 'per_case'})
            else:
                return pd.Series({'landed_per_lb': None, 'case_price': None, 'price_type': 'none'})
        
        price_calcs = wh_df.apply(calc_prices, axis=1)
        wh_df['landed_per_lb'] = price_calcs['landed_per_lb']
        wh_df['case_price'] = price_calcs['case_price']
        wh_df['price_type'] = price_calcs['price_type']
        
        wh_df['pallet_count'] = wh_df['code'].apply(
            lambda x: get_pallet_count(x, pallet_counts)
        )
        
        # Sort by category then description
        category_order = ['Turkey', 'Chicken', 'Pork', 'Beef', 'Seafood', 'Bakery', 'Dessert', 'Fries', 'Sides']
        wh_df['category_sort'] = wh_df['category'].apply(
            lambda x: category_order.index(x) if x in category_order else 99
        )
        wh_df = wh_df.sort_values(['category_sort', 'description'])
        
        # Write warehouse header
        ws.cell(row=current_row, column=1, value=wh_info['name'])
        ws.cell(row=current_row, column=1).font = Font(bold=True, size=12)
        ws.merge_cells(start_row=current_row, start_column=1, 
                       end_row=current_row, end_column=len(headers))
        current_row += 1
        
        # Write items grouped by category
        current_category = None
        for _, row in wh_df.iterrows():
            category = row['category']
            fill_color = CATEGORY_COLORS.get(category, 'FFD4EDDA')  # Default to light green if unknown
            row_fill = PatternFill(start_color=fill_color, end_color=fill_color, fill_type='solid')
            
            # Write row data
            values = [
                row['code'],
                row['description'][:45] if pd.notna(row['description']) else '',
                row['pack_size'] if pd.notna(row['pack_size']) else '',
                row['brand'] if pd.notna(row['brand']) else '',
                int(row['cases_available']) if pd.notna(row['cases_available']) else '',
                f"${row['landed_per_lb']:.2f}" if pd.notna(row['landed_per_lb']) and row['landed_per_lb'] else '',
                f"${row['case_price']:.2f}" if pd.notna(row['case_price']) and row['case_price'] else '',
                int(row['pallet_count']) if pd.notna(row['pallet_count']) and row['pallet_count'] else '',
                row['spec_sheet_url'] if pd.notna(row['spec_sheet_url']) else ''
            ]
            
            for col, value in enumerate(values, 1):
                cell = ws.cell(row=current_row, column=col, value=value)
                cell.fill = row_fill
                cell.border = thin_border
                if col in [5, 6, 7, 8]:  # Numeric columns
                    cell.alignment = Alignment(horizontal='center')
            
            current_row += 1
        
        # Add blank row between warehouses
        current_row += 1
    
    # Add disclaimer at bottom
    current_row += 1
    ws.cell(row=current_row, column=1, value=DISCLAIMER)
    ws.merge_cells(start_row=current_row, start_column=1, 
                   end_row=current_row + 3, end_column=len(headers))
    ws.cell(row=current_row, column=1).alignment = Alignment(wrap_text=True, vertical='top')
    ws.cell(row=current_row, column=1).font = Font(size=9, italic=True)

    # CRITICAL: Set print settings for PDF conversion
    ws.page_setup.orientation = 'landscape'
    ws.page_setup.paperSize = ws.PAPERSIZE_LETTER
    ws.page_margins = PageMargins(left=0.25, right=0.25, top=0.5, bottom=0.5)
    ws.sheet_properties.pageSetUpPr.fitToPage = True
    ws.page_setup.fitToWidth = 1  # Fit all columns on 1 page
    ws.page_setup.fitToHeight = 0  # As many rows as needed
    ws.print_area = f'A1:I{current_row + 3}'

    return wb

# =============================================================================
# MAIN FUNCTION
# =============================================================================

def process_inventory(input_file, date_folder, freight_rates_file, pallet_counts_file, output_dir):
    """Main processing function."""
    
    print(f"Loading raw inventory from: {input_file}")
    df = load_raw_inventory(input_file)
    print(f"  Loaded {len(df)} items from {df['warehouse_code'].nunique()} warehouses")
    
    print(f"Loading freight rates from: {freight_rates_file}")
    freight_rates = load_freight_rates(freight_rates_file)
    
    print(f"Loading pallet counts from: {pallet_counts_file}")
    pallet_counts = load_pallet_counts(pallet_counts_file)
    print(f"  {len(pallet_counts)} items in pallet count reference")
    
    # Parse date for filenames
    date_str = date_folder.replace('-', '')
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    # Generate regional sheets
    for region in REGIONS:
        print(f"\nGenerating {region} price sheet...")
        
        wb = create_price_sheet(df, region, freight_rates, pallet_counts, date_str)
        
        # Save Excel
        excel_path = os.path.join(output_dir, f"{region}_Fleetwood_{date_str}.xlsx")
        wb.save(excel_path)
        print(f"  Saved: {excel_path}")
        
        # Note: PDF generation would require additional libraries like reportlab
        # For now, user can export to PDF from Excel
    
    # Save pallet counts snapshot
    snapshot_path = os.path.join(output_dir, 'pallet-counts-snapshot.json')
    with open(snapshot_path, 'w') as f:
        json.dump({'items': pallet_counts, 'snapshotDate': date_folder}, f, indent=2)
    print(f"\nSaved pallet counts snapshot: {snapshot_path}")
    
    # Identify items needing pallet count review
    items_without_pallet = []
    for _, row in df.iterrows():
        if not get_pallet_count(row['code'], pallet_counts):
            items_without_pallet.append({
                'code': row['code'],
                'description': row['description'],
                'pack_size': row['pack_size'],
                'brand': row['brand'],
                'spec_sheet_url': row['spec_sheet_url'] if pd.notna(row['spec_sheet_url']) else None
            })
    
    if items_without_pallet:
        print(f"\n⚠️  {len(items_without_pallet)} items need pallet count lookup:")
        for item in items_without_pallet[:10]:
            print(f"    {item['code']}: {item['description'][:40]}")
        if len(items_without_pallet) > 10:
            print(f"    ... and {len(items_without_pallet) - 10} more")
        
        # Save items needing review
        review_path = os.path.join(output_dir, 'needs-pallet-count-review.json')
        with open(review_path, 'w') as f:
            json.dump(items_without_pallet, f, indent=2)
        print(f"  Saved review list: {review_path}")
    
    print("\n✅ Processing complete!")
    return True

# =============================================================================
# CLI ENTRY POINT
# =============================================================================

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Process Fleetwood inventory into regional price sheets')
    parser.add_argument('--input', required=True, help='Path to raw inventory Excel file')
    parser.add_argument('--date-folder', required=True, help='Date folder name (e.g., 1-27-26)')
    parser.add_argument('--freight-rates', required=True, help='Path to freight-rates.json')
    parser.add_argument('--pallet-counts', required=True, help='Path to pallet-counts.json master')
    parser.add_argument('--output-dir', required=True, help='Output directory for generated files')
    
    args = parser.parse_args()
    
    process_inventory(
        args.input,
        args.date_folder,
        args.freight_rates,
        args.pallet_counts,
        args.output_dir
    )
