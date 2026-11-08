import io
import os
import re
from typing import Tuple

def extract_text_from_txt(file_bytes: bytes) -> str:
    """Extracts text from UTF-8 / ASCII / Latin-1 encoded plain text."""
    for encoding in ["utf-8", "latin-1", "utf-16", "cp1252"]:
        try:
            return file_bytes.decode(encoding)
        except UnicodeDecodeError:
            continue
    return file_bytes.decode("utf-8", errors="replace")

def extract_text_from_pdf(file_bytes: bytes) -> str:
    """Extracts text from digital PDF using pypdf."""
    try:
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(file_bytes))
        extracted_pages = []
        for i, page in enumerate(reader.pages):
            text = page.extract_text()
            if text:
                extracted_pages.append(text.strip())
        return "\n\n".join(extracted_pages)
    except Exception as e:
        return f"[PDF Extraction Error: {str(e)}]"

def extract_text_from_docx(file_bytes: bytes) -> str:
    """Extracts text from Microsoft Word (.docx) files."""
    try:
        import docx
        doc = docx.Document(io.BytesIO(file_bytes))
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        # Also extract text from tables
        for table in doc.tables:
            for row in table.rows:
                row_text = " | ".join(cell.text.strip() for cell in row.cells if cell.text.strip())
                if row_text:
                    paragraphs.append(row_text)
        return "\n\n".join(paragraphs)
    except Exception as e:
        return f"[DOCX Extraction Error: {str(e)}]"

def extract_text_from_image(file_bytes: bytes, filename: str = "") -> Tuple[str, str]:
    """
    Extracts text from images (.png, .jpg, .jpeg) using pytesseract if available,
    or falls back gracefully with helpful guidance.
    """
    try:
        from PIL import Image
        image = Image.open(io.BytesIO(file_bytes))
        
        # Check pytesseract
        import pytesseract
        # Auto-detect Tesseract in typical Windows locations if not on PATH
        common_paths = [
            r"C:\Program Files\Tesseract-OCR\tesseract.exe",
            r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
            os.path.expanduser(r"~\AppData\Local\Programs\Tesseract-OCR\tesseract.exe")
        ]
        for p in common_paths:
            if os.path.exists(p):
                pytesseract.pytesseract.tesseract_cmd = p
                break
                
        text = pytesseract.image_to_string(image)
        if text.strip():
            return text.strip(), "success"
        else:
            return "[OCR Alert: No readable text detected in this image. Ensure high resolution and readable contrast.]", "empty"
    except Exception as e:
        err_msg = str(e)
        if "tesseract is not installed" in err_msg.lower() or "not found" in err_msg.lower():
            return (
                f"[Image Loaded: '{filename}'. OCR Engine requires Tesseract executable. "
                "For now, please copy/paste handwritten/printed text directly, or install Tesseract Windows binary for automatic scan OCR.]",
                "engine_missing"
            )
        return f"[Image Processing Error: {err_msg}]", "error"

def parse_uploaded_file(uploaded_file) -> Tuple[str, str]:
    """
    Unified router that extracts text from .txt, .pdf, .docx, and image files (.jpg, .jpeg, .png).
    Returns (extracted_text, file_type_summary)
    """
    if uploaded_file is None:
        return "", ""
    
    filename = uploaded_file.name
    ext = os.path.splitext(filename)[1].lower()
    file_bytes = uploaded_file.read()
    
    if ext == ".txt":
        return extract_text_from_txt(file_bytes), "Plain Text (.txt)"
    elif ext == ".pdf":
        return extract_text_from_pdf(file_bytes), "PDF Document (.pdf)"
    elif ext in [".docx", ".doc"]:
        return extract_text_from_docx(file_bytes), "Word Document (.docx)"
    elif ext in [".png", ".jpg", ".jpeg", ".webp", ".bmp"]:
        text, status = extract_text_from_image(file_bytes, filename)
        return text, f"Image ({ext})"
    else:
        # Fallback treat as text
        return extract_text_from_txt(file_bytes), f"Generic File ({ext})"
