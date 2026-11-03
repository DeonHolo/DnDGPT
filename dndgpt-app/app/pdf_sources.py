"""Bounded PDF reference extraction and visual pages, serialized for PDFium safety."""
import base64
from functools import lru_cache
from io import BytesIO
from threading import RLock

import pypdfium2 as pdfium

PDF_LOCK = RLock()  # PDFium must not run concurrently, even on different documents.


def extract_pages(data):
    with PDF_LOCK, pdfium.PdfDocument(data) as document:
        if not 1 <= len(document) <= 96:
            raise ValueError("Adventure PDF exceeds its page limit")
        texts = []
        for index in range(len(document)):
            page = document[index]
            textpage = page.get_textpage()
            try:
                text = textpage.get_text_range()
                if len(text) > 100_000:
                    raise ValueError("Source page exceeds its text limit")
                texts.append(text)
            finally:
                textpage.close(); page.close()
        return texts


def needs_visual(text):
    controls = sum(ord(c) < 32 and c not in "\r\n\t" for c in text)
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    fragmented = len(lines) >= 15 and sum(len(line) <= 2 for line in lines) / len(lines) > .15
    return len(text.strip()) < 250 or controls / max(1, len(text)) > .03 or fragmented


@lru_cache(maxsize=24)
def render_page(data, page_number):
    with PDF_LOCK, pdfium.PdfDocument(data) as document:
        if type(page_number) is not int or not 1 <= page_number <= len(document):
            raise ValueError("Choose an existing PDF page")
        page = document[page_number - 1]
        bitmap = None
        try:
            width, height = page.get_size()
            if min(width, height) <= 0:
                raise ValueError("Invalid PDF page size")
            bitmap = page.render(scale=min(2, 1800 / max(width, height)))
            picture = bitmap.to_pil().convert("RGB")
            output = BytesIO(); picture.save(output, format="JPEG", quality=90)
            return {"type": "image", "mimeType": "image/jpeg", "data": base64.b64encode(output.getvalue()).decode()}
        finally:
            if bitmap is not None: bitmap.close()
            page.close()
