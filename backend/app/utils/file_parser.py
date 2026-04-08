import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024  # 50 MB


def parse_file(file_path: str) -> str:
    """
    Parse a file and return its plain text content.

    Supports: PDF, DOCX, TXT, MD
    Raises ValueError for unsupported formats or files exceeding 50 MB.
    """
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    file_size = os.path.getsize(file_path)
    if file_size > MAX_FILE_SIZE_BYTES:
        raise ValueError(
            f"File size {file_size / (1024 * 1024):.1f} MB exceeds limit of 50 MB"
        )

    suffix = path.suffix.lower()

    if suffix == ".pdf":
        return _parse_pdf(file_path)
    elif suffix == ".docx":
        return _parse_docx(file_path)
    elif suffix in (".txt", ".md"):
        return _parse_text(file_path)
    else:
        raise ValueError(f"Unsupported file format: {suffix}. Supported: PDF, DOCX, TXT, MD")


def _parse_pdf(file_path: str) -> str:
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise ImportError("pypdf is required for PDF parsing. Run: uv add pypdf") from exc

    reader = PdfReader(file_path)
    pages = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            pages.append(text)

    result = "\n\n".join(pages)
    logger.info("Parsed PDF %s — %d pages, %d chars", file_path, len(reader.pages), len(result))
    return result


def _parse_docx(file_path: str) -> str:
    try:
        from docx import Document
    except ImportError as exc:
        raise ImportError(
            "python-docx is required for DOCX parsing. Run: uv add python-docx"
        ) from exc

    doc = Document(file_path)
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    result = "\n\n".join(paragraphs)
    logger.info("Parsed DOCX %s — %d paragraphs, %d chars", file_path, len(paragraphs), len(result))
    return result


def _parse_text(file_path: str) -> str:
    with open(file_path, encoding="utf-8") as f:
        result = f.read()
    logger.info("Parsed text file %s — %d chars", file_path, len(result))
    return result
