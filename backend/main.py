import uuid
import traceback
import os
import time
import json
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import Response, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
from fastapi.staticfiles import StaticFiles

from backend.schema import EuropassCV, SessionData, ChatState
from backend.pdf_generator import generate_pdf_from_cv
from backend.workflow import process_chat_interaction

app = FastAPI(title="Europass Chatbot API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

active_sessions = {}
SESSION_DURATION_SECONDS = 24 * 3600  # 24 Hours window

@app.get("/", response_class=HTMLResponse)
async def serve_root():
    """Explicitly serve index.html to prevent black/blank screen issues."""
    for path in ["index.html", "frontend/index.html"]:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
    return "<h1>Error: index.html not found! Please check your file structure.</h1>"

@app.get("/api/chat/start")
def start_chat():
    session_id = str(uuid.uuid4())
    active_sessions[session_id] = SessionData(
        session_id=session_id,
        state=ChatState.AWAITING_PROFILE_PIC,
        cv=EuropassCV(),
        created_at=time.time()
    )
    
    return {
        "session_id": session_id,
        "bot_message": "Hello! I am your Europass Assistant. You can upload your documents or type your details manually at any step. To get started, please upload a professional passport-sized photo of yourself. If you don't want a photo on your CV, just click Skip.",
        "state": active_sessions[session_id].state,
        "cv": active_sessions[session_id].cv.model_dump()
    }

@app.get("/api/session/download-slip/{session_id}")
async def download_slip(session_id: str):
    if session_id not in active_sessions:
        raise HTTPException(status_code=404, detail="Session not found.")
    
    session_data = active_sessions[session_id]
    export_data = {
        "version": "1.0",
        "timestamp": time.time(),
        "cv_data": session_data.cv.model_dump()
    }
    slip_json = json.dumps(export_data, indent=2)
    
    return Response(
        content=slip_json,
        media_type="application/json",
        headers={"Content-Disposition": "attachment; filename=europass_slip.json"}
    )

@app.post("/api/session/restore-slip")
async def restore_slip(file: UploadFile = File(...)):
    try:
        content = await file.read()
        data = json.loads(content.decode("utf-8"))
        cv_data = data.get("cv_data", {})
        
        new_session_id = str(uuid.uuid4())
        restored_cv = EuropassCV.model_validate(cv_data)
        
        active_sessions[new_session_id] = SessionData(
            session_id=new_session_id,
            state=ChatState.PREVIEW_READY,
            cv=restored_cv,
            created_at=time.time()
        )
        
        return {
            "session_id": new_session_id,
            "bot_message": "Slip successfully loaded! Your previous CV details have been restored. You can review or edit them below.",
            "state": ChatState.PREVIEW_READY,
            "cv": restored_cv.model_dump()
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail="Invalid slip file format.")

@app.post("/api/chat/message")
async def chat_message(
    session_id: str = Form(...),
    text_message: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None)
):
    if session_id not in active_sessions:
        raise HTTPException(status_code=404, detail="Session expired or not found. Please refresh the page or upload your slip.")
    
    session_data = active_sessions[session_id]
    
    # Check 24-hour expiration window
    if time.time() - getattr(session_data, "created_at", time.time()) > SESSION_DURATION_SECONDS:
        raise HTTPException(status_code=401, detail="Session token has expired (24-hour limit reached). Please download your slip or re-upload your slip to continue.")

    # Ignore token validation dummy text if sent from modal resume check
    if text_message == "resume":
        return {
            "bot_message": f"Session resumed successfully! Current stage: {session_data.state.value}",
            "state": session_data.state,
            "cv": session_data.cv.model_dump()
        }

    try:
        updated_session, bot_response = await process_chat_interaction(session_data, text_message, file)
        active_sessions[session_id] = updated_session
        
        return {
            "bot_message": bot_response,
            "state": updated_session.state,
            "cv": updated_session.cv.model_dump()
        }
    except Exception as e:
        print("\n=== AI CRASH REPORT ===")
        traceback.print_exc()
        print("=======================\n")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/generate-pdf/{session_id}")
async def generate_pdf(session_id: str):
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

# Mount static files safely depending on folder layout
if os.path.exists("frontend"):
    app.mount("/", StaticFiles(directory="frontend"), name="frontend")
else:
    app.mount("/", StaticFiles(directory="."), name="root_static")