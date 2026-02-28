# CRM schemas have moved to the global schemas package:
#   ai-outreach/schemas/crm.py          → Person, Company, Demo, CRMContext
#   ai-outreach/schemas/sheet_config.py → PeopleColumns, CompanyColumns, DemoColumns, SheetNames
#
# Agent configuration has moved to:
#   agent/config.py → OutreachAgentConfig
#
# Re-exported here for backwards compatibility.
from agent.config import OutreachAgentConfig  # noqa: F401
from schemas.crm import CRMContext, Company, Demo, Person, PersonWithCompany  # noqa: F401
from schemas.sheet_config import (  # noqa: F401
    CompanyColumns,
    DemoColumns,
    PeopleColumns,
    SheetNames,
)
