import base64
from backend.schema import SessionData, ChatState
from backend.gemini_service import parse_document_with_gemini, generate_ai_about_me

async def process_chat_interaction(session_data: SessionData, text_message: str = None, file = None):
    bot_response = ""
    text_lower = text_message.lower().strip() if text_message else ""
    is_skip = "skip" in text_lower or "done" in text_lower

    state = session_data.state

    if state == ChatState.AWAITING_PROFILE_PIC:
        if file:
            file_bytes = await file.read()
            session_data.cv.profile_image_base64 = base64.b64encode(file_bytes).decode('utf-8')
            session_data.state = ChatState.AWAITING_PASSPORT
            bot_response = "Profile photo saved! Next, please upload your Passport."
        elif is_skip:
            session_data.state = ChatState.AWAITING_PASSPORT
            bot_response = "Skipped photo. Please upload your Passport."
        else:
            bot_response = "Please upload a professional profile picture (or click Skip)."

    elif state == ChatState.AWAITING_PASSPORT:
        if file:
            session_data.cv = await parse_document_with_gemini(file, session_data.cv, "Passport Personal Details")
            session_data.state = ChatState.AWAITING_ABOUT
            bot_response = "Passport details extracted! Next, what would you like in your 'About' section? (Type your summary or click 'Write with AI')."
        else:
            bot_response = "Please upload your passport document."

    elif state == ChatState.AWAITING_ABOUT:
        if text_message:
            if "write" in text_lower or text_lower == "generate":
                # Real AI Generation using Gemini based on extracted CV details
                session_data.cv.about_me = await generate_ai_about_me(session_data.cv)
                bot_response = "Generated professional summary using AI!"
            else:
                session_data.cv.about_me = text_message
                bot_response = "Saved your About section!"
            
            session_data.state = ChatState.AWAITING_HIGHER_SEC
            bot_response += " Now, upload your Higher Secondary (Class XII) document."
        else:
            bot_response = "Please type your About summary or type 'write' to let AI generate it."

    elif state == ChatState.AWAITING_HIGHER_SEC:
        if file:
            session_data.cv = await parse_document_with_gemini(file, session_data.cv, "Higher Secondary Education")
            session_data.state = ChatState.AWAITING_SEC_EDU
            bot_response = "Class XII processed! Next, upload your Secondary Education (Class X) document."
        else:
            bot_response = "Upload your Class XII document, or click Skip."

    elif state == ChatState.AWAITING_SEC_EDU:
        if file:
            session_data.cv = await parse_document_with_gemini(file, session_data.cv, "Secondary Education")
            session_data.state = ChatState.AWAITING_WORK
            bot_response = "Class X processed! Next, upload any work experience documents (or click Skip)."
        else:
            bot_response = "Upload your Class X document, or click Skip."

    elif state == ChatState.AWAITING_WORK:
        if file:
            session_data.cv = await parse_document_with_gemini(file, session_data.cv, "Work Experience")
            bot_response = "Work experience added! Upload another, or click Skip/Done."
        elif is_skip:
            session_data.state = ChatState.AWAITING_LANGUAGES
            bot_response = "Upload any language test certificates, or click Skip."

    elif state == ChatState.AWAITING_LANGUAGES:
        if file:
            session_data.cv = await parse_document_with_gemini(file, session_data.cv, "Language Results")
            bot_response = "Languages added! Upload another, or click Skip/Done."
        elif is_skip:
            session_data.state = ChatState.AWAITING_SKILLS
            bot_response = "Type a comma-separated list of your technical skills (e.g. Python, SQL, AI)."

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
        session_data.state = ChatState.READY_FOR_PDF
        bot_response = "Your CV is complete! Click Generate PDF below."

    return session_data, bot_response