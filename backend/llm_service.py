import os
import tempfile
import time
from google import genai
from google.genai import types
from dotenv import load_dotenv
from backend.schema import EuropassCV, SessionData, ChatState

load_dotenv()
client = genai.Client()

async def process_chat_interaction(session_data: SessionData, text_message: str = None, file = None):
    bot_response = ""
    
    # --- Helper: Extract new document and merge with existing CV ---
    async def extract_and_merge(uploaded_file, current_cv: EuropassCV) -> EuropassCV:
        file_bytes = await uploaded_file.read()
        mime_type = uploaded_file.content_type
        
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_file.write(file_bytes)
            temp_path = temp_file.name

        gemini_file = None
        try:
            gemini_file = client.files.upload(file=temp_path, config={'mime_type': mime_type})
            
            while hasattr(gemini_file, 'state') and gemini_file.state and "PROCESSING" in str(gemini_file.state):
                time.sleep(2)
                gemini_file = client.files.get(name=gemini_file.name)

            # Prompt forces Gemini to combine the old JSON with the new document
            prompt = f"""
            You are a Europass CV assistant. 
            Here is the user's current CV data in JSON:
            {current_cv.model_dump_json()}
            
            Extract any relevant information from the provided document and MERGE it into the current CV data. 
            Do not delete existing information. Add new education, work, or language skills to the existing lists.
            Strictly adhere to the Europass CEFR format for languages.
            """
            
            for attempt in range(3):
                try:
                    response = client.models.generate_content(
                        model='gemini-3.6-flash',
                        contents=[gemini_file, prompt],
                        config=types.GenerateContentConfig(
                            response_mime_type="application/json",
                            response_schema=EuropassCV,
                            temperature=0.1,
                        ),
                    )
                    break
                except Exception as e:
                    if "503" in str(e) or "Deadline" in str(e):
                        if attempt < 2:
                            time.sleep(3)
                            continue
                    raise e
                    
            return EuropassCV.model_validate_json(response.text)
        finally:
            if gemini_file:
                try:
                    client.files.delete(name=gemini_file.name)
                except:
                    pass
            if os.path.exists(temp_path):
                os.remove(temp_path)

    # Clean the text input
    text_lower = text_message.lower().strip() if text_message else ""
    is_done = "done" in text_lower or "skip" in text_lower

    # --- STATE MACHINE LOGIC ---
    
    if session_data.state == ChatState.AWAITING_PASSPORT:
        if file:
            session_data.cv = await extract_and_merge(file, session_data.cv)
            session_data.state = ChatState.AWAITING_DEGREES
            bot_response = "Passport processed! Next, please upload your degree certificates one by one. Say 'done' when you have uploaded all of them."
        else:
            bot_response = "Please upload a document (like a passport or ID) so I can extract your personal details. If you want to skip this, type 'skip'."
            if is_done:
                session_data.state = ChatState.AWAITING_DEGREES
                bot_response = "Skipped personal details. Please upload your degree certificates one by one. Type 'done' when finished."

    elif session_data.state == ChatState.AWAITING_DEGREES:
        if file:
            session_data.cv = await extract_and_merge(file, session_data.cv)
            bot_response = "Degree processed successfully! Upload another degree, or type 'done' if that was the last one."
        elif is_done:
            session_data.state = ChatState.AWAITING_CERTIFICATES
            bot_response = "Great! Now, please upload any language test results or other certificates. Type 'done' when you are finished."
        else:
            bot_response = "Please upload your degree document, or type 'done' if you have no more to add."

    elif session_data.state == ChatState.AWAITING_CERTIFICATES:
        if file:
            session_data.cv = await extract_and_merge(file, session_data.cv)
            bot_response = "Certificate processed! Upload another, or type 'done'."
        elif is_done:
            # Figure out exactly what the AI missed
            missing = []
            pi = session_data.cv.personal_info
            if not pi.first_name: missing.append("first_name")
            if not pi.last_name: missing.append("last_name")
            if not pi.email: missing.append("email")
            if not pi.phone: missing.append("phone")
            
            session_data.missing_fields_queue = missing
            
            if missing:
                session_data.state = ChatState.REVIEWING_MISSING_DATA
                bot_response = f"Awesome, documents are processed. I noticed some missing details. First, what is your {missing[0].replace('_', ' ')}?"
            else:
                session_data.state = ChatState.READY_FOR_PDF
                bot_response = "All documents processed and no details are missing! You can now click the Generate PDF button."
        else:
            bot_response = "Please upload a certificate, or type 'done'."

    elif session_data.state == ChatState.REVIEWING_MISSING_DATA:
        if session_data.missing_fields_queue and text_message:
            current_field = session_data.missing_fields_queue.pop(0)
            
            # Save the user's manual text entry into the CV
            if current_field == "first_name": session_data.cv.personal_info.first_name = text_message
            elif current_field == "last_name": session_data.cv.personal_info.last_name = text_message
            elif current_field == "email": session_data.cv.personal_info.email = text_message
            elif current_field == "phone": session_data.cv.personal_info.phone = text_message
            
        if session_data.missing_fields_queue:
            next_field = session_data.missing_fields_queue[0]
            bot_response = f"Got it. Next, what is your {next_field.replace('_', ' ')}?"
        else:
            session_data.state = ChatState.READY_FOR_PDF
            bot_response = "Perfect! I have all the information I need. Click the button to generate and download your official Europass PDF."

    elif session_data.state == ChatState.READY_FOR_PDF:
        bot_response = "You are all set! Click the Generate PDF button below."

    return session_data, bot_response