class ProspectingError(Exception):
    """Base exception for the prospecting agent."""


class SearchError(ProspectingError):
    """Raised when a Tavily search fails."""


class SheetsWriteError(ProspectingError):
    """Raised when writing to Google Sheets fails."""


class StructuredOutputError(ProspectingError):
    """Raised when the LLM fails to return valid structured output."""
