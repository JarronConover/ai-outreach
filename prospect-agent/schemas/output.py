from pydantic import BaseModel, Field
from typing import List
import uuid


class Lead(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    company: str
    email: str
    title: str
    stage: str = "PROSPECTING"
    last_message: str = ""
    next_action: str = "Send outreach email"


class LeadsOutput(BaseModel):
    leads: List[Lead]
