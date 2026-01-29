#!/usr/bin/env python3
"""
PDF Preview Utility

Converts PDF pages to PNG images for visual verification.

Usage:
    python preview_pdf.py output.pdf                    # Preview first page
    python preview_pdf.py output.pdf --page 2           # Preview specific page
    python preview_pdf.py output.pdf --all              # Preview all pages
    python preview_pdf.py output.pdf --zoom 3.0         # Higher resolution
"""

import argparse
import os
import sys

try:
    import fitz  # PyMuPDF
except ImportError:
    print("Error: PyMuPDF not installed. Run: pip install PyMuPDF")
    sys.exit(1)


def preview_pdf(pdf_path, output_dir=None, pages=None, zoom=2.5):
    """
    Convert PDF pages to PNG images.

    Args:
        pdf_path: Path to PDF file
        output_dir: Output directory (defaults to same as PDF)
        pages: List of page numbers (0-indexed) or None for first page
        zoom: Zoom factor for resolution (2.5 = 2.5x)

    Returns:
        List of output PNG paths
    """
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    if output_dir is None:
        output_dir = os.path.dirname(pdf_path) or '.'

    os.makedirs(output_dir, exist_ok=True)

    doc = fitz.open(pdf_path)
    total_pages = len(doc)
    base_name = os.path.splitext(os.path.basename(pdf_path))[0]

    # Determine which pages to render
    if pages is None:
        pages = [0]  # Default to first page
    elif pages == 'all':
        pages = list(range(total_pages))

    output_paths = []
    for page_num in pages:
        if page_num >= total_pages:
            print(f"Warning: Page {page_num + 1} doesn't exist (total: {total_pages})")
            continue

        page = doc[page_num]
        pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom))

        if len(pages) == 1:
            output_path = os.path.join(output_dir, f"{base_name}_preview.png")
        else:
            output_path = os.path.join(output_dir, f"{base_name}_page{page_num + 1}.png")

        pix.save(output_path)
        output_paths.append(output_path)
        print(f"Created: {output_path}")

    doc.close()
    return output_paths, total_pages


def main():
    parser = argparse.ArgumentParser(
        description='Convert PDF pages to PNG for visual verification',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s report.pdf                    # Preview first page
  %(prog)s report.pdf --page 2           # Preview page 2
  %(prog)s report.pdf --all              # Preview all pages
  %(prog)s report.pdf --zoom 3.0         # Higher resolution
  %(prog)s report.pdf -o ./previews      # Output to specific directory
        """
    )

    parser.add_argument('pdf', help='Input PDF file')
    parser.add_argument('-o', '--output-dir', help='Output directory for PNG files')
    parser.add_argument('-p', '--page', type=int, help='Specific page number (1-indexed)')
    parser.add_argument('-a', '--all', action='store_true', help='Preview all pages')
    parser.add_argument('-z', '--zoom', type=float, default=2.5,
                        help='Zoom factor for resolution (default: 2.5)')

    args = parser.parse_args()

    try:
        if args.all:
            pages = 'all'
        elif args.page:
            pages = [args.page - 1]  # Convert to 0-indexed
        else:
            pages = None  # Default to first page

        output_paths, total_pages = preview_pdf(
            args.pdf,
            output_dir=args.output_dir,
            pages=pages,
            zoom=args.zoom
        )

        print(f"\nPDF has {total_pages} page(s)")
        print(f"Created {len(output_paths)} preview(s)")

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
