#!/usr/bin/env python3
"""
GoShip LTL Quote Request Script

Requests freight quotes from GoShip's GraphQL API.
Requires GOSHIP_API_KEY environment variable.

Usage:
    python3 request_quote.py --origin-zip 19440 --dest-zip 30066 \
        --pickup-date 2026-01-26 --quantity 10 --weight 15000 \
        --freight-class CLASS_70 --description "Pork Lard"
"""

import argparse
import json
import os
import sys
from datetime import datetime, timedelta
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

API_ENDPOINT = "https://nautilus.goship.com/broker/graphql"

# Default pallet dimensions (inches)
DEFAULT_LENGTH = 48
DEFAULT_WIDTH = 40
DEFAULT_HEIGHT = 48


def get_api_key():
    """Get API key from environment variable."""
    key = os.environ.get("GOSHIP_API_KEY")
    if not key:
        print("ERROR: GOSHIP_API_KEY environment variable not set.")
        print("\nTo set up:")
        print("1. Create account at https://quotes.goship.com/sign-up")
        print("2. Generate API key at https://quotes.goship.com/apikeys")
        print("3. Set environment variable:")
        print('   export GOSHIP_API_KEY="your-key-here"')
        sys.exit(1)
    return key


def build_query(args):
    """Build GraphQL query for LTL quote request."""
    
    # Calculate per-pallet weight if total weight provided
    weight_per_unit = args.weight // args.quantity if args.quantity > 0 else args.weight
    
    query = """
    query {
      requestLTLQuote(rfq: {
        origin: {
          postalCode: "%s"
          addressType: %s
        }
        destination: {
          postalCode: "%s"
          addressType: %s
        }
        pickupDate: "%s"
        items: [{
          quantity: %d
          packaging: %s
          sizeUoM: in
          length: %d
          width: %d
          height: %d
          weightUoM: lbs
          weight: %d
          freightClass: %s
          value: %.2f
          itemCondition: NEW
          stackable: %s
          hazardous: %s
          description: "%s"
          pieces: %d
          country: USA
        }]
      }) {
        id
        cost
        deliveryDate
        carrier {
          id
          name
        }
      }
    }
    """ % (
        args.origin_zip,
        args.origin_type,
        args.dest_zip,
        args.dest_type,
        args.pickup_date,
        args.quantity,
        args.packaging,
        args.length,
        args.width,
        args.height,
        weight_per_unit,
        args.freight_class,
        args.value,
        "true" if args.stackable else "false",
        "true" if args.hazardous else "false",
        args.description.replace('"', '\\"'),
        args.quantity
    )
    
    return query


def request_quote(query, api_key):
    """Send GraphQL request to GoShip API."""
    
    headers = {
        "Content-Type": "application/json",
        "X-GoShip-API-Key": api_key
    }
    
    data = json.dumps({"query": query}).encode("utf-8")
    
    request = Request(API_ENDPOINT, data=data, headers=headers, method="POST")
    
    try:
        with urlopen(request, timeout=30) as response:
            result = json.loads(response.read().decode("utf-8"))
            return result
    except HTTPError as e:
        error_body = e.read().decode("utf-8") if e.fp else ""
        print(f"HTTP Error {e.code}: {e.reason}")
        print(f"Response: {error_body}")
        sys.exit(1)
    except URLError as e:
        print(f"URL Error: {e.reason}")
        sys.exit(1)


def format_results(response, args):
    """Format and display quote results."""
    
    if "errors" in response:
        print("\n❌ API Errors:")
        for error in response["errors"]:
            print(f"  - {error.get('message', error)}")
        return
    
    quotes = response.get("data", {}).get("requestLTLQuote", [])
    
    if not quotes:
        print("\n⚠️  No quotes available for this shipment.")
        print("This could be due to:")
        print("  - Service not available to destination")
        print("  - Weight/size restrictions")
        print("  - Invalid freight class")
        return
    
    print("\n" + "=" * 60)
    print("🚚 LTL FREIGHT QUOTES")
    print("=" * 60)
    print(f"Route: {args.origin_zip} → {args.dest_zip}")
    print(f"Pickup: {args.pickup_date}")
    print(f"Load: {args.quantity} {args.packaging}(s), {args.weight} lbs")
    print(f"Commodity: {args.description}")
    print(f"Class: {args.freight_class}")
    print("-" * 60)
    
    # Sort by cost
    quotes_sorted = sorted(quotes, key=lambda x: x.get("cost", float("inf")))
    
    for i, quote in enumerate(quotes_sorted, 1):
        carrier = quote.get("carrier", {})
        cost = quote.get("cost", 0)
        delivery = quote.get("delivery_date") or quote.get("deliveryDate", "N/A")
        quote_id = quote.get("id", "N/A")
        
        print(f"\n#{i} {carrier.get('name', 'Unknown Carrier')}")
        print(f"   💰 Cost: ${cost:,.2f}")
        print(f"   📅 Delivery: {delivery}")
        print(f"   🔑 Quote ID: {quote_id}")
    
    print("\n" + "=" * 60)
    print(f"Total options: {len(quotes)}")
    
    # Output JSON for programmatic use
    if args.json_output:
        print("\n--- JSON Output ---")
        print(json.dumps(quotes_sorted, indent=2))


def get_next_business_day():
    """Get next business day (Mon-Fri)."""
    today = datetime.now()
    days_ahead = 1
    next_day = today + timedelta(days=days_ahead)
    
    # Skip weekends
    while next_day.weekday() >= 5:  # 5=Saturday, 6=Sunday
        days_ahead += 1
        next_day = today + timedelta(days=days_ahead)
    
    return next_day.strftime("%Y-%m-%d")


def main():
    parser = argparse.ArgumentParser(
        description="Request LTL freight quotes from GoShip API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic quote request
  python3 request_quote.py --origin-zip 19440 --dest-zip 30066 \\
      --quantity 10 --weight 15000 --freight-class CLASS_70 \\
      --description "Pork Lard"

  # With specific pickup date
  python3 request_quote.py --origin-zip 19512 --dest-zip 30066 \\
      --pickup-date 2026-01-22 --quantity 3 --weight 6000 \\
      --freight-class CLASS_85 --description "Frozen Cooked Chicken"
        """
    )
    
    # Required arguments
    parser.add_argument("--origin-zip", required=True, help="Origin postal code (5 digits)")
    parser.add_argument("--dest-zip", required=True, help="Destination postal code (5 digits)")
    parser.add_argument("--quantity", type=int, required=True, help="Number of units (pallets)")
    parser.add_argument("--weight", type=int, required=True, help="Total weight in pounds")
    parser.add_argument("--freight-class", required=True, 
                       help="Freight class (e.g., CLASS_70, CLASS_85)")
    parser.add_argument("--description", required=True, help="Commodity description")
    
    # Optional arguments
    parser.add_argument("--pickup-date", default=get_next_business_day(),
                       help="Pickup date (YYYY-MM-DD), default: next business day")
    parser.add_argument("--packaging", default="PALLET",
                       choices=["PALLET", "CRATE", "BOX", "BUNDLE", "DRUM", "ROLL", "BAGS"],
                       help="Packaging type (default: PALLET)")
    parser.add_argument("--length", type=int, default=DEFAULT_LENGTH,
                       help=f"Length in inches (default: {DEFAULT_LENGTH})")
    parser.add_argument("--width", type=int, default=DEFAULT_WIDTH,
                       help=f"Width in inches (default: {DEFAULT_WIDTH})")
    parser.add_argument("--height", type=int, default=DEFAULT_HEIGHT,
                       help=f"Height in inches (default: {DEFAULT_HEIGHT})")
    parser.add_argument("--origin-type", default="BUSINESS_W_DOCK",
                       choices=["RESIDENTIAL", "BUSINESS", "BUSINESS_W_DOCK"],
                       help="Origin address type (default: BUSINESS_W_DOCK)")
    parser.add_argument("--dest-type", default="BUSINESS_W_DOCK",
                       choices=["RESIDENTIAL", "BUSINESS", "BUSINESS_W_DOCK"],
                       help="Destination address type (default: BUSINESS_W_DOCK)")
    parser.add_argument("--value", type=float, default=1000.0,
                       help="Declared value in USD (default: 1000)")
    parser.add_argument("--stackable", action="store_true",
                       help="Items are stackable")
    parser.add_argument("--hazardous", action="store_true",
                       help="Items are hazardous")
    parser.add_argument("--json-output", action="store_true",
                       help="Also output raw JSON")
    
    args = parser.parse_args()
    
    # Validate inputs
    if len(args.origin_zip) != 5 or not args.origin_zip.isdigit():
        print(f"ERROR: Invalid origin zip code: {args.origin_zip}")
        sys.exit(1)
    
    if len(args.dest_zip) != 5 or not args.dest_zip.isdigit():
        print(f"ERROR: Invalid destination zip code: {args.dest_zip}")
        sys.exit(1)
    
    # Validate freight class format
    valid_classes = [
        "CLASS_50", "CLASS_55", "CLASS_60", "CLASS_65", "CLASS_70",
        "CLASS_77_5", "CLASS_85", "CLASS_92_5", "CLASS_100", "CLASS_110",
        "CLASS_125", "CLASS_150", "CLASS_175", "CLASS_200", "CLASS_250",
        "CLASS_300", "CLASS_400", "CLASS_500"
    ]
    if args.freight_class not in valid_classes:
        print(f"ERROR: Invalid freight class: {args.freight_class}")
        print(f"Valid classes: {', '.join(valid_classes)}")
        sys.exit(1)
    
    # Get API key
    api_key = get_api_key()
    
    # Build and execute query
    print(f"Requesting quotes from GoShip API...")
    query = build_query(args)
    response = request_quote(query, api_key)
    
    # Display results
    format_results(response, args)


if __name__ == "__main__":
    main()
