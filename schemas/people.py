from pydantic import BaseModel, Field, EmailStr
from typing import Optional
from datetime import datetime
from enum import Enum
import uuid


class PeopleStage(str, Enum):
    """Pipeline stage for a person."""
    PROSPECTING = "PROSPECTING"
    INTERESTED = "INTERESTED"
    QUALIFIED = "QUALIFIED"
    NEGOTIATING = "NEGOTIATING"
    WON = "WON"
    LOST = "LOST"


class PeopleCreate(BaseModel):
    """Schema for creating a person."""
    name: str
    company_id: str
    email: str
    linkedin: Optional[str] = None
    phone: Optional[str] = None
    title: str
    stage: PeopleStage = PeopleStage.PROSPECTING


class People(BaseModel):
    """Full People record with all fields."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    company_id: str
    email: str
    linkedin: Optional[str] = None
    phone: Optional[str] = None
    title: str
    stage: PeopleStage
    last_response: Optional[datetime] = None
    last_contact: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        use_enum_values = True
