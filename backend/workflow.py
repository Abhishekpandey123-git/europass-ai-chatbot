import base64
import os
import shutil
from backend.schema import SessionData, ChatState
from backend.extractor import parse_document_with_llamaparse
from backend.openrouter_service import (
    parse_document_with_openrouter_text as parse_document_with_gemini_text,
    generate_ai_about_me_openrouter as generate_ai_about_me,
    update_cv_via_instruction_openrouter as update_cv_via_instruction
)

async def process_chat_interaction(session_data: SessionData, text_message: str = None, file = None):
    bot_response = ""
    text_lower = text_message.lower().strip() if text_message else ""
    is_skip = "skip" in text_lower or "done" in text_lower

    state = session_data.state

    # Helper function to handle cloud-based document parsing efficiently
    async def process_doc_with_cloud(file_obj, category_name: str):
        temp_file_path = f"temp_{file_obj.filename}"
        with open(temp_file_path, "wb") as buffer:
            shutil.copyfileobj(file_obj.file, buffer)
        try:
            # Offload heavy parsing to LlamaParse API
            parsed_markdown = await parse_document_with_llamaparse(temp_file_path)
            # Pass the parsed text into the OpenRouter text extraction workflow
            session_data.cv = await parse_document_with_gemini_text(parsed_markdown, session_data.cv, category_name)
        finally:
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)

    if state == ChatState.AWAITING_PROFILE_PIC:
        if file:
            file_bytes = await file.read()
            session_data.cv.profile_image_base64 = base64.b64encode(file_bytes).decode('utf-8')
            session_data.state = ChatState.AWAITING_PASSPORT
            bot_response = "Profile photo saved! Next, please upload your Passport or type your personal details manually."
        elif is_skip:
            session_data.state = ChatState.AWAITING_PASSPORT
            bot_response = "Skipped photo. Please upload your Passport or type your personal details manually."
        else:
            bot_response = "Please upload a professional profile picture (or click Skip)."

    elif state == ChatState.AWAITING_PASSPORT:
        if file:
            await process_doc_with_cloud(file, "Passport Personal Details")
            session_data.state = ChatState.AWAITING_ABOUT
            bot_response = "Passport details extracted! Next, what would you like in your 'About' section? (Type your summary or click 'Write with AI')."
        elif text_message and not is_skip:
            session_data.cv.other_info = (session_data.cv.other_info or "") + f"\nPassport / Personal Details: {text_message}"
            session_data.state = ChatState.AWAITING_ABOUT
            bot_response = "Manual personal details saved! Next, what would you like in your 'About' section? (Type your summary or click 'Write with AI')."
        else:
            bot_response = "Please upload your passport document or type your details manually."

    elif state == ChatState.AWAITING_ABOUT:
        if text_message:
            if "write" in text_lower or text_lower == "generate":
                session_data.cv.about_me = await generate_ai_about_me(session_data.cv)
                bot_response = "Generated professional summary using AI!"
            else:
                session_data.cv.about_me = text_message
                bot_response = "Saved your About section!"

            session_data.state = ChatState.AWAITING_HIGHER_SEC
            bot_response += " Now, upload your Higher Secondary (Class XII) document or type the details manually."
        else:
            bot_response = "Please type your About summary or type 'write' to let AI generate it."

    elif state == ChatState.AWAITING_HIGHER_SEC:
        if file:
            await process_doc_with_cloud(file, "Higher Secondary Education")
            session_data.state = ChatState.AWAITING_SEC_EDU
            bot_response = "Class XII processed! Next, upload your Secondary Education (Class X) document or type it manually."
        elif text_message and not is_skip:
            session_data.cv.other_info = (session_data.cv.other_info or "") + f"\nHigher Secondary Education: {text_message}"
            session_data.state = ChatState.AWAITING_SEC_EDU
            bot_response = "Class XII details saved manually! Next, upload your Secondary Education (Class X) document or type it manually."
        elif is_skip:
            session_data.state = ChatState.AWAITING_SEC_EDU
            bot_response = "Skipped Higher Secondary. Upload your Secondary Education (Class X) document or type it manually."
        else:
            bot_response = "Upload your Class XII document, type details manually, or click Skip."

    elif state == ChatState.AWAITING_SEC_EDU:
        if file:
            await process_doc_with_cloud(file, "Secondary Education")
            session_data.state = ChatState.AWAITING_WORK
            bot_response = "Class X processed! Next, upload any work experience documents or type them manually (or click Skip)."
        elif text_message and not is_skip:
            session_data.cv.other_info = (session_data.cv.other_info or "") + f"\nSecondary Education: {text_message}"
            session_data.state = ChatState.AWAITING_WORK
            bot_response = "Class X details saved manually! Next, upload any work experience documents or type them manually (or click Skip)."
        elif is_skip:
            session_data.state = ChatState.AWAITING_WORK
            bot_response = "Skipped Class X. Upload any work experience documents or type them manually (or click Skip)."
        else:
            bot_response = "Upload your Class X document, type details manually, or click Skip."

    elif state == ChatState.AWAITING_WORK:
        if file:
            await process_doc_with_cloud(file, "Work Experience")
            bot_response = "Work experience added! Upload another, type details manually, or click Skip/Done."
        elif text_message and not is_skip:
            session_data.cv.other_info = (session_data.cv.other_info or "") + f"\nWork Experience: {text_message}"
            bot_response = "Work experience added manually! Upload another, type details manually, or click Skip/Done."
        elif is_skip:
            session_data.state = ChatState.AWAITING_LANGUAGES
            bot_response = "Upload any language test certificates or type them manually (or click Skip)."
        else:
            bot_response = "Upload your work experience document, type details manually, or click Skip/Done."

    elif state == ChatState.AWAITING_LANGUAGES:
        if file:
            await process_doc_with_cloud(file, "Language Results")
            bot_response = "Languages added! Upload another, type details manually, or click Skip/Done."
        elif text_message and not is_skip:
            session_data.cv.other_info = (session_data.cv.other_info or "") + f"\nLanguages: {text_message}"
            bot_response = "Languages added manually! Upload another, type details manually, or click Skip/Done."
        elif is_skip:
            session_data.state = ChatState.AWAITING_SKILLS
            bot_response = "Type a comma-separated list of your technical skills (e.g. Python, SQL, AI)."
        else:
            bot_response = "Upload language certificate, type details manually, or click Skip."

    elif state == ChatState.AWAITING_SKILLS:
        if text_message:
            session_data.cv.digital_skills = [s.strip() for s in text_message.split(",")]
            session_data.state = ChatState.AWAITING_OTHER
            bot_response = "Skills saved! Any other information to add? (Click Skip if no)."

    elif state == ChatState.AWAITING_OTHER:
        if text_message and not is_skip:
            session_data.cv.other_info = text_message
        session_data.state = ChatState.AWAITING_HOBBIES
        bot_response = "List your hobbies and interests (comma-separated), or type 'skip'."

    elif state == ChatState.AWAITING_HOBBIES:
        if text_message and not is_skip:
            session_data.cv.hobbies = [h.strip() for h in text_message.split(",")]
        session_data.state = ChatState.AWAITING_MANUAL_PURPOSE
        bot_response = "Hobbies saved! Now let's gather details not found in documents.\n\nWhat is your purpose of application and target University/Program?"

    # --- MANUAL GAP-FILLING STAGES ---
    elif state == ChatState.AWAITING_MANUAL_PURPOSE:
        if text_message:
            session_data.cv.other_info = (session_data.cv.other_info or "") + f"\nPurpose & Program: {text_message}"
        session_data.state = ChatState.AWAITING_MANUAL_CONTACT
        bot_response = "Saved! Please provide your phone number and current home address."

    elif state == ChatState.AWAITING_MANUAL_CONTACT:
        if text_message:
            session_data.cv.personal_info.phone = text_message
        session_data.state = ChatState.AWAITING_MANUAL_SKILLS_HOBBIES
        bot_response = "Contact info saved! Finally, list any personal soft skills (comma-separated)."

    elif state == ChatState.AWAITING_MANUAL_SKILLS_HOBBIES:
        if text_message:
            session_data.cv.other_info = (session_data.cv.other_info or "") + f"\nPersonal Skills: {text_message}"

        session_data.state = ChatState.PREVIEW_READY
        bot_response = "All details collected! Your CV preview is ready. You can review it, chat with me to make any changes, or click Generate PDF below."

    elif state in [ChatState.PREVIEW_READY, ChatState.AWAITING_REVISION]:
        if text_message:
            session_data.cv = await update_cv_via_instruction(session_data.cv, text_message)
            bot_response = "I have updated your CV based on your instructions! Check the changes or ask for further edits."
        session_data.state = ChatState.AWAITING_REVISION

    return session_data, bot_response