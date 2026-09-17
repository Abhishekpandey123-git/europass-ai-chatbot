# import os
# import json
# from groq import Groq
# from dotenv import load_dotenv
# from backend.schema import EuropassCV

# load_dotenv()
# groq_api_key = os.getenv("GROQ_API_KEY")
# if not groq_api_key:
#     raise ValueError("GROQ_API_KEY is missing from environment variables!")

# groq_client = Groq(api_key=groq_api_key)

# async def parse_document_with_groq_text(markdown_text: str, current_cv: EuropassCV, context: str) -> EuropassCV:
#     prompt = f"""
#     You are an expert document data extractor. Inspect this document markdown content for context: '{context}'.
#     Extract all matching personal info, education history, and work experience details accurately.
#     Return a clean JSON object matching this schema structure:
#     {{
#       "personal_info": {{
#         "first_name": "string",
#         "last_name": "string",
#         "email": "string",
#         "phone": "string",
#         "date_of_birth": "string",
#         "nationality": ["string"]
#       }},
#       "education": [
#         {{
#           "title": "string",
#           "organization": "string",
#           "start_date": "string",
#           "end_date": "string",
#           "description": "string"
#         }}
#       ],
#       "work_experience": [
#         {{
#           "title": "string",
#           "employer": "string",
#           "start_date": "string",
#           "end_date": "string",
#           "description": "string"
#         }}
#       ]
#     }}
#     Return ONLY valid JSON. If a field is missing, use an empty string or empty list.

#     Markdown Document Content:
#     {markdown_text}
#     """

#     response = groq_client.chat.completions.create(
#         model="llama3-8b-8192",
#         messages=[{"role": "user", "content": prompt}],
#         temperature=0.0,
#         response_format={"type": "json_object"}
#     )

#     try:
#         data_dict = json.loads(response.choices[0].message.content)
#     except Exception:
#         data_dict = {}

#     current_dict = current_cv.model_dump()

#     if "personal_info" in data_dict and isinstance(data_dict["personal_info"], dict):
#         for k, v in data_dict["personal_info"].items():
#             if v and str(v).strip() and str(v).lower() not in ["n/a", "none", ""]:
#                 if k == "nationality":
#                     if isinstance(v, str):
#                         current_dict["personal_info"][k] = [v.strip()]
#                     elif isinstance(v, list):
#                         current_dict["personal_info"][k] = [str(item).strip() for item in v]
#                 else:
#                     current_dict["personal_info"][k] = str(v).strip()

#     if "education" in data_dict and isinstance(data_dict["education"], list):
#         for edu in data_dict["education"]:
#             if isinstance(edu, dict) and edu.get("title"):
#                 current_dict["education"].append({
#                     "title": str(edu.get("title") or ""),
#                     "organization": str(edu.get("organization") or ""),
#                     "start_date": str(edu.get("start_date") or ""),
#                     "end_date": str(edu.get("end_date") or ""),
#                     "description": str(edu.get("description") or "")
#                 })

#     if "work_experience" in data_dict and isinstance(data_dict["work_experience"], list):
#         for work in data_dict["work_experience"]:
#             if isinstance(work, dict) and work.get("title"):
#                 current_dict["work_experience"].append({
#                     "title": str(work.get("title") or ""),
#                     "employer": str(work.get("employer") or ""),
#                     "start_date": str(work.get("start_date") or ""),
#                     "end_date": str(work.get("end_date") or ""),
#                     "description": str(work.get("description") or "")
#                 })

#     return EuropassCV.model_validate(current_dict)


# async def generate_ai_about_me_groq(current_cv: EuropassCV) -> str:
#     first_name = current_cv.personal_info.first_name or "Candidate"
#     last_name = current_cv.personal_info.last_name or ""
#     edu_titles = [e.title for e in current_cv.education] if current_cv.education else []
#     skills = current_cv.digital_skills if current_cv.digital_skills else []
    
#     prompt = f"""
#     Write a professional, concise 2-sentence Europass profile summary (About Me) for {first_name} {last_name}.
#     Their educational background includes: {', '.join(edu_titles)}.
#     Their technical skills include: {', '.join(skills)}.
#     Keep it formal, motivation-driven, and tailored for career/academic opportunities. Return ONLY the raw summary text.
#     """

#     response = groq_client.chat.completions.create(
#         model="llama3-8b-8192",
#         messages=[{"role": "user", "content": prompt}],
#         temperature=0.7,
#     )
#     return response.choices[0].message.content.strip()


# async def update_cv_via_instruction_groq(current_cv: EuropassCV, instruction: str) -> EuropassCV:
#     current_dict = current_cv.model_dump()
#     prompt = f"""
#     You are an intelligent CV editing assistant. 
#     Here is the current CV data JSON:
#     {json.dumps(current_dict)}

#     The user wants to make this change or correction: "{instruction}"
    
#     Update the JSON fields accordingly to reflect the user's request. Return ONLY the updated valid JSON object matching the exact original structure.
#     """

#     response = groq_client.chat.completions.create(
#         model="openai/gpt-oss-20b",
#         messages=[{"role": "user", "content": prompt}],
#         temperature=0.0,
#         response_format={"type": "json_object"}
#     )

#     try:
#         updated_dict = json.loads(response.choices[0].message.content)
#         return EuropassCV.model_validate(updated_dict)
#     except Exception:
#         return current_cv