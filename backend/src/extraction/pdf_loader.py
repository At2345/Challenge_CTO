"""PDF text extraction using multiple independent engines, arbitrated by
an accuracy score rather than a simple first-success fallback chain.

Three engines are available:

1. pdfplumber (handles most digital/vector PDFs cleanly).
2. PyMuPDF (fitz) -- a second, independently implemented digital-text
   extractor that sometimes recovers text pdfplumber misses (or vice
   versa) due to differences in how each library parses content streams.
3. pytesseract OCR over rendered page images -- the only engine able to
   read scanned/image-only PDFs, but also useful as a cross-check for
   digital PDFs with unusual encodings that garble text extraction.

Both digital engines always run (cheap). OCR is comparatively expensive
(page rasterization + Tesseract), so it is skipped when both digital
engines already produced high-confidence output (see
`_HIGH_CONFIDENCE_SCORE`); otherwise it also runs and is compared
alongside the digital results.

Each engine's output is scored by `_score_text()` (recognized German
invoice vocabulary hits, printable-character ratio, and length), and the
highest-scoring result is used. This catches cases where one digital
extractor silently returns garbled or incomplete text for a given PDF
while another engine (digital or OCR) produces a clean result.
"""
import re
from typing import Callable, Dict, List, Optional, Tuple


def _extract_with_pdfplumber(path: str) -> str:
    import pdfplumber

    text_parts = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text() or ""
            text_parts.append(page_text)
    return "\n".join(text_parts).strip()


def _extract_with_pymupdf(path: str) -> str:
    import fitz  # PyMuPDF

    text_parts = []
    with fitz.open(path) as doc:
        for page in doc:
            text_parts.append(page.get_text())
    return "\n".join(text_parts).strip()


def _extract_with_ocr(path: str) -> str:
    import fitz  # PyMuPDF
    import pytesseract
    from PIL import Image
    import io

    text_parts = []
    with fitz.open(path) as doc:
        for page in doc:
            pix = page.get_pixmap(dpi=300)
            image = Image.open(io.BytesIO(pix.tobytes("png")))
            text_parts.append(pytesseract.image_to_string(image, lang="deu+eng"))
    return "\n".join(text_parts).strip()


_KEYWORD_HINTS_RE = re.compile(
    r"rechnung|nummer|datum|betrag|eur|ust|mwst|netto|brutto|iban|gmbh|steuer|"
    r"leistung|empf[aä]nger|w[aä]hrung|kunden",
    re.IGNORECASE,
)


def _printable_ratio(text: str) -> float:
    if not text:
        return 0.0
    printable = sum(1 for c in text if c.isalnum() or c.isspace() or c in ".,-:/%€·")
    return printable / len(text)


def _score_text(text: Optional[str]) -> float:
    """Heuristic accuracy score used to arbitrate between extraction engines.

    Higher is better. Rewards recognizable German invoice vocabulary
    (strong signal the text was extracted correctly/coherently), a high
    ratio of printable/expected characters (penalizes OCR noise or
    mis-decoded digital text), and overall content length (penalizes
    engines that only partially recovered the document).
    """
    if not text or not text.strip():
        return -1.0
    keyword_hits = len(_KEYWORD_HINTS_RE.findall(text))
    ratio = _printable_ratio(text)
    return keyword_hits * 10 + ratio * 5 + min(len(text), 2000) * 0.001


# Minimum `_score_text()` value considered "high confidence". Calibrated
# against clean digital sample invoices, which typically score ~175-215
# (several recognized keywords + near-100% printable ratio). Garbled/noisy
# text (wrong encoding, OCR artifacts) scores far lower since it lacks
# recognizable invoice vocabulary. Set well below the clean-text range so
# only genuinely well-extracted text skips the OCR cross-check, while still
# well above what garbled text can reach purely from length/printable-ratio.
_HIGH_CONFIDENCE_SCORE = 80.0


def extract_text_with_method(path: str) -> Tuple[str, str]:
    """Run extraction engines and return the best-scoring result.

    Both digital engines (pdfplumber, PyMuPDF) always run, since they are
    cheap. OCR is comparatively expensive (page rasterization + Tesseract)
    and is only needed either when a document has no digital text layer at
    all (scanned PDFs) or when the digital engines produced suspect output.
    OCR is therefore skipped when *both* digital engines succeeded and
    scored above `_HIGH_CONFIDENCE_SCORE` -- otherwise it still runs and
    is compared against the digital results like any other candidate.

    Returns a tuple of (text, method_name) so callers can record which
    engine's output was actually used, for audit-trail transparency.
    """
    digital_engines: List[Tuple[str, Callable[[str], str]]] = [
        ("pdfplumber", _extract_with_pdfplumber),
        ("pymupdf", _extract_with_pymupdf),
    ]

    candidates: Dict[str, str] = {}
    for name, fn in digital_engines:
        try:
            result = fn(path)
        except Exception:
            result = None
        if result:
            candidates[name] = result

    both_digital_high_confidence = (
        "pdfplumber" in candidates
        and "pymupdf" in candidates
        and _score_text(candidates["pdfplumber"]) >= _HIGH_CONFIDENCE_SCORE
        and _score_text(candidates["pymupdf"]) >= _HIGH_CONFIDENCE_SCORE
    )

    if not both_digital_high_confidence:
        try:
            ocr_result = _extract_with_ocr(path)
        except Exception:
            ocr_result = None
        if ocr_result:
            candidates["ocr"] = ocr_result

    if not candidates:
        return "", "none"

    best_name = max(candidates, key=lambda name: _score_text(candidates[name]))
    return candidates[best_name], best_name


def extract_text(path: str) -> str:
    """Return the best-effort text content of the PDF at `path`.

    Convenience wrapper around `extract_text_with_method` for callers that
    don't need to know which engine won.
    """
    text, _method = extract_text_with_method(path)
    return text
