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
        D  discovery          (notes / link)
        E  discovery_date
        F  tech               (notes / link)
        G  tech_date
        H  pricing            (notes / link)
        I  pricing_date
        J  onboarding         (notes / link)
        K  onboarding_date
        L  client             (notes / link)
        M  client_date
        N  status             (scheduled | completed | canceled | missed)
        O  count              (number of meetings held)
        P  calendar_event_id  (managed by outreach agent – write here after creating event)
    """
    ID                = 0
    PEOPLE_ID         = 1
    COMPANY_ID        = 2
    DISCOVERY         = 3
    DISCOVERY_DATE    = 4
    TECH              = 5
    TECH_DATE         = 6
    PRICING           = 7
    PRICING_DATE      = 8
    ONBOARDING        = 9
    ONBOARDING_DATE   = 10
    CLIENT            = 11
    CLIENT_DATE       = 12
    STATUS            = 13
    COUNT             = 14
    CALENDAR_EVENT_ID = 15  # agent-managed; add this column to the sheet

    TOTAL_COLUMNS = 16


class SheetNames:
    """Tab names inside the 'Fellowship CRM' Google Sheets file."""
    PEOPLE    = "People"
    COMPANIES = "Companies"
    DEMOS     = "Demos"
    EMAILS    = "Emails"
    THREADS   = "Threads"
