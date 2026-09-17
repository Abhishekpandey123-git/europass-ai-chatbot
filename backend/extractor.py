import io
import os
import base64
import time
import pymupdf
from PIL import Image
from llama_parse import LlamaParse
from dotenv import load_dotenv

load_dotenv()

async def parse_document_with_llamaparse(file_path: str) -> str:
    """
    Sends documents to LlamaParse API to extract structured markdown.
    Offloads heavy OCR and document parsing to LlamaCloud infrastructure with timestamp logging.
    """
    api_key = os.getenv("LLAMA_CLOUD_API_KEY")
    if not api_key:
        raise ValueError("LLAMA_CLOUD_API_KEY is not set in environment variables.")

    start_time = time.time()
    timestamp_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(start_time))
    print(f"[TIMING] [{timestamp_str}] Starting LlamaParse extraction for: {file_path}")

    parser = LlamaParse(
        api_key=api_key,
        result_type="markdown",
        verbose=True
    )

    documents = await parser.aload_data(file_path)
    full_text = "\n".join([doc.text for doc in documents])

    elapsed = time.time() - start_time
    print(f"[TIMING] LlamaParse completed successfully in {elapsed:.2f} seconds.")
    return full_text

async def get_document_base64_image(uploaded_file) -> str:
    """
    Renders uploaded PDF pages or standard image files into a base64 encoded JPEG string.
    Useful for multimodal LLM vision workflows, with execution duration tracking.
    """
    start_time = time.time()
    print(f"[TIMING] Starting base64 image conversion for upload...")

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

    elapsed = time.time() - start_time
    print(f"[TIMING] Base64 image conversion completed in {elapsed:.2f} seconds.")

    return base64.b64encode(img_bytes).decode("utf-8")