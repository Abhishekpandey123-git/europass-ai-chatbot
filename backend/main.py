import uuid
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import Response
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional

from backend.schema import EuropassCV, SessionData, ChatState
from backend.pdf_generator import generate_pdf_from_cv
# We will update llm_service next!
from backend.llm_service import process_chat_interaction

app = FastAPI(title="Europass Chatbot API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory database to store active user sessions
active_sessions = {}

@app.get("/api/chat/start")
def start_chat():
    """ Initializes a new conversational session. """
    session_id = str(uuid.uuid4())
    active_sessions[session_id] = SessionData(session_id=session_id)
    
    return {
        "session_id": session_id,
        "bot_message": "Hello! I am your Europass Assistant. To get started, please upload a picture of your passport or ID so I can extract your basic personal details."
    }

@app.post("/api/chat/message")
async def chat_message(
    session_id: str = Form(...),
    text_message: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None)
):
    """ Handles all incoming chat messages and files. """
    if session_id not in active_sessions:
        raise HTTPException(status_code=404, detail="Session expired or not found. Please refresh the page.")
    
    session_data = active_sessions[session_id]
    
    try:
        # Pass the input and the current memory to our LLM engine
        updated_session, bot_response = await process_chat_interaction(session_data, text_message, file)
        
        # Save the updated memory
        active_sessions[session_id] = updated_session
        
        return {
            "bot_message": bot_response,
            "state": updated_session.state
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/generate-pdf/{session_id}")
async def generate_pdf(session_id: str):
    """ Renders the PDF using the stored session data. """
    if session_id not in active_sessions:
        raise HTTPException(status_code=404, detail="Session not found.")
    
    try:
        cv_data = active_sessions[session_id].cv
        pdf_bytes = generate_pdf_from_cv(cv_data)
        
        return Response(
            content=pdf_bytes, 
            media_type="application/pdf",
            headers={"Content-Disposition": "attachment; filename=Europass_CV.pdf"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {str(e)}")