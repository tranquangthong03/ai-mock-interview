import fitz  # PyMuPDF
from docx import Document as DocxDocument
from pathlib import Path
import re

def extract_text_from_pdf(file_path: str) -> str:
    text = ""

    with fitz.open(file_path) as pdf:
        for page in pdf:
            text += page.get_text() + "\n"

    return text.strip()


def extract_text_from_docx(file_path: str) -> str:
    doc = DocxDocument(file_path)
    paragraphs = [p.text for p in doc.paragraphs]
    return "\n".join(paragraphs).strip()

def clean_extracted_text(text: str) -> str:
    # Chuẩn hóa xuống dòng
    text = text.replace("\r", "\n")

    # Xóa nhiều dòng trống liên tiếp
    text = re.sub(r"\n{2,}", "\n", text)

    # Xóa nhiều khoảng trắng liên tiếp
    text = re.sub(r"[ \t]+", " ", text)

    # Xóa khoảng trắng đầu/cuối từng dòng
    lines = [line.strip() for line in text.split("\n")]

    # Bỏ dòng rỗng
    lines = [line for line in lines if line]

    return "\n".join(lines).strip()


def extract_text(file_path: str) -> str:
    suffix = Path(file_path).suffix.lower()

    if suffix == ".pdf":
        text = extract_text_from_pdf(file_path)
    elif suffix == ".docx":
        text = extract_text_from_docx(file_path)
    elif suffix == ".txt":
        with open(file_path, "r", encoding="utf-8") as f:
            text = f.read()
    else:
        raise ValueError("Unsupported file type. Only PDF, DOCX, TXT are supported.")

    return clean_extracted_text(text)
