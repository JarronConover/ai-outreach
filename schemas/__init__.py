# Global CRM schemas for the Fellowship CRM Google Sheets database.
# Used by all agents in this project.
from schemas.crm import (
    CRMContext,
    Company,
    Demo,
    DemoStatus,
    InboxEmail,
    Person,
    PersonWithCompany,
    Stage,
    Thread,
)
from schemas.sheet_config import CompanyColumns, DemoColumns, PeopleColumns, SheetNames

__all__ = [
    "CRMContext",
    "Company",
    "Demo",
    "DemoStatus",
    "InboxEmail",
    "Person",
    "PersonWithCompany",
    "Stage",
    "Thread",
    "CompanyColumns",
    "DemoColumns",
    "PeopleColumns",
    "SheetNames",
]
