from pydantic import BaseModel, Field
from typing import List, Optional
from enum import Enum

# --- 1. Europass CV Structures ---

class Address(BaseModel):
    line1: Optional[str] = Field(None, description="Street address")
    city: Optional[str] = None
    postal_code: Optional[str] = None
    country: Optional[str] = None

class PersonalInfo(BaseModel):
    first_name: Optional[str] = None  # Made optional for early chat stages
    last_name: Optional[str] = None   # Made optional for early chat stages
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[Address] = None
    date_of_birth: Optional[str] = Field(None, description="Format: DD/MM/YYYY")
    nationality: Optional[List[str]] = Field(default_factory=list)

class WorkExperience(BaseModel):
    title: str = Field(..., description="Job title")
    employer: str
    city: Optional[str] = None
    country: Optional[str] = None
    start_date: str = Field(..., description="Format: MM/YYYY")
    end_date: Optional[str] = Field(None, description="Format: MM/YYYY or 'Ongoing'")
    description: Optional[str] = Field(None, description="Main responsibilities and achievements")

class Education(BaseModel):
    title: str = Field(..., description="Qualification awarded")
    organization: str = Field(..., description="Educational institution name")
    city: Optional[str] = None
    country: Optional[str] = None
    start_date: str = Field(..., description="Format: MM/YYYY")
    end_date: Optional[str] = Field(None, description="Format: MM/YYYY or 'Ongoing'")
    description: Optional[str] = Field(None, description="Subjects studied / skills acquired")

class LanguageSkill(BaseModel):
    language: str
    listening: str = Field(..., description="Strictly one of: A1, A2, B1, B2, C1, C2")
    reading: str = Field(..., description="Strictly one of: A1, A2, B1, B2, C1, C2")
    spoken_interaction: str = Field(..., description="Strictly one of: A1, A2, B1, B2, C1, C2")
    spoken_production: str = Field(..., description="Strictly one of: A1, A2, B1, B2, C1, C2")
    writing: str = Field(..., description="Strictly one of: A1, A2, B1, B2, C1, C2")

class EuropassCV(BaseModel):
    personal_info: PersonalInfo = Field(default_factory=PersonalInfo)
    work_experience: List[WorkExperience] = Field(default_factory=list)
    education: List[Education] = Field(default_factory=list)
    mother_tongues: List[str] = Field(default_factory=list)
    other_languages: List[LanguageSkill] = Field(default_factory=list)
    digital_skills: List[str] = Field(default_factory=list)

# --- 2. Chatbot State Management ---

class ChatState(str, Enum):
    AWAITING_PASSPORT = "AWAITING_PASSPORT"
    AWAITING_DEGREES = "AWAITING_DEGREES"
    AWAITING_CERTIFICATES = "AWAITING_CERTIFICATES"
    REVIEWING_MISSING_DATA = "REVIEWING_MISSING_DATA"
    READY_FOR_PDF = "READY_FOR_PDF"

class SessionData(BaseModel):
    session_id: str
    state: ChatState = ChatState.AWAITING_PASSPORT
    cv: EuropassCV = Field(default_factory=EuropassCV)
    missing_fields_queue: List[str] = Field(default_factory=list)