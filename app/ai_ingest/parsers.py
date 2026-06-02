import io
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def parse_pdf(file_bytes: bytes, filename: str = "") -> str:
    try:
        import pdfplumber
    except ImportError:
        logger.warning("pdfplumber not installed, PDF parsing unavailable")
        return ""
    text_parts = []
    try:
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            for page in pdf.pages:
                txt = page.extract_text()
                if txt:
                    text_parts.append(txt)
    except Exception as e:
        logger.error("PDF parse error (%s): %s", filename, e)
        return ""
    return "\n".join(text_parts)


def parse_excel(file_bytes: bytes, filename: str = "") -> str:
    try:
        import pandas as pd
    except ImportError:
        logger.warning("pandas not installed, Excel parsing unavailable")
        return ""
    text_parts = []
    try:
        xls = pd.ExcelFile(io.BytesIO(file_bytes))
        for sheet_name in xls.sheet_names:
            df = pd.read_excel(xls, sheet_name=sheet_name)
            text_parts.append(f"=== Sheet: {sheet_name} ===")
            text_parts.append(df.to_string(index=False))
    except Exception as e:
        logger.error("Excel parse error (%s): %s", filename, e)
        return ""
    return "\n".join(text_parts)


def parse_word(file_bytes: bytes, filename: str = "") -> str:
    try:
        from docx import Document
    except ImportError:
        logger.warning("python-docx not installed, Word parsing unavailable")
        return ""
    try:
        doc = Document(io.BytesIO(file_bytes))
        return "\n".join(p.text for p in doc.paragraphs)
    except Exception as e:
        logger.error("Word parse error (%s): %s", filename, e)
        return ""


def parse_outlook_msg(file_bytes: bytes, filename: str = "") -> str:
    try:
        import extract_msg
    except ImportError:
        logger.warning("extract-msg not installed, Outlook .msg parsing unavailable")
        return ""
    try:
        msg = extract_msg.Message(io.BytesIO(file_bytes))
        parts = []
        if msg.subject:
            parts.append(f"Subject: {msg.subject}")
        if msg.sender:
            parts.append(f"From: {msg.sender}")
        if msg.to:
            parts.append(f"To: {msg.to}")
        if msg.body:
            parts.append(msg.body)
        return "\n".join(parts)
    except Exception as e:
        logger.error("Outlook msg parse error (%s): %s", filename, e)
        return ""


def parse_plain_text(file_bytes: bytes, filename: str = "") -> str:
    try:
        return file_bytes.decode("utf-8", errors="replace")
    except Exception as e:
        logger.error("Text parse error (%s): %s", filename, e)
        return ""


PARSER_MAP = {
    ".pdf": parse_pdf,
    ".xls": parse_excel,
    ".xlsx": parse_excel,
    ".doc": parse_word,
    ".docx": parse_word,
    ".msg": parse_outlook_msg,
    ".txt": parse_plain_text,
    ".csv": parse_plain_text,
    ".json": parse_plain_text,
    ".xml": parse_plain_text,
}


def parse_document(file_bytes: bytes, filename: str) -> str:
    ext = Path(filename).suffix.lower()
    parser = PARSER_MAP.get(ext, parse_plain_text)
    return parser(file_bytes, filename)
