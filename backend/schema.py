from pydantic import BaseModel, Field
from typing import List, Optional
from enum import Enum

class Address(BaseModel):
    line1: Optional[str] = Field(None, description="Street address")
    city: Optional[str] = None
    postal_code: Optional[str] = None
    country: Optional[str] = None

class PersonalInfo(BaseModel):
    first_name: Optional[str] = None  
    last_name: Optional[str] = None   
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
    profile_image_base64: Optional[str] = None
    about_me: Optional[str] = None
    personal_info: PersonalInfo = Field(default_factory=PersonalInfo)
    work_experience: List[WorkExperience] = Field(default_factory=list)
    education: List[Education] = Field(default_factory=list)
    mother_tongues: List[str] = Field(default_factory=list)
    other_languages: List[LanguageSkill] = Field(default_factory=list)
    digital_skills: List[str] = Field(default_factory=list)
    hobbies: List[str] = Field(default_factory=list)
    other_info: Optional[str] = None

class ChatState(str, Enum):
    AWAITING_PROFILE_PIC = "AWAITING_PROFILE_PIC"
    AWAITING_PASSPORT = "AWAITING_PASSPORT"
    AWAITING_ABOUT = "AWAITING_ABOUT"
    AWAITING_HIGHER_SEC = "AWAITING_HIGHER_SEC"
    AWAITING_SEC_EDU = "AWAITING_SEC_EDU"
    AWAITING_WORK = "AWAITING_WORK"
    AWAITING_LANGUAGES = "AWAITING_LANGUAGES"
    AWAITING_SKILLS = "AWAITING_SKILLS"
    AWAITING_OTHER = "AWAITING_OTHER"
    AWAITING_HOBBIES = "AWAITING_HOBBIES"
    # New manual collection and preview states
    AWAITING_MANUAL_PURPOSE = "AWAITING_MANUAL_PURPOSE"
    AWAITING_MANUAL_CONTACT = "AWAITING_MANUAL_CONTACT"
    AWAITING_MANUAL_SKILLS_HOBBIES = "AWAITING_MANUAL_SKILLS_HOBBIES"
    PREVIEW_READY = "PREVIEW_READY"
    AWAITING_REVISION = "AWAITING_REVISION"
    READY_FOR_PDF = "READY_FOR_PDF"

class SessionData(BaseModel):
    session_id: str
    state: ChatState = ChatState.AWAITING_PROFILE_PIC
    cv: EuropassCV = Field(default_factory=EuropassCV)
    missing_fields_queue: List[str] = Field(default_factory=list)