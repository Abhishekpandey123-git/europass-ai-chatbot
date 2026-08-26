import os
import json
import base64
from google import genai
from google.genai import types
from dotenv import load_dotenv
from backend.schema import EuropassCV
from backend.extractor import get_document_base64_image

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise ValueError("GEMINI_API_KEY is missing from environment variables!")

client = genai.Client(api_key=api_key)

async def parse_document_with_gemini(uploaded_file, current_cv: EuropassCV, context: str) -> EuropassCV:
    base64_image = await get_document_base64_image(uploaded_file)

    prompt = f"""
    You are an expert document parser. Inspect this document layout visually for context: '{context}'.
    Extract all matching personal info, education history, and work experience details accurately.
    Return a clean JSON object matching this schema structure:
    {{
      "personal_info": {{
        "first_name": "string",
        "last_name": "string",
        "email": "string",
        "phone": "string",
        "date_of_birth": "string",
        "nationality": ["string"]
      }},
      "education": [
        {{
          "title": "string",
          "organization": "string",
          "start_date": "string",
          "end_date": "string",
          "description": "string"
        }}
      ],
      "work_experience": [
        {{
          "title": "string",
          "employer": "string",
          "start_date": "string",
          "end_date": "string",
          "description": "string"
        }}
      ]
    }}
    Return ONLY valid JSON. If a field is missing, use an empty string or empty list.
    """

    response = client.models.generate_content(
        model='gemini-3.6-flash',
        contents=[
            types.Part.from_bytes(
                data=base64.b64decode(base64_image),
                mime_type='image/jpeg',
            ),
            prompt
        ],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=0.0
        ),
    )

    try:
        data_dict = json.loads(response.text)
    except Exception:
        data_dict = {}

    current_dict = current_cv.model_dump()

    # Safely merge personal info and handle type casting (e.g., string vs list for nationality)
    if "personal_info" in data_dict and isinstance(data_dict["personal_info"], dict):
        for k, v in data_dict["personal_info"].items():
            if v and str(v).strip() and str(v).lower() not in ["n/a", "none", ""]:
                if k == "nationality":
                    if isinstance(v, str):
                        current_dict["personal_info"][k] = [v.strip()]
                    elif isinstance(v, list):
                        current_dict["personal_info"][k] = [str(item).strip() for item in v]
                else:
                    current_dict["personal_info"][k] = str(v).strip()

    # Merge education safely
    if "education" in data_dict and isinstance(data_dict["education"], list):
        for edu in data_dict["education"]:
            if isinstance(edu, dict) and edu.get("title"):
                current_dict["education"].append({
                    "title": str(edu.get("title") or ""),
                    "organization": str(edu.get("organization") or ""),
                    "start_date": str(edu.get("start_date") or ""),
                    "end_date": str(edu.get("end_date") or ""),
                    "description": str(edu.get("description") or "")
                })

    # Merge work experience safely
    if "work_experience" in data_dict and isinstance(data_dict["work_experience"], list):
        for work in data_dict["work_experience"]:
            if isinstance(work, dict) and work.get("title"):
                current_dict["work_experience"].append({
                    "title": str(work.get("title") or ""),
                    "employer": str(work.get("employer") or ""),
                    "start_date": str(work.get("start_date") or ""),
                    "end_date": str(work.get("end_date") or ""),
                    "description": str(work.get("description") or "")
                })

    return EuropassCV.model_validate(current_dict)


async def generate_ai_about_me(current_cv: EuropassCV) -> str:
    """
    Generates a professional profile summary dynamically using Gemini 
    based on the candidate's existing academic and skill profile.
    """
    first_name = current_cv.personal_info.first_name or "Candidate"
    last_name = current_cv.personal_info.last_name or ""
    edu_titles = [e.title for e in current_cv.education] if current_cv.education else []
    skills = current_cv.digital_skills if current_cv.digital_skills else []
    
    prompt = f"""
    Write a professional, concise 2-sentence Europass profile summary (About Me) for {first_name} {last_name}.
    Their educational background includes: {', '.join(edu_titles)}.
    Their technical skills include: {', '.join(skills)}.
    Keep it formal, motivation-driven, and tailored for career/academic opportunities. Return ONLY the raw summary text.
    """

    response = client.models.generate_content(
        model='gemini-3.6-flash',
        contents=[prompt],
        config=types.GenerateContentConfig(temperature=0.7),
    )
    return response.text.strip()