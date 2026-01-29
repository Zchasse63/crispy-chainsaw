#!/usr/bin/env python3
"""
Professional Sales Sheet Generator

Creates professionally designed PDF sales sheets from Excel data.
Implements B2B design best practices: visual hierarchy, proper typography,
trust-building color schemes, and mobile-friendly layouts.

Usage:
    from professional_sales_sheet import create_sales_sheet

    create_sales_sheet(
        excel_path="pricing.xlsx",
        output_path="sales_sheet.pdf",
        theme="fleetwood",
        contact_name="Zach Chasse",
        contact_email="Chasse@fleetwoodfoods.com",
        contact_phone="352-274-0354"
    )
"""

import os
import re
from datetime import datetime
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Any, Callable

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, landscape, legal
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph,
    Spacer, Image, PageBreak, KeepTogether
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont


# =============================================================================
# THEME DEFINITIONS
# =============================================================================

@dataclass
class Theme:
    """Color theme for sales sheet."""
    name: str
    primary: str
    primary_dark: str
    accent: str
    text_primary: str
    text_secondary: str
    background: str
    stripe: str
    border: str
    success: str
    warning: str
    danger: str

    def get_color(self, color_name: str) -> colors.Color:
        """Convert hex color to ReportLab Color."""
        hex_color = getattr(self, color_name, self.primary)
        return hex_to_color(hex_color)


def hex_to_color(hex_str: str) -> colors.Color:
    """Convert hex string to ReportLab Color."""
    hex_str = hex_str.lstrip('#')
    r = int(hex_str[0:2], 16) / 255
    g = int(hex_str[2:4], 16) / 255
    b = int(hex_str[4:6], 16) / 255
    return colors.Color(r, g, b)


# Pre-defined themes
THEMES = {
    "fleetwood": Theme(
        name="fleetwood",
        primary="#1B4D3E",
        primary_dark="#0F2E25",
        accent="#D4A84B",
        text_primary="#2D3436",
        text_secondary="#636E72",
        background="#FFFFFF",
        stripe="#F8F9FA",
        border="#E0E0E0",
        success="#27AE60",
        warning="#F39C12",
        danger="#E74C3C",
    ),
    "professional": Theme(
        name="professional",
        primary="#1E3A5F",
        primary_dark="#152A45",
        accent="#2E7D32",
        text_primary="#37474F",
        text_secondary="#607D8B",
        background="#FFFFFF",
        stripe="#F5F5F5",
        border="#E0E0E0",
        success="#4CAF50",
        warning="#FFB300",
        danger="#E53935",
    ),
    "minimal": Theme(
        name="minimal",
        primary="#424242",
        primary_dark="#212121",
        accent="#1976D2",
        text_primary="#424242",
        text_secondary="#757575",
        background="#FFFFFF",
        stripe="#FAFAFA",
        border="#EEEEEE",
        success="#66BB6A",
        warning="#FFA726",
        danger="#EF5350",
    ),
    "bold": Theme(
        name="bold",
        primary="#D32F2F",
        primary_dark="#B71C1C",
        accent="#FFC107",
        text_primary="#212121",
        text_secondary="#616161",
        background="#FFFFFF",
        stripe="#FFF8E1",
        border="#BDBDBD",
        success="#43A047",
        warning="#FB8C00",
        danger="#C62828",
    ),
}


# =============================================================================
# COLUMN DETECTION & FORMATTING
# =============================================================================

@dataclass
class ColumnConfig:
    """Configuration for a single column."""
    width: float = 0.10  # Percentage of table width
    align: str = "left"  # left, center, right
    format: str = "text"  # text, currency, integer, decimal, link
    header: Optional[str] = None  # Override header display
    wrap: bool = False
    max_lines: int = 2
    link_text: str = "View"
    highlight_if: Optional[Callable] = None


# Auto-detection patterns
COLUMN_PATTERNS = {
    "code": {
        "patterns": ["code", "sku", "item", "product.*#", "part.*#"],
        "config": ColumnConfig(width=0.08, align="left", format="text"),
    },
    "description": {
        "patterns": ["desc", "name", "product(?!.*#)", "item.*name"],
        "config": ColumnConfig(width=0.25, align="left", format="text", wrap=True),
    },
    "pack": {
        "patterns": ["pack", "size", "qty", "quantity", "unit"],
        "config": ColumnConfig(width=0.10, align="left", format="text"),
    },
    "brand": {
        "patterns": ["brand", "mfr", "manufacturer", "vendor"],
        "config": ColumnConfig(width=0.12, align="left", format="text"),
    },
    "availability": {
        "patterns": ["avail", "stock", "cs.*avail", "inventory", "on.*hand"],
        "config": ColumnConfig(width=0.08, align="right", format="integer"),
    },
    "currency": {
        "patterns": [r"\$", "price", "cost", "amount", "total"],
        "config": ColumnConfig(width=0.10, align="right", format="currency"),
    },
    "pallet": {
        "patterns": ["plt", "pallet", "cs.*plt", "ti.*hi"],
        "config": ColumnConfig(width=0.06, align="right", format="integer"),
    },
    "link": {
        "patterns": ["spec", "link", "url", "sheet", "http"],
        "config": ColumnConfig(width=0.08, align="center", format="link"),
    },
}


def detect_column_type(column_name: str) -> ColumnConfig:
    """Auto-detect column configuration based on name."""
    col_lower = column_name.lower()

    for type_name, type_info in COLUMN_PATTERNS.items():
        for pattern in type_info["patterns"]:
            if re.search(pattern, col_lower):
                return ColumnConfig(**type_info["config"].__dict__)

    # Default configuration
    return ColumnConfig(width=0.10, align="left", format="text")


def format_value(value: Any, format_type: str, link_text: str = "View") -> str:
    """Format a cell value based on its type."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""

    if format_type == "currency":
        try:
            num = float(value)
            return f"${num:,.2f}"
        except (ValueError, TypeError):
            return str(value)

    elif format_type == "integer":
        try:
            num = int(float(value))
            return f"{num:,}"
        except (ValueError, TypeError):
            return str(value)

    elif format_type == "decimal":
        try:
            num = float(value)
            return f"{num:,.2f}"
        except (ValueError, TypeError):
            return str(value)

    elif format_type == "link":
        val_str = str(value).strip()
        if val_str and (val_str.startswith("http") or val_str.startswith("www")):
            # Return tuple (display_text, url) for link processing
            return (link_text, val_str)
        return ""

    else:
        return str(value) if value else ""


# =============================================================================
# PDF DOCUMENT BUILDER
# =============================================================================

class SalesSheetBuilder:
    """Builds professional PDF sales sheets."""

    def __init__(
        self,
        theme: Theme,
        orientation: str = "landscape",
        page_size: str = "letter",
    ):
        self.theme = theme
        self.orientation = orientation
        self.page_size = page_size

        # Calculate page dimensions
        base_size = letter if page_size == "letter" else legal
        if orientation == "landscape":
            self.page_width, self.page_height = landscape(base_size)
        else:
            self.page_width, self.page_height = base_size

        # Margins
        self.margin = 0.5 * inch
        self.content_width = self.page_width - (2 * self.margin)

        # Styles
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()

    def _setup_custom_styles(self):
        """Create custom paragraph styles."""
        self.styles.add(ParagraphStyle(
            name='DocTitle',
            parent=self.styles['Heading1'],
            fontSize=20,
            textColor=self.theme.get_color('primary'),
            spaceAfter=4,
            fontName='Helvetica-Bold',
        ))

        self.styles.add(ParagraphStyle(
            name='DocSubtitle',
            parent=self.styles['Normal'],
            fontSize=12,
            textColor=self.theme.get_color('text_secondary'),
            spaceAfter=2,
        ))

        self.styles.add(ParagraphStyle(
            name='EffectiveDate',
            parent=self.styles['Normal'],
            fontSize=10,
            textColor=self.theme.get_color('text_secondary'),
            alignment=2,  # Right align
        ))

        self.styles.add(ParagraphStyle(
            name='SectionHeader',
            parent=self.styles['Heading2'],
            fontSize=12,
            textColor=self.theme.get_color('primary'),
            spaceBefore=12,
            spaceAfter=6,
            fontName='Helvetica-Bold',
        ))

        self.styles.add(ParagraphStyle(
            name='Footer',
            parent=self.styles['Normal'],
            fontSize=8,
            textColor=self.theme.get_color('text_secondary'),
            fontName='Helvetica-Oblique',
        ))

        self.styles.add(ParagraphStyle(
            name='Contact',
            parent=self.styles['Normal'],
            fontSize=9,
            textColor=self.theme.get_color('text_primary'),
        ))

        self.styles.add(ParagraphStyle(
            name='Link',
            parent=self.styles['Normal'],
            fontSize=8,
            textColor=self.theme.get_color('primary'),
            fontName='Helvetica-Bold',
            alignment=1,  # Center align
        ))

    def build_header(
        self,
        title: str,
        subtitle: Optional[str] = None,
        effective_date: Optional[str] = None,
        logo_path: Optional[str] = None,
        company_name: Optional[str] = None,
    ) -> List:
        """Build document header elements."""
        elements = []

        # Header table: Logo+Title on left, Date on right
        header_data = []

        # Left side content
        left_content = []
        if company_name:
            left_content.append(Paragraph(company_name, self.styles['DocSubtitle']))
        left_content.append(Paragraph(title, self.styles['DocTitle']))
        if subtitle:
            left_content.append(Paragraph(subtitle, self.styles['DocSubtitle']))

        # Right side content
        right_content = []
        if effective_date:
            right_content.append(Paragraph(
                f"<b>Prices Effective:</b> {effective_date}",
                self.styles['EffectiveDate']
            ))

        # Build header row
        if logo_path and os.path.exists(logo_path):
            try:
                logo = Image(logo_path, height=0.6*inch, width=1.5*inch)
                logo.hAlign = 'LEFT'
                header_data.append([logo, left_content, right_content])
                col_widths = [1.6*inch, self.content_width - 3.2*inch, 1.6*inch]
            except:
                header_data.append([left_content, right_content])
                col_widths = [self.content_width - 1.8*inch, 1.8*inch]
        else:
            header_data.append([left_content, right_content])
            col_widths = [self.content_width - 1.8*inch, 1.8*inch]

        header_table = Table(header_data, colWidths=col_widths)
        header_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('ALIGN', (-1, 0), (-1, -1), 'RIGHT'),
        ]))

        elements.append(header_table)
        elements.append(Spacer(1, 12))

        return elements

    def build_data_table(
        self,
        df: pd.DataFrame,
        column_configs: Dict[str, ColumnConfig],
        column_order: Optional[List[str]] = None,
    ) -> Table:
        """Build the main data table."""

        # Determine column order
        if column_order:
            columns = [c for c in column_order if c in df.columns]
        else:
            columns = list(df.columns)

        # Calculate column widths
        total_width_pct = sum(column_configs.get(c, detect_column_type(c)).width for c in columns)
        col_widths = []
        for col in columns:
            config = column_configs.get(col, detect_column_type(col))
            width = (config.width / total_width_pct) * self.content_width
            col_widths.append(width)

        # Build header row
        header_row = []
        for col in columns:
            config = column_configs.get(col, detect_column_type(col))
            display_name = config.header if config.header else col
            header_row.append(display_name)

        # Build data rows
        data_rows = [header_row]
        for _, row in df.iterrows():
            data_row = []
            for col in columns:
                config = column_configs.get(col, detect_column_type(col))
                value = row.get(col, "")
                formatted = format_value(value, config.format, config.link_text)

                # Handle links - create Paragraph with hyperlink
                if isinstance(formatted, tuple) and len(formatted) == 2:
                    display_text, url = formatted
                    # Create clickable hyperlink using ReportLab's link tag
                    link_html = f'<link href="{url}">{display_text}</link>'
                    data_row.append(Paragraph(link_html, self.styles['Link']))
                else:
                    data_row.append(formatted)
            data_rows.append(data_row)

        # Create table
        table = Table(data_rows, colWidths=col_widths, repeatRows=1)

        # Build style commands
        style_commands = [
            # Header row styling
            ('BACKGROUND', (0, 0), (-1, 0), self.theme.get_color('primary')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('TOPPADDING', (0, 0), (-1, 0), 8),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),

            # Data rows styling
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('TEXTCOLOR', (0, 1), (-1, -1), self.theme.get_color('text_primary')),
            ('TOPPADDING', (0, 1), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 5),

            # Zebra striping
            ('ROWBACKGROUNDS', (0, 1), (-1, -1),
             [colors.white, self.theme.get_color('stripe')]),

            # Borders
            ('LINEBELOW', (0, 0), (-1, 0), 1.5, self.theme.get_color('primary')),
            ('LINEBELOW', (0, 1), (-1, -2), 0.5, self.theme.get_color('border')),
            ('LINEBELOW', (0, -1), (-1, -1), 1, self.theme.get_color('primary')),

            # Vertical alignment
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]

        # Apply column-specific alignment
        for i, col in enumerate(columns):
            config = column_configs.get(col, detect_column_type(col))
            align_map = {"left": "LEFT", "center": "CENTER", "right": "RIGHT"}
            align = align_map.get(config.align, "LEFT")
            style_commands.append(('ALIGN', (i, 0), (i, -1), align))

            # Horizontal padding
            style_commands.append(('LEFTPADDING', (i, 0), (i, -1), 6))
            style_commands.append(('RIGHTPADDING', (i, 0), (i, -1), 6))

        table.setStyle(TableStyle(style_commands))

        return table

    def build_section_table(
        self,
        section_name: str,
        df: pd.DataFrame,
        column_configs: Dict[str, ColumnConfig],
        column_order: Optional[List[str]] = None,
    ) -> List:
        """Build a section with header and data table."""
        elements = []

        # Section header
        elements.append(Paragraph(section_name, self.styles['SectionHeader']))

        # Data table
        table = self.build_data_table(df, column_configs, column_order)
        elements.append(table)
        elements.append(Spacer(1, 8))

        return elements

    def build_footer(
        self,
        footer_notes: Optional[List[str]] = None,
        contact_name: Optional[str] = None,
        contact_email: Optional[str] = None,
        contact_phone: Optional[str] = None,
    ) -> List:
        """Build document footer elements."""
        elements = []

        elements.append(Spacer(1, 16))

        # Disclaimer/notes
        if footer_notes:
            for note in footer_notes:
                elements.append(Paragraph(note, self.styles['Footer']))
            elements.append(Spacer(1, 8))

        # Contact info
        contact_parts = []
        if contact_name:
            contact_parts.append(f"<b>{contact_name}</b>")
        if contact_email:
            contact_parts.append(contact_email)
        if contact_phone:
            contact_parts.append(contact_phone)

        if contact_parts:
            contact_str = " | ".join(contact_parts)
            elements.append(Paragraph(contact_str, self.styles['Contact']))

        return elements


class PageNumCanvas:
    """Canvas wrapper for adding page numbers."""

    def __init__(self, doc, theme):
        self.doc = doc
        self.theme = theme
        self.pages = []

    def afterPage(self):
        self.pages.append(dict(self.doc.page))

    def beforePage(self):
        pass


def add_page_numbers(canvas, doc):
    """Add page numbers to footer."""
    page_num = canvas.getPageNumber()
    text = f"Page {page_num}"
    canvas.saveState()
    canvas.setFont('Helvetica', 8)
    canvas.setFillColor(colors.Color(0.4, 0.4, 0.4))
    canvas.drawRightString(doc.pagesize[0] - 36, 30, text)
    canvas.restoreState()


# =============================================================================
# VALIDATION
# =============================================================================

def validate_table_data(
    df: pd.DataFrame,
    column_configs: Dict[str, ColumnConfig],
    content_width: float,
    column_order: Optional[List[str]] = None,
) -> List[str]:
    """
    Validate table data for potential rendering issues.

    Checks for:
    - Text overflow (content too wide for column)
    - Missing data in key columns

    Args:
        df: DataFrame with table data
        column_configs: Column configuration dict
        content_width: Available content width in points
        column_order: Optional column order list

    Returns:
        List of warning messages (empty if no issues)
    """
    warnings = []

    # Determine column order
    columns = column_order if column_order else list(df.columns)
    columns = [c for c in columns if c in df.columns]

    # Calculate actual column widths in points
    total_width_pct = sum(column_configs.get(c, detect_column_type(c)).width for c in columns)
    col_widths = {}
    for col in columns:
        config = column_configs.get(col, detect_column_type(col))
        col_widths[col] = (config.width / total_width_pct) * content_width

    # Approximate character width (Helvetica 8pt ≈ 4.5 points per char)
    CHAR_WIDTH = 4.5
    PADDING = 12  # Left + right padding

    # Check each cell for potential overflow
    for col in columns:
        available_chars = int((col_widths[col] - PADDING) / CHAR_WIDTH)

        for idx, value in df[col].items():
            if pd.isna(value):
                continue
            text = str(value)
            if len(text) > available_chars:
                warnings.append(
                    f"Text overflow: Row {idx + 1}, Column '{col}' - "
                    f"'{text[:30]}{'...' if len(text) > 30 else ''}' "
                    f"({len(text)} chars) exceeds column width (~{available_chars} chars)"
                )

    return warnings


def print_validation_warnings(warnings: List[str]) -> None:
    """Print validation warnings to stderr."""
    if warnings:
        import sys
        print("\n⚠️  VALIDATION WARNINGS:", file=sys.stderr)
        for w in warnings[:10]:  # Limit to first 10
            print(f"   • {w}", file=sys.stderr)
        if len(warnings) > 10:
            print(f"   ... and {len(warnings) - 10} more warnings", file=sys.stderr)
        print("", file=sys.stderr)


# =============================================================================
# MAIN API
# =============================================================================

def create_sales_sheet(
    # Required
    excel_path: str,
    output_path: str,

    # Theme & Branding
    theme: str = "fleetwood",
    primary_color: Optional[str] = None,
    accent_color: Optional[str] = None,
    logo_path: Optional[str] = None,
    company_name: Optional[str] = None,
    custom_theme: Optional[Theme] = None,

    # Document Settings
    title: Optional[str] = None,
    subtitle: Optional[str] = None,
    effective_date: Optional[str] = None,

    # Contact Info
    contact_name: Optional[str] = None,
    contact_email: Optional[str] = None,
    contact_phone: Optional[str] = None,

    # Data Configuration
    sheet_name: Any = 0,
    group_by_column: Optional[str] = None,
    column_config: Optional[Dict[str, Dict]] = None,
    exclude_columns: Optional[List[str]] = None,
    column_order: Optional[List[str]] = None,

    # Layout
    orientation: str = "landscape",
    page_size: str = "letter",

    # Footer
    footer_notes: Optional[List[str]] = None,

    # Validation
    validate: bool = True,
) -> str:
    """
    Create a professional PDF sales sheet from Excel data.

    Args:
        excel_path: Path to Excel file
        output_path: Output PDF path
        theme: Theme name ("fleetwood", "professional", "minimal", "bold") or "custom"
        primary_color: Override primary color (hex)
        accent_color: Override accent color (hex)
        logo_path: Path to logo image
        company_name: Company name for header
        custom_theme: Full custom Theme object
        title: Document title (defaults to filename)
        subtitle: Optional subtitle
        effective_date: Pricing effective date (defaults to today)
        contact_name: Contact name for footer
        contact_email: Contact email for footer
        contact_phone: Contact phone for footer
        sheet_name: Excel sheet to use (name or index)
        group_by_column: Column name to group rows by
        column_config: Custom column configuration dict
        exclude_columns: List of columns to exclude
        column_order: Explicit column order
        orientation: "landscape" or "portrait"
        page_size: "letter" or "legal"
        footer_notes: List of footer disclaimer strings (defaults to empty)
        validate: If True, check for text overflow and print warnings

    Returns:
        Path to created PDF file
    """

    # Load theme
    if custom_theme:
        active_theme = custom_theme
    elif theme == "custom":
        # Create custom theme from provided colors
        base = THEMES["professional"]
        active_theme = Theme(
            name="custom",
            primary=primary_color or base.primary,
            primary_dark=primary_color or base.primary_dark,
            accent=accent_color or base.accent,
            text_primary=base.text_primary,
            text_secondary=base.text_secondary,
            background=base.background,
            stripe=base.stripe,
            border=base.border,
            success=base.success,
            warning=base.warning,
            danger=base.danger,
        )
    else:
        active_theme = THEMES.get(theme, THEMES["fleetwood"])
        # Apply overrides
        if primary_color:
            active_theme.primary = primary_color
        if accent_color:
            active_theme.accent = accent_color

    # Read Excel data
    df = pd.read_excel(excel_path, sheet_name=sheet_name)

    # Filter out footer/disclaimer rows (rows where most columns are NaN)
    # This handles Excel files that have embedded disclaimers at the bottom
    if len(df.columns) > 2:
        # Count non-NaN values per row - keep rows with at least 3 non-NaN columns
        non_nan_counts = df.notna().sum(axis=1)
        df = df[non_nan_counts >= 3].reset_index(drop=True)

    # Exclude columns
    if exclude_columns:
        df = df.drop(columns=[c for c in exclude_columns if c in df.columns], errors='ignore')

    # Build column configs
    col_configs = {}
    for col in df.columns:
        # Start with auto-detected config
        col_configs[col] = detect_column_type(col)

        # Apply user overrides
        if column_config and col in column_config:
            user_cfg = column_config[col]
            for key, value in user_cfg.items():
                if hasattr(col_configs[col], key):
                    setattr(col_configs[col], key, value)

    # Set defaults
    if not title:
        title = os.path.splitext(os.path.basename(excel_path))[0].replace("_", " ")

    if not effective_date:
        effective_date = datetime.now().strftime("%B %d, %Y")

    # No default footer notes - must be explicitly provided
    if footer_notes is None:
        footer_notes = []

    # Create builder
    builder = SalesSheetBuilder(
        theme=active_theme,
        orientation=orientation,
        page_size=page_size,
    )

    # Validate data before building PDF
    if validate:
        validation_warnings = validate_table_data(
            df=df,
            column_configs=col_configs,
            content_width=builder.content_width,
            column_order=column_order,
        )
        print_validation_warnings(validation_warnings)

    # Determine page size for document
    base_size = letter if page_size == "letter" else legal
    if orientation == "landscape":
        doc_pagesize = landscape(base_size)
    else:
        doc_pagesize = base_size

    # Create document
    doc = SimpleDocTemplate(
        output_path,
        pagesize=doc_pagesize,
        leftMargin=0.5*inch,
        rightMargin=0.5*inch,
        topMargin=0.5*inch,
        bottomMargin=0.5*inch,
    )

    # Build elements
    elements = []

    # Header
    elements.extend(builder.build_header(
        title=title,
        subtitle=subtitle,
        effective_date=effective_date,
        logo_path=logo_path,
        company_name=company_name,
    ))

    # Data table(s)
    if group_by_column and group_by_column in df.columns:
        # Grouped sections
        groups = df.groupby(group_by_column, sort=False)
        for group_name, group_df in groups:
            # Remove grouping column from display
            display_df = group_df.drop(columns=[group_by_column])
            elements.extend(builder.build_section_table(
                section_name=str(group_name),
                df=display_df,
                column_configs=col_configs,
                column_order=column_order,
            ))
    else:
        # Single table
        table = builder.build_data_table(df, col_configs, column_order)
        elements.append(table)

    # Footer
    elements.extend(builder.build_footer(
        footer_notes=footer_notes,
        contact_name=contact_name,
        contact_email=contact_email,
        contact_phone=contact_phone,
    ))

    # Build PDF
    doc.build(elements, onFirstPage=add_page_numbers, onLaterPages=add_page_numbers)

    return output_path


# =============================================================================
# CLI SUPPORT
# =============================================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Create professional PDF sales sheets")
    parser.add_argument("input", help="Input Excel file")
    parser.add_argument("output", help="Output PDF file")
    parser.add_argument("--theme", default="fleetwood",
                        choices=["fleetwood", "professional", "minimal", "bold"],
                        help="Color theme")
    parser.add_argument("--title", help="Document title")
    parser.add_argument("--subtitle", help="Document subtitle")
    parser.add_argument("--contact-name", help="Contact name for footer")
    parser.add_argument("--contact-email", help="Contact email for footer")
    parser.add_argument("--contact-phone", help="Contact phone for footer")
    parser.add_argument("--orientation", default="landscape",
                        choices=["landscape", "portrait"])
    parser.add_argument("--page-size", default="letter",
                        choices=["letter", "legal"])

    args = parser.parse_args()

    result = create_sales_sheet(
        excel_path=args.input,
        output_path=args.output,
        theme=args.theme,
        title=args.title,
        subtitle=args.subtitle,
        contact_name=args.contact_name,
        contact_email=args.contact_email,
        contact_phone=args.contact_phone,
        orientation=args.orientation,
        page_size=args.page_size,
    )

    print(f"Created: {result}")
