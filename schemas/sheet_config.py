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


class ActionColumns:
    """
    Sheet: Actions
    Columns (0-based):
        A  id
        B  kind            (email | calendar)
        C  status          (pending | confirming | confirmed | canceled)
        D  created_at
        E  confirmed_at
        F  email_type      (prospect_outreach | client_outreach | followup_email | demo_invite |
                            inbox_reply_interested | inbox_reply_not_interested | inbox_reply_demo_request)
        G  recipient_email
        H  recipient_name
        I  subject
        J  people_id
        K  event_type      (demo_discovery | demo_tech | demo_pricing | demo_onboarding | demo_client)
        L  event_title
        M  attendees       (comma-separated)
        N  start_time
        O  end_time
        P  demo_id
        Q  source_email_id (inbox email id this action replies to)
        R  body            (pre-generated HTML body for inbox reply actions)
    """
    ID              = 0
    KIND            = 1
    STATUS          = 2
    CREATED_AT      = 3
    CONFIRMED_AT    = 4
    EMAIL_TYPE      = 5
    RECIPIENT_EMAIL = 6
    RECIPIENT_NAME  = 7
    SUBJECT         = 8
    PEOPLE_ID       = 9
    EVENT_TYPE      = 10
    EVENT_TITLE     = 11
    ATTENDEES       = 12
    START_TIME      = 13
    END_TIME        = 14
    DEMO_ID         = 15
    SOURCE_EMAIL_ID = 16
    BODY            = 17

    TOTAL_COLUMNS   = 18


class EmailColumns:
    """
    Sheet: Emails
    Columns (0-based):
        A  id
        B  message_id        (Gmail message ID — deduplication key)
        C  from_email
        D  from_name
        E  people_id         (matched Person.id, or "" if unknown sender)
        F  subject
        G  body_snippet      (first 500 chars of plain-text body)
        H  received_at       (ISO datetime)
        I  category          (interested | not_interested | manual | demo_request | other)
        J  status            (new | pending_response | responded | ignored)
        K  response_action_id (linked Actions.id, written after creating an action)
        L  note              (LLM-generated summary of email intent/key points)
    """
    ID                 = 0
    MESSAGE_ID         = 1
    FROM_EMAIL         = 2
    FROM_NAME          = 3
    PEOPLE_ID          = 4
    SUBJECT            = 5
    BODY_SNIPPET       = 6
    RECEIVED_AT        = 7
    CATEGORY           = 8
    STATUS             = 9
    RESPONSE_ACTION_ID = 10
    NOTE               = 11

    TOTAL_COLUMNS = 12


class SheetNames:
    """Tab names inside the 'Fellowship CRM' Google Sheets file."""
    PEOPLE    = "People"
    COMPANIES = "Companies"
    DEMOS     = "Demos"
    EMAILS    = "Emails"
    THREADS   = "Threads"
    ACTIONS   = "Actions"
