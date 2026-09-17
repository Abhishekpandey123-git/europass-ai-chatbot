import os
from google import genai
from google.genai import types
from dotenv import load_dotenv
from backend.schema import EuropassCV

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise ValueError("GEMINI_API_KEY is missing from environment variables!")

client = genai.Client(api_key=api_key)

async def parse_document_with_vision(uploaded_file, current_cv: EuropassCV, context: str) -> EuropassCV:
    file_bytes = await uploaded_file.read()
    
    filename = getattr(uploaded_file, 'filename', '').lower()
    mime_type = "application/pdf" if filename.endswith(".pdf") else "image/jpeg"

    prompt = f"""
    You are an expert document parser. Inspect this document layout visually for '{context}'.
    Extract all relevant personal info, education history, and work experience details accurately.
    """

    # Passes the raw document bytes natively to Gemini with schema enforcement
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=[
            types.Part.from_bytes(data=file_bytes, mime_type=mime_type),
            prompt
        ],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=EuropassCV,
            temperature=0.0
        ),
    )

    parsed_cv = EuropassCV.model_validate_json(response.text)

    current_dict = current_cv.model_dump()
    parsed_dict = parsed_cv.model_dump()

    # Merge extracted details into session state
    if parsed_dict.get("personal_info"):
        for k, v in parsed_dict["personal_info"].items():
            if v and str(v).strip() and str(v).lower() not in ["n/a", "none", ""]:
                current_dict["personal_info"][k] = str(v).strip()

    if parsed_dict.get("education"):
        for edu in parsed_dict["education"]:
            if edu.get("title") and edu.get("title").lower() not in ["n/a", ""]:
                current_dict["education"].append(edu)

    if parsed_dict.get("work_experience"):
        for work in parsed_dict["work_experience"]:
            if work.get("title") and work.get("title").lower() not in ["n/a", ""]:
                current_dict["work_experience"].append(work)

    return EuropassCV.model_validate(current_dict)