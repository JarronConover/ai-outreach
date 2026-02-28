"""
Column index constants and sheet name constants for the Fellowship CRM
Google Sheets file.

Every column is 0-based (matching Python list indexing).
These map exactly to the "Fellowship CRM" spreadsheet layout described below.

Spreadsheet title : Fellowship CRM
Sheets            : People, Companies, Demos, Emails, Threads
"""


class PeopleColumns:
    """
    Sheet: People
    Columns (0-based):
        A  id
        B  name
        C  company_id
        D  email
        E  phone
        F  linkedIn
        G  title
        H  stage
        I  last_demo_id
        J  next_demo_id
        K  last_response
        L  last_contact
        M  last_response_date
        N  last_contact_date
    """
    ID                = 0
    NAME              = 1
    COMPANY_ID        = 2
    EMAIL             = 3
    PHONE             = 4
    LINKEDIN          = 5
    TITLE             = 6
    STAGE             = 7
    LAST_DEMO_ID      = 8
    NEXT_DEMO_ID      = 9
    LAST_RESPONSE     = 10
    LAST_CONTACT      = 11
    LAST_RESPONSE_DATE = 12
    LAST_CONTACT_DATE = 13

    TOTAL_COLUMNS = 14


class CompanyColumns:
    """
    Sheet: Companies
    Columns (0-based):
        A  id
        B  name
        C  address
        D  city
        E  state
        F  zip
        G  phone
        H  website
        I  industry
        J  employee_count
    """
    ID             = 0
    NAME           = 1
    ADDRESS        = 2
    CITY           = 3
    STATE          = 4
    ZIP            = 5
    PHONE          = 6
    WEBSITE        = 7
    INDUSTRY       = 8
    EMPLOYEE_COUNT = 9

    TOTAL_COLUMNS = 10


class DemoColumns:
    """
    Sheet: Demos
    Columns (0-based):
        A  id
        B  people_id
        C  company_id
        D  type               (discovery | tech | pricing | onboarding | client)
        E  date               (date/time of the meeting)
        F  status             (scheduled | completed | canceled | missed)
        G  count              (number of meetings held)
        H  event_id           (managed by outreach agent – written after creating event)
    """
    ID        = 0
    PEOPLE_ID = 1
    COMPANY_ID = 2
    TYPE      = 3
    DATE      = 4
    STATUS    = 5
    COUNT     = 6
    EVENT_ID  = 7  # agent-managed; Google Calendar event ID

    TOTAL_COLUMNS = 8


class SheetNames:
    """Tab names inside the 'Fellowship CRM' Google Sheets file."""
    PEOPLE    = "People"
    COMPANIES = "Companies"
    DEMOS     = "Demos"
    EMAILS    = "Emails"
    THREADS   = "Threads"
