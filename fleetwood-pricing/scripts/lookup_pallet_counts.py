#!/usr/bin/env python3
"""
Pallet Count Lookup for Fleetwood Inventory Pricing

Determines cases per pallet for items by:
1. Checking master reference
2. Fetching and parsing spec sheet PDFs (Ti/Hi extraction)
3. Web research for product specifications
4. Flagging items for manual review

Usage:
    python lookup_pallet_counts.py --items <needs-review.json> --master <pallet-counts.json>
"""

import json
import re
import os
from datetime import datetime

# =============================================================================
# TI/HI PARSING
# =============================================================================

def parse_ti_hi(text):
    """
    Extract Ti/Hi from spec sheet text and calculate cases per pallet.
    
    Common formats:
    - "Ti / Hi: 8 x 10 (Ti x Hi)"
    - "Ti/Hi: 8x10"
    - "Pallet Configuration: 8 Ti x 10 Hi"
    - "8 x 10 = 80"
    
    Returns (ti, hi, cases_per_pallet) or (None, None, None)
    """
    if not text:
        return None, None, None
    
    # Normalize text
    text = text.replace('\n', ' ').replace('\r', ' ')
    
    # Pattern 1: "Ti / Hi: 8 x 10" or "Ti/Hi: 8x10"
    match = re.search(r'Ti\s*/?\s*Hi[:\s]+(\d+)\s*[xX×]\s*(\d+)', text, re.IGNORECASE)
    if match:
        ti, hi = int(match.group(1)), int(match.group(2))
        return ti, hi, ti * hi
    
    # Pattern 2: "8 Ti x 10 Hi"
    match = re.search(r'(\d+)\s*Ti\s*[xX×]\s*(\d+)\s*Hi', text, re.IGNORECASE)
    if match:
        ti, hi = int(match.group(1)), int(match.group(2))
        return ti, hi, ti * hi
    
    # Pattern 3: "Pallet: 8 x 10"
    match = re.search(r'Pallet[:\s]+(\d+)\s*[xX×]\s*(\d+)', text, re.IGNORECASE)
    if match:
        ti, hi = int(match.group(1)), int(match.group(2))
        return ti, hi, ti * hi
    
    # Pattern 4: "Cases per Pallet: 80" or "Cases/Pallet: 80"
    match = re.search(r'Cases?\s*/?\s*(?:per\s*)?Pallet[:\s]+(\d+)', text, re.IGNORECASE)
    if match:
        cases = int(match.group(1))
        return None, None, cases
    
    return None, None, None

def extract_text_from_pdf(pdf_path):
    """
    Extract text from PDF file.
    
    NOTE: Requires pdfplumber or PyPDF2 to be installed.
    This is a placeholder - Claude will use appropriate PDF reading tools.
    """
    try:
        import pdfplumber
        with pdfplumber.open(pdf_path) as pdf:
            text = ''
            for page in pdf.pages:
                text += page.extract_text() or ''
            return text
    except ImportError:
        print("Warning: pdfplumber not installed. Install with: pip install pdfplumber")
        return None
    except Exception as e:
        print(f"Error reading PDF: {e}")
        return None

# =============================================================================
# SPEC SHEET URL HANDLING
# =============================================================================

def is_valid_spec_url(url):
    """Check if URL is a valid Fleetwood spec sheet URL."""
    if not url:
        return False
    
    valid_domains = [
        'specff.psce.pw',
        'specff.psee.io', 
        'mfspec.psce.pw'
    ]
    
    return any(domain in str(url) for domain in valid_domains)

def fetch_spec_sheet(url, output_dir='/tmp/spec_sheets'):
    """
    Fetch spec sheet PDF from URL.
    
    Returns path to downloaded PDF or None.
    
    NOTE: This is a placeholder. Claude will use web_fetch or browser
    tools to download spec sheet PDFs.
    """
    if not is_valid_spec_url(url):
        return None
    
    os.makedirs(output_dir, exist_ok=True)
    
    # Extract filename from URL
    filename = url.split('/')[-1] + '.pdf'
    output_path = os.path.join(output_dir, filename)
    
    # Placeholder for actual download
    # Claude will use: requests.get(url) or browser automation
    print(f"  Would fetch: {url}")
    print(f"  Save to: {output_path}")
    
    return None  # Return None until actually downloaded

# =============================================================================
# WEB RESEARCH
# =============================================================================

def generate_search_queries(item):
    """
    Generate search queries for finding product spec sheets.
    """
    brand = item.get('brand', '').strip()
    description = item.get('description', '').strip()
    pack_size = item.get('pack_size', '').strip()
    
    queries = []
    
    # Primary query: exact product
    if brand and description:
        queries.append(f'"{brand}" "{description}" spec sheet Ti Hi')
        queries.append(f'"{brand}" "{description}" pallet configuration')
    
    # Secondary: brand + pack size
    if brand and pack_size:
        queries.append(f'"{brand}" {pack_size} cases per pallet')
    
    # Tertiary: generic product type
    if description:
        # Extract product type keywords
        product_keywords = []
        for word in ['chicken', 'turkey', 'beef', 'pork', 'tender', 'wing', 'nugget', 'patty']:
            if word in description.lower():
                product_keywords.append(word)
        
        if product_keywords and pack_size:
            queries.append(f'{" ".join(product_keywords)} {pack_size} pallet count')
    
    return queries

# =============================================================================
# ESTIMATION LOGIC
# =============================================================================

def estimate_pallet_count(pack_size, description=''):
    """
    Estimate pallet count based on pack size and product type.
    
    This is used as a last resort when no spec sheet or research
    can determine the actual count.
    
    Returns (estimate, confidence, reasoning)
    """
    if not pack_size:
        return None, None, "No pack size provided"
    
    pack_str = str(pack_size).upper()
    
    # Parse case weight
    case_weight = None
    
    # N/N LB format
    match = re.match(r'(\d+)\s*/\s*(\d+\.?\d*)\s*LB', pack_str)
    if match:
        case_weight = float(match.group(1)) * float(match.group(2))
    
    # N LB format
    if not case_weight:
        match = re.match(r'^(\d+\.?\d*)\s*LB', pack_str)
        if match:
            case_weight = float(match.group(1))
    
    if not case_weight:
        return None, None, f"Could not parse pack size: {pack_size}"
    
    # Estimate based on case weight
    # General rule: heavier cases = fewer per pallet
    if case_weight <= 10:
        estimate = 140
        confidence = 'medium'
    elif case_weight <= 15:
        estimate = 120
        confidence = 'medium'
    elif case_weight <= 20:
        estimate = 100
        confidence = 'medium'
    elif case_weight <= 30:
        estimate = 70
        confidence = 'low'
    elif case_weight <= 40:
        estimate = 56
        confidence = 'low'
    else:
        estimate = 42
        confidence = 'low'
    
    reasoning = f"Estimated from {case_weight}lb case weight using standard pallet configurations"
    
    return estimate, confidence, reasoning

# =============================================================================
# MASTER REFERENCE MANAGEMENT
# =============================================================================

def load_master_reference(filepath):
    """Load master pallet counts reference."""
    if not os.path.exists(filepath):
        return {'metadata': {}, 'items': {}, 'needsReview': []}
    
    with open(filepath, 'r') as f:
        return json.load(f)

def save_master_reference(data, filepath):
    """Save master pallet counts reference."""
    data['metadata']['lastUpdated'] = datetime.now().strftime('%Y-%m-%d')
    data['metadata']['totalItems'] = len(data.get('items', {}))
    
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2)
    
    print(f"Saved master reference: {filepath}")

def add_pallet_count(master, item_code, cases_per_pallet, source, **kwargs):
    """Add or update pallet count in master reference."""
    master['items'][str(item_code)] = {
        'casesPerPallet': cases_per_pallet,
        'source': source,
        'dateAdded': datetime.now().strftime('%Y-%m-%d'),
        **kwargs
    }

# =============================================================================
# LOOKUP WORKFLOW
# =============================================================================

def lookup_pallet_count(item, master):
    """
    Complete pallet count lookup for a single item.
    
    Returns dict with:
    - casesPerPallet: int or None
    - source: str (master, spec_sheet, web_research, estimated, needs_review)
    - confidence: str (high, medium, low)
    - notes: str
    """
    item_code = str(item.get('code', ''))
    
    # Step 1: Check master reference
    if item_code in master.get('items', {}):
        existing = master['items'][item_code]
        return {
            'casesPerPallet': existing.get('casesPerPallet'),
            'source': 'master',
            'confidence': 'high',
            'notes': f"From master reference ({existing.get('source', 'unknown')})"
        }
    
    # Step 2: Check for spec sheet URL
    spec_url = item.get('spec_sheet_url')
    if is_valid_spec_url(spec_url):
        # NOTE: Claude will actually fetch and parse the PDF
        # This is a placeholder showing the workflow
        return {
            'casesPerPallet': None,
            'source': 'needs_spec_fetch',
            'confidence': None,
            'notes': f"Spec sheet available: {spec_url}",
            'specUrl': spec_url,
            'action': 'Fetch PDF and extract Ti/Hi'
        }
    
    # Step 3: Generate search queries for web research
    queries = generate_search_queries(item)
    if queries:
        return {
            'casesPerPallet': None,
            'source': 'needs_web_research',
            'confidence': None,
            'notes': 'No spec sheet URL, web research needed',
            'searchQueries': queries,
            'action': 'Search web for product specifications'
        }
    
    # Step 4: Attempt estimation
    estimate, confidence, reasoning = estimate_pallet_count(
        item.get('pack_size'), 
        item.get('description')
    )
    
    if estimate:
        return {
            'casesPerPallet': estimate,
            'source': 'estimated',
            'confidence': confidence,
            'notes': reasoning,
            'action': 'Consider verifying this estimate'
        }
    
    # Step 5: Flag for manual review
    return {
        'casesPerPallet': None,
        'source': 'needs_review',
        'confidence': None,
        'notes': 'Could not determine pallet count',
        'action': 'Manual lookup required'
    }

def process_items_needing_review(items_file, master_file, output_file=None):
    """
    Process a list of items needing pallet count review.
    
    Creates a detailed report with lookup results and recommended actions.
    """
    with open(items_file, 'r') as f:
        items = json.load(f)
    
    master = load_master_reference(master_file)
    
    results = {
        'summary': {
            'total': len(items),
            'found_in_master': 0,
            'needs_spec_fetch': 0,
            'needs_web_research': 0,
            'estimated': 0,
            'needs_manual_review': 0
        },
        'items': []
    }
    
    for item in items:
        lookup_result = lookup_pallet_count(item, master)
        
        # Update summary
        source = lookup_result.get('source', 'unknown')
        if source == 'master':
            results['summary']['found_in_master'] += 1
        elif source == 'needs_spec_fetch':
            results['summary']['needs_spec_fetch'] += 1
        elif source == 'needs_web_research':
            results['summary']['needs_web_research'] += 1
        elif source == 'estimated':
            results['summary']['estimated'] += 1
        else:
            results['summary']['needs_manual_review'] += 1
        
        results['items'].append({
            'item': item,
            'lookup': lookup_result
        })
    
    # Print summary
    print("\n" + "=" * 60)
    print("PALLET COUNT LOOKUP RESULTS")
    print("=" * 60)
    print(f"\nTotal items: {results['summary']['total']}")
    print(f"  Found in master:      {results['summary']['found_in_master']}")
    print(f"  Need spec fetch:      {results['summary']['needs_spec_fetch']}")
    print(f"  Need web research:    {results['summary']['needs_web_research']}")
    print(f"  Estimated:            {results['summary']['estimated']}")
    print(f"  Need manual review:   {results['summary']['needs_manual_review']}")
    
    # Save results
    if output_file:
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"\nSaved detailed results: {output_file}")
    
    return results

# =============================================================================
# CLI ENTRY POINT
# =============================================================================

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Lookup pallet counts for Fleetwood inventory items')
    parser.add_argument('--items', required=True, help='JSON file with items needing review')
    parser.add_argument('--master', required=True, help='Path to master pallet-counts.json')
    parser.add_argument('--output', help='Output file for results')
    
    args = parser.parse_args()
    
    process_items_needing_review(
        args.items,
        args.master,
        args.output
    )
