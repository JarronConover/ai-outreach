"""Custom exceptions for the outreach agent."""


class OutreachAgentError(Exception):
    """Base exception for all outreach agent errors."""
    pass


class GoogleAPIError(OutreachAgentError):
    """Base exception for Google API errors."""
    pass


class GmailAPIError(GoogleAPIError):
    """Raised when Gmail API operations fail."""
    pass


class GoogleSheetsAPIError(GoogleAPIError):
    """Raised when Google Sheets API operations fail."""
    pass


class GoogleCalendarAPIError(GoogleAPIError):
    """Raised when Google Calendar API operations fail."""
    pass


class AuthenticationError(OutreachAgentError):
    """Raised when Google OAuth authentication fails."""
    pass


class RecipientNotFoundError(OutreachAgentError):
    """Raised when a recipient cannot be found in the database."""
    pass


class DemoSchedulingError(OutreachAgentError):
    """Raised when scheduling a demo fails."""
    pass


class FollowUpSchedulingError(OutreachAgentError):
    """Raised when scheduling a follow-up meeting fails."""
    pass


class ContentGenerationError(OutreachAgentError):
    """Raised when AI content generation fails."""
    pass


class SheetUpdateError(OutreachAgentError):
    """Raised when writing back to the Google Sheet fails."""
    pass
