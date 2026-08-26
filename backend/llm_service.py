import os
import tempfile
import time
import base64
from google import genai
from google.genai import types
from dotenv import load_dotenv
from backend.schema import EuropassCV, SessionData, ChatState

load_dotenv()
client = genai.Client()

async def process_chat_interaction(session_data: SessionData, text_message: str = None, file = None):
    bot_response = ""
    text_lower = text_message.lower().strip() if text_message else ""
    is_skip = "skip" in text_lower or "done" in text_lower

    async def extract_and_merge(uploaded_file, current_cv: EuropassCV, context: str) -> EuropassCV:
        file_bytes = await uploaded_file.read()
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_file.write(file_bytes)
            temp_path = temp_file.name

        gemini_file = None
        try:
            gemini_file = client.files.upload(file=temp_path, config={'mime_type': uploaded_file.content_type})
            while hasattr(gemini_file, 'state') and gemini_file.state and "PROCESSING" in str(gemini_file.state):
                time.sleep(2)
                gemini_file = client.files.get(name=gemini_file.name)

            prompt = f"""
            You are a Europass CV assistant. The user is currently providing: {context}.
            Current CV JSON: {current_cv.model_dump_json()}
            Extract the new info from the document/text and MERGE it. Do not delete existing info.
            """
            
            for attempt in range(3):
                try:
                    res = client.models.generate_content(
                        model='gemini-3.6-flash',
                        contents=[gemini_file, prompt] if gemini_file else [prompt],
                        config=types.GenerateContentConfig(response_mime_type="application/json", response_schema=EuropassCV, temperature=0.1)
                    )
                    break
                except Exception as e:
                    if attempt < 2: time.sleep(3)
                    else: raise e
            return EuropassCV.model_validate_json(res.text)
        finally:
            if gemini_file: client.files.delete(name=gemini_file.name)
            if os.path.exists(temp_path): os.remove(temp_path)

    # --- THE INTERVIEW FLOW ---
    state = session_data.state

    if state == ChatState.AWAITING_PROFILE_PIC:
        if file:
            file_bytes = await file.read()
            session_data.cv.profile_image_base64 = base64.b64encode(file_bytes).decode('utf-8')
            session_data.state = ChatState.AWAITING_PASSPORT
            bot_response = "Looking good! Next, please upload your Passport for your personal details."
        elif is_skip:
            session_data.state = ChatState.AWAITING_PASSPORT
            bot_response = "Skipped photo. Please upload your Passport."
        else:
            bot_response = "Let's begin! Please upload a professional passport-sized photo (or type 'skip')."

    elif state == ChatState.AWAITING_PASSPORT:
        if file:
            session_data.cv = await extract_and_merge(file, session_data.cv, "Passport Personal Details")
            session_data.state = ChatState.AWAITING_ABOUT
            bot_response = "Got it! Next, what would you like in your 'About' section? Tell me your career goals, or ask me to write one for you!"
        else:
            bot_response = "Please upload your passport (or type 'skip')."

    elif state == ChatState.AWAITING_ABOUT:
        if text_message:
            session_data.cv.about_me = text_message # (You can enhance this to ask LLM to rewrite it)
            session_data.state = ChatState.AWAITING_HIGHER_SEC
            bot_response = "Saved your About section! Now, please upload your Higher Secondary (Class XII) document."
        else:
            bot_response = "Please type your About section details."

    elif state == ChatState.AWAITING_HIGHER_SEC:
        if file:
            session_data.cv = await extract_and_merge(file, session_data.cv, "Higher Secondary Education")
            session_data.state = ChatState.AWAITING_SEC_EDU
            bot_response = "Class XII processed. Next, upload your Secondary Education (Class X) document."
        else:
            bot_response = "Upload your Class XII document, or type 'skip'."

    elif state == ChatState.AWAITING_SEC_EDU:
        if file:
            session_data.cv = await extract_and_merge(file, session_data.cv, "Secondary Education")
            session_data.state = ChatState.AWAITING_WORK
            bot_response = "Class X processed. Next, upload any work experience documents (Optional, type 'skip' if none)."
        else:
            bot_response = "Upload your Class X document, or type 'skip'."

    elif state == ChatState.AWAITING_WORK:
        if file:
            session_data.cv = await extract_and_merge(file, session_data.cv, "Work Experience")
            bot_response = "Work added. Upload another, or type 'done'."
        elif is_skip:
            session_data.state = ChatState.AWAITING_LANGUAGES
            bot_response = "Moving on! Please upload any language test results (IELTS, TOEFL, etc.)."

    elif state == ChatState.AWAITING_LANGUAGES:
        if file:
            session_data.cv = await extract_and_merge(file, session_data.cv, "Language Results")
            bot_response = "Languages added. Upload another, or type 'done'."
        elif is_skip:
            session_data.state = ChatState.AWAITING_SKILLS
            bot_response = "Next, type out a comma-separated list of your technical and personal skills."

    elif state == ChatState.AWAITING_SKILLS:
        if text_message:
            session_data.cv.digital_skills = [s.strip() for s in text_message.split(",")]
            session_data.state = ChatState.AWAITING_OTHER
            bot_response = "Skills saved! Is there any other information you want to add to your CV? (Type 'skip' if no)."

    elif state == ChatState.AWAITING_OTHER:
        if text_message and not is_skip:
            session_data.cv.other_info = text_message
        session_data.state = ChatState.AWAITING_HOBBIES
        bot_response = "Finally, list your hobbies and interests (comma-separated), or type 'skip'."

    elif state == ChatState.AWAITING_HOBBIES:
        if text_message and not is_skip:
            session_data.cv.hobbies = [h.strip() for h in text_message.split(",")]
        session_data.state = ChatState.READY_FOR_PDF
        bot_response = "Amazing! Your CV is completely mapped out. Click Generate PDF below!"

    return session_data, bot_response