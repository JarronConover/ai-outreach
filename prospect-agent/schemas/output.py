from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
import uuid


class Person(BaseModel):
    """Person record for the People sheet."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    company_id: str
    company_name: Optional[str] = None
    email: str
    title: str
    linkedin: Optional[str] = None
    stage: str = "prospect"
    last_response: Optional[datetime] = None
    last_contact: Optional[datetime] = None
    last_demo_id: Optional[str] = None
    next_demo_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class Company(BaseModel):
    """Company record returned by the prospecting agent."""
    name: str
    website: Optional[str] = None
    industry: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip: Optional[str] = None
    phone: Optional[str] = None
    employee_count: Optional[str] = None


class PeopleOutput(BaseModel):
    """Output containing a list of Person records and their companies."""
    people: List[Person]
    companies: List[Company] = Field(default_factory=list)
