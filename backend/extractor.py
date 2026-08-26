import io
import base64
import pymupdf
from PIL import Image

async def get_document_base64_image(uploaded_file) -> str:
    file_bytes = await uploaded_file.read()
    
    try:
        # Render first page of PDF to image natively via PyMuPDF
        doc = pymupdf.open(stream=file_bytes, filetype="pdf")
        page = doc[0]
        pix = page.get_pixmap(dpi=150)
        img_bytes = pix.tobytes("jpeg")
    except Exception:
        # Handle direct image uploads (PNG/JPEG)
        img = Image.open(io.BytesIO(file_bytes))
        if img.mode != "RGB":
            img = img.convert("RGB")
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=85)
        img_bytes = buffer.getvalue()

    return base64.b64encode(img_bytes).decode("utf-8")