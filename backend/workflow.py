import base64
import os
import tempfile
from backend.schema import SessionData, ChatState
from backend.extractor import parse_document_with_llamaparse
from backend.openrouter_service import (
    parse_document_with_openrouter_text as parse_document_with_gemini_text,
    generate_ai_about_me_openrouter as generate_ai_about_me,
    update_cv_via_instruction_openrouter as update_cv_via_instruction
)

MAX_UPLOAD_BYTES = 10 * 1024 * 1024

async def process_chat_interaction(session_data: SessionData, text_message: str = None, file = None):
    bot_response = ""
    text_lower = text_message.lower().strip() if text_message else ""
    is_skip = "skip" in text_lower or text_lower == "done"

    # Helper function to handle cloud-based document parsing efficiently & merge into CV
    async def process_doc_with_cloud(file_obj, category_name: str):
        suffix = os.path.splitext(file_obj.filename or "")[1].lower()
        temp_file = tempfile.NamedTemporaryFile(prefix="europass_", suffix=suffix, delete=False)
        temp_file_path = temp_file.name
        total_bytes = 0
        try:
            while chunk := file_obj.file.read(1024 * 1024):
                total_bytes += len(chunk)
                if total_bytes > MAX_UPLOAD_BYTES:
                    raise ValueError("Uploaded file is too large")
                temp_file.write(chunk)
            temp_file.close()
            parsed_markdown = await parse_document_with_llamaparse(temp_file_path)
            session_data.cv = await parse_document_with_gemini_text(parsed_markdown, session_data.cv, category_name)
        finally:
            if not temp_file.closed:
                temp_file.close()
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)

    # Handle profile picture upload anytime if an image file is attached
    if file and file.content_type and file.content_type.startswith("image/"):
        file_bytes = await file.read(MAX_UPLOAD_BYTES + 1)
        if len(file_bytes) > MAX_UPLOAD_BYTES:
            raise ValueError("Uploaded file is too large")
        session_data.cv.profile_image_base64 = base64.b64encode(file_bytes).decode('utf-8')
        bot_response = "Profile photo updated successfully! "
        file = None # Consumed

    state = session_data.state

    # --- STEP 1: GATHER PERSONAL INFO / PASSPORT ---
    if state == ChatState.GATHERING_PERSONAL:
        if file:
            await process_doc_with_cloud(file, "Passport / Personal Details")
            bot_response += "Personal information extracted from document! "
        elif text_message and text_message != "resume" and not is_skip:
            session_data.cv = await update_cv_via_instruction(session_data.cv, text_message)
            bot_response += "Personal details saved! "
        
        # Advance to Education step
        session_data.state = ChatState.GATHERING_EDUCATION
        bot_response += "Next step: Please upload your **Education / Degree certificates** (or type details manually, or click Skip)."

    # --- STEP 2: GATHER EDUCATION ---
    elif state == ChatState.GATHERING_EDUCATION:
        if file:
            await process_doc_with_cloud(file, "Education and Training")
            bot_response += "Education history extracted! "
        elif text_message and text_message != "resume" and not is_skip:
            session_data.cv = await update_cv_via_instruction(session_data.cv, text_message)
            bot_response += "Education details saved! "

        # Advance to Work Experience step
        session_data.state = ChatState.GATHERING_WORK
        bot_response += "Next step: Please upload your **Work Experience / Internship certificates** (or type details manually, or click Skip)."

    # --- STEP 3: GATHER WORK EXPERIENCE ---
    elif state == ChatState.GATHERING_WORK:
        if file:
            await process_doc_with_cloud(file, "Work Experience")
            bot_response += "Work experience extracted! "
        elif text_message and text_message != "resume" and not is_skip:
            session_data.cv = await update_cv_via_instruction(session_data.cv, text_message)
            bot_response += "Work details saved! "

        # Advance to Skills step
        session_data.state = ChatState.GATHERING_SKILLS
        bot_response += "Next step: Please list your **Digital / Technical Skills** (comma-separated) or upload skill certificates (or click Skip)."

    # --- STEP 4: GATHER SKILLS & GENERATE ABOUT ME ---
    elif state == ChatState.GATHERING_SKILLS:
        if file:
            await process_doc_with_cloud(file, "Skills & Languages")
        elif text_message and text_message != "resume" and not is_skip:
            if "," in text_message or len(text_message.split()) < 10:
                session_data.cv.digital_skills = [s.strip() for s in text_message.split(",")]
            else:
                session_data.cv = await update_cv_via_instruction(session_data.cv, text_message)

        # All categories collected! Now automatically generate the professional "About Me" summary using full context
        session_data.cv.about_me = await generate_ai_about_me(session_data.cv)
        
        session_data.state = ChatState.PREVIEW_READY
        bot_response = "All core documents and sections have been processed! I've automatically written your professional **'About Me'** summary based on your background. Your live CV preview is ready below!"

    # --- REVIEW & REVISION PHASE ---
    elif state in [ChatState.PREVIEW_READY, ChatState.AWAITING_REVISION, ChatState.READY_FOR_PDF]:
        session_data.state = ChatState.AWAITING_REVISION
        if text_message and text_message != "resume":
            session_data.cv = await update_cv_via_instruction(session_data.cv, text_message)
            bot_response = "CV updated successfully based on your instructions! Check the live preview."
        else:
            bot_response = "Your preview is active. Type any instructions to tweak your CV or download your final PDF."

    return session_data, bot_response