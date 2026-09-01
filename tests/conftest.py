from __future__ import annotations

from pathlib import Path

import pytest
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from deep_pdf_reader.mapping.builder import MapBuilder
from deep_pdf_reader.mapping.store import DocumentMapStore
from deep_pdf_reader.models import DocumentMap
from deep_pdf_reader.parsers.pymupdf import PyMuPDFParser
from deep_pdf_reader.providers.mock import DeterministicTextModel


@pytest.fixture()
def sample_pdf(tmp_path: Path) -> Path:
    path = tmp_path / "sample-report.pdf"
    styles = getSampleStyleSheet()
    title = styles["Heading1"]
    title.fontName = "Helvetica-Bold"
    title.fontSize = 18
    title.leading = 22
    subtitle = styles["Heading2"]
    subtitle.fontName = "Helvetica-Bold"
    subtitle.fontSize = 14
    subtitle.leading = 18
    body = styles["BodyText"]
    body.fontName = "Helvetica"
    body.fontSize = 10
    body.leading = 14

    document = SimpleDocTemplate(
        str(path),
        pagesize=letter,
        title="Deep Reader Test Report",
        leftMargin=0.75 * inch,
        rightMargin=0.75 * inch,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
    )
    story = [
        Paragraph("1. Business Overview", title),
        Spacer(1, 12),
        Paragraph(
            "Acme Corporation designs durable industrial pumps for regional customers. "
            "This page explains the ordinary business model and customer service network.",
            body,
        ),
        PageBreak(),
        Paragraph("2. Management Discussion", title),
        Spacer(1, 8),
        Paragraph("2.1 Liquidity and Cash Flow", subtitle),
        Spacer(1, 12),
        Paragraph(
            "Operating cash flow declined because customer collections slowed while "
            "inventory purchases increased. The discussion compares working-capital "
            "drivers and refers to the following page for the supporting table. The "
            "reported amount was 12.83 billion in the source statement.",
            body,
        ),
        PageBreak(),
        Paragraph(
            "The liquidity section continues on this page with the cash flow table.", body
        ),
        Spacer(1, 12),
        Table(
            [
                ["Cash flow item", "Current year", "Prior year"],
                ["Customer collections", "92", "108"],
                ["Inventory purchases", "(41)", "(30)"],
                ["Operating cash flow", "51", "78"],
            ],
            colWidths=[2.5 * inch, 1.4 * inch, 1.4 * inch],
            style=TableStyle(
                [
                    ("GRID", (0, 0), (-1, -1), 0.75, colors.black),
                    ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                    ("FONTSIZE", (0, 0), (-1, -1), 10),
                    ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ]
            ),
        ),
        PageBreak(),
        Paragraph("3. Risk Factors", title),
        Spacer(1, 12),
        Paragraph(
            "Supply disruption and foreign-exchange volatility are the main operational "
            "risks discussed in this section.",
            body,
        ),
    ]
    document.build(story)
    return path


@pytest.fixture()
def document_map(sample_pdf: Path, tmp_path: Path) -> DocumentMap:
    store = DocumentMapStore(
        PyMuPDFParser(),
        MapBuilder(DeterministicTextModel()),
        cache_root=tmp_path / "map-cache",
    )
    return store.load_or_build(sample_pdf).document_map
