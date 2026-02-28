from pydantic import BaseModel, Field
from typing import List, Optional
import uuid


class StageResult(BaseModel):
    """Result from a single pipeline stage."""
    stage: str
    status: str  # "completed", "skipped", "failed"
    people_written: int = 0
    people_found: int = 0
    duplicates_skipped: int = 0
    new_person_ids: List[str] = Field(default_factory=list)
    error: Optional[str] = None


class PipelineResult(BaseModel):
    """Full result from an orchestrated pipeline run."""
    pipeline_job_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    stages: List[StageResult] = Field(default_factory=list)
