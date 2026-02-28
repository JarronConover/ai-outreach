from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
import uuid


class Person(BaseModel):
    """Person record for the People sheet."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    company_id: str
    email: str
    title: str
    linkedin: Optional[str] = None
    stage: str = "PROSPECTING"
    last_response: Optional[datetime] = None
    last_contact: Optional[datetime] = None
    last_demo_id: Optional[str] = None
    next_demo_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class PeopleOutput(BaseModel):
    """Output containing a list of Person records."""
    people: List[Person]
