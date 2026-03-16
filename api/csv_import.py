"""Backward-compatibility shim — real implementation is in backend/services/csv_import.py."""
from backend.services.csv_import import (  # noqa: F401
    parse_companies_csv,
    parse_people_csv,
    parse_demos_csv,
)

__all__ = ["parse_companies_csv", "parse_people_csv", "parse_demos_csv"]
