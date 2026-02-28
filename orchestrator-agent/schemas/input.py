from pydantic import BaseModel, Field
from typing import List, Optional


class PipelineInput(BaseModel):
    """Input for the full pipeline run."""
    industry: str
    company_size: str = "any size"
    roles_to_target: List[str]
    pain_points: List[str]
    location: Optional[str] = None
    num_companies: int = Field(default=5, ge=1, le=20)
    num_people_per_company: int = Field(default=2, ge=1, le=5)
    stages: List[str] = Field(default=["prospect"])
    enable_post_deduplication: bool = True
