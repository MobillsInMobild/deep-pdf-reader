"""Map-guided, source-page-verified PDF reading."""

from deep_pdf_reader.models import EvidenceItem, EvidenceResult
from deep_pdf_reader.workflow import DeepPdfReader

__all__ = ["DeepPdfReader", "EvidenceItem", "EvidenceResult"]
__version__ = "0.1.0"
