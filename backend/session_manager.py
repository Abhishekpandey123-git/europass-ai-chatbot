import time
import json
import uuid
from backend.schema import SessionData, ChatState, EuropassCV

# In-memory storage dictionary (can be replaced with a database later)
ACTIVE_SESSIONS = {}
SESSION_DURATION_SECONDS = 24 * 3600  # 24 Hours

def create_new_session() -> tuple[str, SessionData]:
    token = str(uuid.uuid4())
    session_data = SessionData(
        session_id=token,
        state=ChatState.AWAITING_PROFILE_PIC,
        cv=EuropassCV(),
        created_at=time.time()
    )
    ACTIVE_SESSIONS[token] = session_data
    return token, session_data

def get_session(token: str) -> SessionData | None:
    session_data = ACTIVE_SESSIONS.get(token)
    if not session_data:
        return None
    
    # Check if 24-hour window has expired
    if time.time() - session_data.created_at > SESSION_DURATION_SECONDS:
        # Expired, but keep data accessible if they restore via slip, 
        # or remove active session. We'll handle restoration separately.
        pass
        
    return session_data

def export_session_slip(session_data: SessionData) -> str:
    """Exports session CV data as a clean JSON string 'slip'."""
    export_data = {
        "version": "1.0",
        "timestamp": time.time(),
        "cv_data": session_data.cv.model_dump()
    }
    return json.dumps(export_data, indent=2)

def import_session_slip(json_content: str) -> tuple[str, SessionData]:
    """Creates a brand new 24-hour session token loaded with slip data."""
    data = json.loads(json_content)
    cv_data = data.get("cv_data", {})
    
    token = str(uuid.uuid4())
    restored_cv = EuropassCV.model_validate(cv_data)
    
    session_data = SessionData(
        session_id=token,
        state=ChatState.PREVIEW_READY,  # Jump straight to preview/revision since data is loaded
        cv=restored_cv,
        created_at=time.time()
    )
    ACTIVE_SESSIONS[token] = session_data
    return token, session_data