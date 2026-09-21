import uuid
import traceback
import os
import time
import json
import hashlib
import hmac
import secrets
from collections import defaultdict, deque
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import Response, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
from pydantic import BaseModel

load_dotenv()

from backend.schema import EuropassCV, SessionData, ChatState
from backend.pdf_generator import generate_pdf_from_cv
from backend.workflow import process_chat_interaction

app = FastAPI(title="Europass Chatbot API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in os.getenv("ALLOWED_ORIGINS", "http://127.0.0.1:8000,http://localhost:8000").split(",") if origin.strip()],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

active_sessions = {}
SESSION_DURATION_SECONDS = 24 * 3600  # 24 Hours window
MAX_UPLOAD_BYTES = 10 * 1024 * 1024
SESSION_SECRET = os.getenv("SESSION_SECRET")
if not SESSION_SECRET:
    SESSION_SECRET = secrets.token_urlsafe(32)
request_log = defaultdict(deque)

@app.middleware("http")
async def security_middleware(request, call_next):
    client_ip = request.client.host if request.client else "unknown"
    now = time.monotonic()
    requests = request_log[client_ip]
    while requests and now - requests[0] > 60:
        requests.popleft()
    if request.url.path.startswith("/api/"):
        if len(requests) >= 30:
            return Response(content="Too many requests", status_code=429, media_type="text/plain")
        requests.append(now)
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self' https://cdnjs.cloudflare.com; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'"
    return response

def _session_token(raw_id: str) -> str:
    signature = hmac.new(SESSION_SECRET.encode(), raw_id.encode(), hashlib.sha256).hexdigest()
    return f"{raw_id}.{signature}"

def _require_session(session_id: str) -> SessionData:
    raw_id, separator, signature = session_id.rpartition(".")
    expected = hmac.new(SESSION_SECRET.encode(), raw_id.encode(), hashlib.sha256).hexdigest()
    if not separator or not hmac.compare_digest(signature, expected) or session_id not in active_sessions:
        raise HTTPException(status_code=404, detail="Session not found.")
    session_data = active_sessions[session_id]
    if time.time() - getattr(session_data, "created_at", time.time()) > SESSION_DURATION_SECONDS:
        raise HTTPException(status_code=401, detail="Session expired.")
    return session_data

class CVUpdateRequest(BaseModel):
    session_id: str
    cv: EuropassCV

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
    session_id = _session_token(str(uuid.uuid4()))
    active_sessions[session_id] = SessionData(
        session_id=session_id,
        state=ChatState.GATHERING_PERSONAL,
        cv=EuropassCV(),
        created_at=time.time()
    )
    
    return {
        "session_id": session_id,
        "bot_message": "Hello! I am your Europass Assistant. Let's build your CV step by step. First, please upload your **Passport or Personal Information document** (or type your details freely, or click Skip).",
        "state": active_sessions[session_id].state,
        "cv": active_sessions[session_id].cv.model_dump()
    }

@app.get("/api/session/download-slip/{session_id}")
async def download_slip(session_id: str):
    session_data = _require_session(session_id)
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
        content = await file.read(MAX_UPLOAD_BYTES + 1)
        if len(content) > MAX_UPLOAD_BYTES:
            raise ValueError("Slip file is too large")
        data = json.loads(content.decode("utf-8"))
        cv_data = data.get("cv_data", {})
        
        new_session_id = _session_token(str(uuid.uuid4()))
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

@app.post("/api/session/update-cv")
async def update_cv(request: CVUpdateRequest):
    session_data = _require_session(request.session_id)

    session_data.cv = request.cv
    session_data.state = ChatState.AWAITING_REVISION
    return {"state": session_data.state, "cv": session_data.cv.model_dump()}

@app.post("/api/chat/message")
async def chat_message(
    session_id: str = Form(...),
    text_message: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None)
):
    session_data = _require_session(session_id)
    if file and file.size and file.size > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Uploaded file is too large.")
    if file and file.content_type not in {"application/pdf", "image/jpeg", "image/png"}:
        raise HTTPException(status_code=415, detail="Only PDF, JPEG, and PNG files are supported.")

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
        raise HTTPException(status_code=502, detail="Document processing failed. Please try again.")

@app.get("/api/generate-pdf/{session_id}")
async def generate_pdf(session_id: str):
    try:
        cv_data = _require_session(session_id).cv
        pdf_bytes = generate_pdf_from_cv(cv_data)
        
        return Response(
            content=pdf_bytes, 
            media_type="application/pdf",
            headers={"Content-Disposition": "attachment; filename=Europass_CV.pdf"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail="PDF generation failed.")

# Mount static files safely depending on folder layout
if os.path.exists("frontend"):
    app.mount("/", StaticFiles(directory="frontend"), name="frontend")
else:
    app.mount("/", StaticFiles(directory="."), name="root_static")